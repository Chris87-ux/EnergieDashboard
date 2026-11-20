import unittest
from lib.visibility import next_visibility
from lib.live import evaluate, _averages
from lib.topology import derived_samples
from routers.config_csv import render_csv, prepare, parse_csv, revision
from models.flow import Flow
from models.settings import AppSettings
from models.acquisition import Connection, Measurement


class RevisionTests(unittest.TestCase):
    def state(self):
        return {"connection":[Connection(id="c",name="MQTT ; = Name",protocol="mqtt",host="localhost",port=1883,password="secret").model_dump()],
            "measurement":[Measurement(id="p",name="=SUM(A1)",connection_id="c",address="test/p").model_dump()],
            "flow":[Flow(id="g",name="Netz",kind="grid",grid_mode="signed",datapoints={"power_total":"point:p"}).model_dump()],
            "settings":[{"id":"app",**AppSettings(influx={"password":"influx-secret","token":"token-secret"}).model_dump()}]}

    def test_zero_after_minute_and_missing_resets(self):
        previous=None
        for now in range(0,61,5):
            previous=next_visibility(previous,0,now,1,60,15)
            self.assertEqual(previous["hidden"],now>=60)
        self.assertFalse(next_visibility(previous,None,65,1,60,15)["hidden"])
        self.assertFalse(next_visibility(previous,5,65,1,60,15)["hidden"])
        self.assertFalse(next_visibility(previous,0,100,1,60,15)["hidden"])

    def test_zero_threshold_and_delay(self):
        self.assertIsNone(next_visibility(None,1,0,1,60,15)["zero_since"])
        self.assertIsNone(next_visibility(None,.1,0,0,60,15)["zero_since"])
        self.assertEqual(next_visibility(None,0,0,0,60,15)["zero_since"],0)

    def test_csv_roundtrip_keeps_ids_secrets_and_formulas(self):
        state=self.state();text=render_csv(state)
        self.assertNotIn("secret",text)
        self.assertIn("'=SUM(A1)",text)
        candidate,changes=prepare(state,text,"replace")
        self.assertEqual(candidate["measurement"][0]["name"],"=SUM(A1)")
        self.assertEqual(candidate["connection"][0]["password"],"secret")
        self.assertEqual(candidate["settings"][0]["influx"]["token"],"token-secret")
        self.assertEqual(candidate["flow"][0]["id"],"g")
        self.assertEqual(candidate["flow"][0]["kind"],"grid")
        self.assertTrue(all(c["status"]=="unchanged" for c in changes),changes)

    def test_csv_merge_does_not_delete_missing_entries(self):
        state=self.state();subset={k:[] for k in state};subset["measurement"]=[{**state["measurement"][0],"name":"Neuer Name"}]
        candidate,_=prepare(state,render_csv(subset),"merge")
        self.assertEqual(candidate["flow"][0]["id"],"g")
        self.assertEqual(candidate["measurement"][0]["name"],"Neuer Name")

    def test_csv_dangling_reference_and_cycle_rejected(self):
        state=self.state();bad={k:list(v) for k,v in state.items()};bad["measurement"]=[]
        with self.assertRaisesRegex(ValueError,"Messpunkt"):prepare(state,render_csv(bad),"replace")
        a=Flow(id="a",name="A",kind="node",parent_id="b").model_dump()
        b=Flow(id="b",name="B",kind="node",parent_id="a").model_dump()
        bad=self.state();bad["flow"] += [a,b]
        with self.assertRaisesRegex(ValueError,"Kreis"):prepare(state,render_csv(bad),"replace")

    def test_csv_rejects_duplicates_and_bad_version(self):
        with self.assertRaises(ValueError):parse_csv("record_type;csv_version;id\nmeasurement;2;x\n")
        with self.assertRaises(ValueError):parse_csv("record_type;csv_version;id\nmeasurement;1;x\nmeasurement;1;x\n")
        with self.assertRaises(ValueError):parse_csv("record_type;csv_version;id\nmeasurement;1;\n")
        with self.assertRaisesRegex(ValueError,"Unbekannte CSV-Spalten"):
            parse_csv("record_type;csv_version;id;scal\nmeasurement;1;x;1000\n")

    def test_grid_legacy_normalization_and_storage_sides(self):
        self.assertEqual(Flow(name="Netz",category="grid").kind,"grid")
        for side in ("ac","dc"):
            flow=Flow(name="Speicher",kind="storage",electrical_side=side,datapoints={"power_total":"p","soc":"s"})
            self.assertEqual(flow.electrical_side,side)

    def test_storage_ac_phases_and_reserve_datapoint(self):
        _averages.clear()
        flow=Flow(id="bat",name="B",kind="storage",electrical_side="ac",capacity_kwh=10,power_phase_mode="three",charge_sign="positive",
            datapoints={"power_l1":"l1","power_l2":"l2","power_l3":"l3","soc":"s","soc_reserve":"r"})
        values={"l1":-200,"l2":-300,"l3":-500,"s":80,"r":30}
        _,_,storages=evaluate([flow],values,0)
        self.assertEqual(storages[0].discharge_w,1000)
        self.assertEqual(storages[0].usable_kwh,5)
        self.assertEqual(storages[0].runtime_h,5)
        self.assertEqual(len(storages[0].phases),3)
        self.assertEqual({r["dp"]:r["v"] for r in derived_samples([flow],values,0)}["energieboard:bat:discharge"],1000)
        del values["r"]
        self.assertIsNone(evaluate([flow],values,15)[2][0].runtime_h)

    def test_generator_telemetry_is_not_power(self):
        flow=Flow(name="BHKW",category="generator",direction="in",datapoints={"power_total":"p","engine_temperature":"t","efficiency":"e","fuel_consumption":"f","operating_hours":"h"})
        rows,_,_=evaluate([flow],{"p":2000,"t":83,"e":92,"f":2.3,"h":1200},0)
        self.assertEqual(rows[0].power_w,2000)
        self.assertEqual(rows[0].telemetry["engine_temperature"],83)
        self.assertEqual(rows[0].telemetry["fuel_unit"],"L/h")

    def test_revision_changes_on_configuration_edit(self):
        state=self.state();before=revision(state);state["measurement"][0]["scale"]=2
        self.assertNotEqual(before,revision(state))


class ImportRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_failed_csv_write_restores_previous_configuration(self):
        from copy import deepcopy
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, patch
        from fastapi import HTTPException
        from routers import config_csv
        state=RevisionTests().state()
        candidate=deepcopy(state);candidate["measurement"][0]["name"]="Geändert"
        storage={config_csv.COLLECTIONS[k]:deepcopy(v) for k,v in state.items()}
        storage["config_backups"]=[]
        fail=True
        class Collection:
            def __init__(self,name):self.name=name
            async def delete_many(self,query):storage[self.name]=[]
            async def insert_many(self,documents):
                nonlocal fail
                if self.name=="connections" and fail:
                    fail=False
                    raise RuntimeError("Simulierter Schreibfehler")
                storage[self.name].extend(deepcopy(documents))
            async def insert_one(self,document):storage[self.name].append(document)
        class Database:
            def __getitem__(self,name):return Collection(name)
            @property
            def config_backups(self):return Collection("config_backups")
        body=config_csv.ImportRequest(csv_text="test",expected_revision=config_csv.revision(state))
        with patch.object(config_csv,"db",Database()),patch.object(config_csv,"plan",AsyncMock(return_value=(state,candidate,[]))):
            with self.assertRaises(HTTPException) as error:
                await config_csv.apply_csv(body)
        self.assertEqual(error.exception.status_code,503)
        self.assertEqual(storage["measurements"],state["measurement"])
        self.assertEqual(storage["connections"],state["connection"])
        self.assertEqual(storage["flows"],state["flow"])
        self.assertEqual(storage["config_backups"][0]["documents"],state)
