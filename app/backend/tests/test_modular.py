import asyncio
import struct
import unittest
from lib.live import evaluate, aggregate_storage, _averages
from lib.topology import derived_samples, history_flows
from lib.acquisition import decode_payload, decode_registers, read_modbus
from models.acquisition import Connection, Measurement
from models.flow import Flow


def node(id, parent=None):
    return Flow(id=id, name=id, kind="node", parent_id=parent, datapoints={"power_total":id})


class ModularTests(unittest.IsolatedAsyncioTestCase):
    def test_nested_mixed_nodes_and_dc_exclusion(self):
        flows=[node("a"),node("b","a"),Flow(id="motor",name="Motor",parent_id="b",datapoints={"power_total":"motor"}),
            Flow(id="pv",name="PV",direction="in",parent_id="b",datapoints={"power_total":"pv"}),
            Flow(id="mppt",name="MPPT",pv_type="mppt",electrical_side="dc",parent_id="b",datapoints={"power_total":"mppt"}),
            Flow(id="bat",name="Akku",kind="storage",electrical_side="dc",parent_id="b",capacity_kwh=10,datapoints={"power_total":"bat","soc":"soc"})]
        live,nodes,storage=evaluate(flows,{"a":1000,"b":600,"motor":300,"pv":200,"mppt":900,"bat":-800,"soc":80},100)
        self.assertEqual([(n.children_w,n.difference_w) for n in nodes],[(600,400),(100,500)])
        signed=sum(f.power_w*(1 if f.direction=="out" else -1) for f in live)
        self.assertEqual(signed,1000)
        self.assertFalse(any(f.storage_id or f.flow_id in ("bat","mppt") for f in live))
        self.assertEqual(storage[0].remaining_kwh,8)

    def test_unmetered_nested_section_and_missing_child(self):
        group=Flow(id="group",name="Gruppe",kind="node",parent_id="a")
        child=Flow(name="Gerät",parent_id="group",datapoints={"power_total":"child"})
        _,nodes,_=evaluate([node("a"),group,child],{"a":1000,"child":200},0)
        self.assertEqual(nodes[0].difference_w,800)
        _,nodes,_=evaluate([node("a"),group,child],{"a":1000},0)
        self.assertIsNone(nodes[0].difference_w)

    def test_rest_sign_changes_use_stable_history_channels(self):
        flow=node("a")
        rows=history_flows([flow])
        self.assertEqual([r.direction for r in rows],["out","in"])
        values=derived_samples([flow],{"a":-250},10)
        self.assertEqual({v["dp"]:v["v"] for v in values},{"energieboard:a:rest_consumption":0,"energieboard:a:rest_production":250})

    def test_grid_and_hybrid_bidirectional(self):
        grid=Flow(id="grid",name="Netz",category="grid",grid_mode="signed",datapoints={"power_total":"grid"})
        hybrid=Flow(id="hybrid",name="Victron",category="pv",pv_type="hybrid",datapoints={"power_total":"hybrid"})
        rows,_,_=evaluate([grid,hybrid],{"grid":500,"hybrid":-300},100)
        self.assertEqual({r.flow_id:r.power_w for r in rows},{"grid:import":500,"grid:export":0,"hybrid:ac_production":0,"hybrid:ac_consumption":300})
        self.assertEqual(len(derived_samples([grid,hybrid],{"grid":500,"hybrid":-300},100)),4)

    def test_weighted_storage_missing_soc_reserve_and_smoothing(self):
        _averages.clear()
        a=Flow(id="a",name="A",kind="storage",capacity_kwh=10,reserve_soc_pct=20,datapoints={"power_total":"a","soc":"as"})
        b=Flow(id="b",name="B",kind="storage",capacity_kwh=5,charge_sign="positive",datapoints={"power_total":"b","soc":"bs"})
        _,_,storages=evaluate([a,b],{"a":1000,"as":80,"b":-500,"bs":20},0)
        total=aggregate_storage(storages)
        self.assertEqual(total.soc_pct,60)
        self.assertEqual(total.remaining_kwh,9)
        self.assertEqual(storages[0].runtime_h,6)
        _,_,storages=evaluate([a],{"a":2000,"as":80},30)
        self.assertGreater(storages[0].smoothed_power_w,-2000)
        self.assertLess(storages[0].smoothed_power_w,-1000)
        _,_,storages=evaluate([a,b],{"a":-1000,"as":80,"b":-500},60)
        self.assertIsNone(storages[0].runtime_h) # charging now
        self.assertIsNone(aggregate_storage(storages).soc_pct)

    def test_json_and_endianness(self):
        self.assertEqual(decode_payload(b'{"data":{"power":[12,45]}}',"data.power.1"),45)
        self.assertEqual(decode_payload(b'true',""),1)
        self.assertIsNone(decode_payload(b'nan',""))
        for datatype,fmt,value in (("uint16","H",65000),("int16","h",-42),("uint32","I",123456),("int32","i",-90000),("float32","f",12.5),("float64","d",19.25)):
            for byte in ("big","little"):
                for word in ("big","little"):
                    payload=struct.pack(">"+fmt,value)
                    words=[payload[i:i+2] for i in range(0,len(payload),2)]
                    if byte=="little":words=[v[::-1] for v in words]
                    if word=="little":words.reverse()
                    point=Measurement(name="p",connection_id="c",datatype=datatype,byte_order=byte,word_order=word)
                    self.assertEqual(decode_registers(b''.join(words),point),value)

    async def test_real_modbus_tcp(self):
        async def device(reader,writer):
            request=await reader.readexactly(12)
            tx,_,_,unit,fc,register,count=struct.unpack(">HHHBBHH",request)
            payload=struct.pack(">f",1234.5)
            writer.write(struct.pack(">HHHBBB",tx,0,7,unit,fc,4)+payload)
            await writer.drain();writer.close();await writer.wait_closed()
        server=await asyncio.start_server(device,"127.0.0.1",0)
        async with server:
            connection=Connection(name="test",protocol="modbus",host="127.0.0.1",port=server.sockets[0].getsockname()[1])
            point=Measurement(id="p",name="P",connection_id=connection.id,datatype="float32")
            result=await read_modbus(connection,[point])
            self.assertEqual(result,{"p":1234.5})

    async def test_modbus_rejects_wrong_transaction(self):
        async def device(reader,writer):
            request=await reader.readexactly(12)
            tx,_,_,unit,fc,_,_=struct.unpack(">HHHBBHH",request)
            writer.write(struct.pack(">HHHBBBH",tx+1,0,5,unit,fc,2,42))
            await writer.drain();writer.close();await writer.wait_closed()
        server=await asyncio.start_server(device,"127.0.0.1",0)
        async with server:
            connection=Connection(name="test",protocol="modbus",host="127.0.0.1",port=server.sockets[0].getsockname()[1])
            point=Measurement(name="P",connection_id=connection.id)
            with self.assertRaisesRegex(ValueError,"Antwortkopf"):
                await read_modbus(connection,[point])

    async def test_modbus_register_exception_keeps_other_points(self):
        async def device(reader,writer):
            for i in range(2):
                request=await reader.readexactly(12)
                tx,_,_,unit,fc,_,_=struct.unpack(">HHHBBHH",request)
                pdu=bytes([fc|128,2]) if i==0 else bytes([fc,2,0,42])
                writer.write(struct.pack(">HHHB",tx,0,len(pdu)+1,unit)+pdu)
                await writer.drain()
            writer.close();await writer.wait_closed()
        server=await asyncio.start_server(device,"127.0.0.1",0)
        async with server:
            connection=Connection(name="test",protocol="modbus",host="127.0.0.1",port=server.sockets[0].getsockname()[1])
            points=[Measurement(id=str(i),name="P",connection_id=connection.id,register=i) for i in range(2)]
            self.assertEqual(await read_modbus(connection,points),{"0":None,"1":42})

    def test_metadata_and_alias_validation(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):Flow(name="f",extra={"invalid":float("nan")})
        with self.assertRaises(ValidationError):Flow(name="f",extra={"too_large":"a"*20000})
        point=Measurement(name="p",connection_id="c",register=820)
        self.assertEqual(point.model_dump()["register"],820)
        self.assertNotIn("register_address",point.model_dump())

    async def test_signed_grid_uses_separate_energy_counters(self):
        from test_topology import History
        from lib.energy import compute_all
        grid=Flow(id="g",name="Netz",category="grid",grid_mode="signed",datapoints={"power_total":"p","energy_import":"ei","energy_export":"ee"})
        rows,totals=await compute_all(history_flows([grid]),History({"ei":[(0,10),(60,11)],"ee":[(0,3),(60,3.2)]}),0,60,60,900)
        self.assertEqual(totals.in_kwh,1)
        self.assertEqual(totals.out_kwh,0.2)
        self.assertTrue(all(r.total.method=="counter_delta" for r in rows))

    async def test_missing_dc_storage_does_not_mark_ac_totals_incomplete(self):
        from test_topology import History
        from lib.energy import compute_all
        device=Flow(id="run",name="RUN",run_power_w=100,datapoints={"run":"r"})
        storage=Flow(id="bat",name="Speicher",kind="storage",capacity_kwh=10,datapoints={"power_total":"p","soc":"s"})
        source=History({"energieboard:run:run":[(0,100),(15,100),(30,100),(45,100)]})
        rows,totals=await compute_all(history_flows([device,storage]),source,0,60,60,900)
        self.assertFalse(totals.incomplete)
        self.assertTrue(any(not r.total.complete for r in rows if r.storage_id))

    def test_fifty_devices_nested_total(self):
        flows=[node("main"),node("sub","main")]+[Flow(id=f"d{i}",name=f"D{i}",parent_id="sub",datapoints={"power_total":f"d{i}"}) for i in range(50)]
        rows,_,_=evaluate(flows,{"main":6000,"sub":5500,**{f"d{i}":100 for i in range(50)}},0)
        self.assertEqual(sum(r.power_w*(1 if r.direction=="out" else -1) for r in rows),6000)


if __name__=="__main__":unittest.main()
