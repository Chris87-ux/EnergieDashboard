import unittest
from unittest.mock import AsyncMock, patch
from lib.live import evaluate
from lib.visibility import next_visibility, update_visibility
from lib.sources import LiveSource, to_power_w
from lib.energy import compute_all
from models.flow import Flow
from models.settings import AppSettings
from routers.energy import _summary


class SignedPowerTests(unittest.IsolatedAsyncioTestCase):
    def test_negative_producer_keeps_sign_and_correct_balance(self):
        node=Flow(id="n",name="Abschnitt",kind="node",datapoints={"power_total":"meter"})
        producer=Flow(id="pv",name="PV",direction="in",category="pv",parent_id="n",datapoints={"power_total":"pv"})
        consumer=Flow(id="c",name="Gerät",parent_id="n",datapoints={"power_total":"load"})
        flows,nodes,_=evaluate([node,producer,consumer],{"meter":300,"pv":-200,"load":500},0)
        self.assertEqual(next(f for f in flows if f.flow_id=="pv").power_w,-200)
        self.assertEqual(nodes[0].children_w,300)
        self.assertEqual(nodes[0].difference_w,0)
        self.assertEqual(_summary(flows).pv_w,200)
        self.assertEqual(_summary(flows).consumption_w,500)

    def test_tiny_signed_power_is_not_rounded_to_zero(self):
        for value in (-.25,.25,-.0001,.0001):
            flow=Flow(name="Messwert",direction="in",datapoints={"power_total":"p"})
            self.assertEqual(evaluate([flow],{"p":value},0)[0][0].power_w,value)
            self.assertEqual(to_power_w(flow,value),value)

    def test_filter_is_strictly_between_minus_one_and_plus_one(self):
        for power in (-1000,-1.1,-1,1,1.1,1000):
            previous={"last_seen":60,"zero_since":0}
            state=next_visibility(previous,power,60,1,60,15)
            self.assertFalse(state["hidden"])
            self.assertIsNone(state["zero_since"])
        for power in (-.99,-.25,0,.25,.99):
            state=next_visibility({"last_seen":60,"zero_since":0},power,60,1,60,15)
            self.assertTrue(state["hidden"])

    async def test_grid_never_hidden_even_at_zero(self):
        grid=Flow(name="Netz",kind="grid",grid_mode="signed",datapoints={"power_total":"p"})
        flows,_,_=evaluate([grid],{"p":0},100)
        class Cursor:
            async def to_list(self):return [{"id":f.flow_id,"last_seen":100,"zero_since":0} for f in flows]
        with patch("lib.visibility.db") as db:
            db.visibility.find.return_value=Cursor()
            db.visibility.bulk_write=AsyncMock()
            await update_visibility(flows,100,AppSettings())
        self.assertTrue(all(not f.hidden and f.zero_since is None for f in flows))

    async def test_negative_producer_history_integrates_magnitude(self):
        flow=Flow(name="PV",direction="in",category="pv",datapoints={"power_total":"p"})
        source=LiveSource(AppSettings())
        with patch("lib.sources.mongo_series",AsyncMock(return_value=[(0,-600),(60,-600)])):
            rows,totals=await compute_all([flow],source,0,60,60,900)
        self.assertEqual(totals.in_kwh,.01)
        self.assertEqual(rows[0].total.kwh,.01)
