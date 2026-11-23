import unittest
from unittest.mock import patch,AsyncMock
import httpx
from pydantic import ValidationError
from models.acquisition import Connection,Measurement,validate_measurement
from models.flow import Flow
from models.consumer_group import ConsumerGroup
from lib.http_api import read_api,extract
from lib.consumer_groups import group_summaries
from routers.config_csv import render_csv,prepare


class ApiGroupTests(unittest.IsolatedAsyncioTestCase):
    async def api(self,c,points,handler):
        real=httpx.AsyncClient
        with patch("lib.http_api.httpx.AsyncClient",side_effect=lambda **kw:real(transport=httpx.MockTransport(handler),**kw)):
            return await read_api(c,points)

    def test_legacy_iobroker_keeps_bulk_command(self):
        c=Connection(name="Alt",protocol="iobroker",host="localhost",port=8087)
        self.assertEqual((c.protocol,c.api_preset,c.api_path,c.api_json_path),("api","iobroker","/getBulk/{addresses}","val"))

    def test_presets_are_real_configurable_defaults(self):
        ha=Connection(name="HA",protocol="api",api_preset="homeassistant",host="localhost")
        self.assertEqual((ha.port,ha.api_path,ha.api_auth,ha.api_json_path),(8123,"/api/states/{address}","bearer","state"))
        ev=Connection(name="EV",protocol="api",api_preset="evcc",host="localhost")
        self.assertEqual((ev.port,ev.api_path,ev.api_json_path),(7070,"/api/state","result"))
        ha=Connection(name="HA",protocol="api",api_preset="homeassistant",host="localhost",api_path="/custom/{address}")
        self.assertEqual(ha.api_path,"/custom/{address}")

    def test_host_cannot_be_replaced_by_template(self):
        for path in ("//evil.invalid/path","https://evil.invalid","/path#fragment","/path/{unknown}","/path with space"):
            with self.subTest(path=path),self.assertRaises(ValidationError):
                Connection(name="API",protocol="api",host="localhost",api_path=path)

    def test_json_dot_and_pointer_paths(self):
        self.assertEqual(extract({"a":[{"x":12}]},"a.0.x"),12)
        self.assertEqual(extract({"sensor.x/y":{"a~b":7}},"/sensor.x~1y/a~0b"),7)

    async def test_homeassistant_auth_state_and_unknown(self):
        c=Connection(name="HA",protocol="api",api_preset="homeassistant",host="localhost",token="fixture-token")
        points=[Measurement(id="p",name="P",connection_id=c.id,address="sensor.power"),Measurement(id="u",name="U",connection_id=c.id,address="sensor.missing")]
        def handler(req):
            self.assertEqual(req.headers["authorization"],"Bearer fixture-token")
            return httpx.Response(200,json={"state":"unavailable" if req.url.path.endswith("sensor.missing") else "125.5"})
        values,errors=await self.api(c,points,handler)
        self.assertEqual(values,{"p":125.5,"u":None});self.assertEqual(errors,[])

    async def test_evcc_fetches_one_snapshot_for_multiple_points(self):
        c=Connection(name="EV",protocol="api",api_preset="evcc",host="localhost")
        points=[Measurement(id="g",name="Netz",connection_id=c.id,address="grid.power"),Measurement(id="lp",name="Wallbox",connection_id=c.id,address="loadpoints.0.chargePower")]
        calls=[]
        def handler(req):
            calls.append(req.url.path)
            return httpx.Response(200,json={"result":{"grid":{"power":-250},"loadpoints":[{"chargePower":11000}]}})
        values,errors=await self.api(c,points,handler)
        self.assertEqual(values,{"g":-250,"lp":11000});self.assertEqual(calls,["/api/state"]);self.assertEqual(errors,[])

    async def test_plain_command_is_editable_and_address_encoded(self):
        c=Connection(name="API",protocol="api",host="localhost",api_path="/value?object={address}")
        p=Measurement(name="P",connection_id=c.id,address="a&secret=1")
        def handler(req):
            self.assertEqual(dict(req.url.params),{"object":"a&secret=1"})
            return httpx.Response(200,text="42.5")
        values,_=await self.api(c,[p],handler)
        self.assertEqual(values[p.id],42.5)

    async def test_iobroker_bulk_40_and_both_response_shapes(self):
        c=Connection(name="IO",protocol="iobroker",host="localhost",port=8087)
        points=[Measurement(id=str(i),name=str(i),connection_id=c.id,address="p"+str(i)) for i in range(45)]
        calls=[]
        def handler(req):
            ids=req.url.path.split("/getBulk/")[1].split(",");calls.append(len(ids))
            if len(ids)==40:return httpx.Response(200,json=[{"id":id,"val":12} for id in ids])
            return httpx.Response(200,json={id:{"val":7} for id in ids})
        values,errors=await self.api(c,points,handler)
        self.assertEqual(calls,[40,5]);self.assertEqual(values["0"],12);self.assertEqual(values["44"],7);self.assertEqual(errors,[])

    async def test_errors_are_isolated_and_never_expose_token(self):
        c=Connection(name="API",protocol="api",host="localhost",api_path="/{address}",token="fixture-secret",api_auth="bearer")
        points=[Measurement(id=x,name=x,connection_id=c.id,address=x) for x in ("good","bad")]
        def handler(req):return httpx.Response(200,json=42) if req.url.path=="/good" else httpx.Response(401,text="fixture-secret")
        values,errors=await self.api(c,points,handler)
        self.assertEqual(values,{"good":42,"bad":None});self.assertNotIn("fixture-secret",str(errors));self.assertIn("401",str(errors))

    async def test_basic_and_custom_header_auth(self):
        for auth in ("basic","header"):
            c=Connection(name="API",protocol="api",host="localhost",api_path="/value",api_auth=auth,username="user",password="pass",token="key",api_token_header="X-API-Key")
            def handler(req):
                self.assertEqual(req.headers.get("X-API-Key") if auth=="header" else req.headers.get("Authorization"),"key" if auth=="header" else "Basic dXNlcjpwYXNz")
                return httpx.Response(200,json=1)
            values,_=await self.api(c,[Measurement(name="P",connection_id=c.id)],handler)
            self.assertEqual(list(values.values()),[1])

    def test_generic_fixed_path_and_mqtt_wildcards(self):
        api=Connection(name="API",protocol="api",host="localhost",api_path="/values")
        validate_measurement(api,Measurement(name="P",connection_id=api.id,json_path="power"))
        mqtt=Connection(name="MQTT",protocol="mqtt",host="localhost",port=1883)
        with self.assertRaises(ValueError):validate_measurement(mqtt,Measurement(name="P",connection_id=mqtt.id,address="test/+"))

    def test_group_sums_do_not_add_synthetic_flows(self):
        group=ConsumerGroup(id="g",name="Pumpen")
        a=Flow(id="a",name="A",group_id="g",parent_id="node",datapoints={"power_total":"a"})
        b=Flow(id="b",name="B",group_id="g",run_power_w=200,datapoints={"run":"b"})
        r=group_summaries([group],[a,b],{"a":-300,"b":200})[0]
        self.assertEqual((r.power_w,len(r.member_ids),r.complete),(500,2,True))
        self.assertEqual(len([a,b]),2)

    def test_group_missing_values_are_not_ignored(self):
        group=ConsumerGroup(id="g",name="G");f=Flow(id="a",name="A",group_id="g")
        r=group_summaries([group],[f],{})[0]
        self.assertIsNone(r.power_w);self.assertFalse(r.complete)
        r=group_summaries([group],[],{})[0]
        self.assertEqual(r.power_w,0);self.assertTrue(r.complete)

    def test_group_period_preserves_incomplete_coverage(self):
        group=ConsumerGroup(id="g",name="G");f=Flow(id="a",name="A",group_id="g")
        r=group_summaries([group],[f],{"a":2.5},{"a":False},energy=True)[0]
        self.assertEqual(r.energy_kwh,2.5);self.assertFalse(r.complete)

    def test_only_consumers_may_join_groups(self):
        for config in ({"direction":"in"},{"kind":"node"},{"kind":"grid"},{"category":"pv","pv_type":"hybrid"},{"category":"pv","pv_type":"mppt"}):
            with self.subTest(config=config),self.assertRaises(ValidationError):Flow(name="F",group_id="g",**config)

    def test_csv_roundtrip_groups_and_api_secrets(self):
        from test_revision import RevisionTests
        state=RevisionTests().state();state["consumer_group"]=[ConsumerGroup(id="group",name="Geräte").model_dump()]
        state["flow"].append(Flow(id="load",name="Verbraucher",group_id="group",datapoints={"power_total":"point:p"}).model_dump())
        state["connection"][0]=Connection(id="c",name="HA",protocol="api",api_preset="homeassistant",host="localhost",token="fixture-secret").model_dump()
        exported=render_csv(state);self.assertNotIn("fixture-secret",exported)
        candidate,_=prepare(state,exported,"replace")
        self.assertEqual(candidate["flow"][-1]["group_id"],"group")
        self.assertEqual(candidate["connection"][0]["token"],"fixture-secret")
        self.assertEqual(candidate["consumer_group"][0]["id"],"group")
        state["consumer_group"]=[]
        with self.assertRaisesRegex(ValueError,"Verbrauchergruppe"):prepare(state,render_csv(state),"replace")

    async def test_connection_response_redacts_and_preserves_or_clears_token(self):
        from routers import acquisition
        body=Connection(id="c",name="API",protocol="api",host="localhost",token="")
        with patch.object(acquisition,"db") as db:
            db.connections.find_one=AsyncMock(return_value={"id":"c","token":"fixture-secret"})
            db.connections.replace_one=AsyncMock()
            result=await acquisition.save_connection("c",body)
            self.assertEqual(result["token"],"");self.assertTrue(result["token_set"])
            self.assertEqual(db.connections.replace_one.await_args.args[1]["token"],"fixture-secret")
            body.clear_token=True
            result=await acquisition.save_connection("c",body)
            self.assertFalse(result["token_set"])
