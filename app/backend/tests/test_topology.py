import unittest
from unittest.mock import AsyncMock, patch

import numpy as np
from pydantic import ValidationError

from lib.energy import compute_all
from lib.sources import _num
from lib.topology import derived_samples, history_flows, sample_id
from models.flow import Flow
from models.settings import AppSettings
from routers import energy


class History:
    def __init__(self, samples):
        self.samples = samples
        self.s = AppSettings(recorder={"interval_s": 15})
        self.errors = []

    async def series(self, flow, key, start, end, step, agg):
        points = self.samples.get(flow.datapoints.get(key))
        if points is None:
            return None
        return np.array([p[0] for p in points]), np.array([p[1] for p in points])


class TopologyTests(unittest.IsolatedAsyncioTestCase):
    async def test_mixed_node_counts_children_once(self):
        node = Flow(id="section", name="Werkstatt", kind="node", power_phase_mode="three",
                    datapoints={"power_l1": "l1", "power_l2": "l2", "power_l3": "l3"})
        consumer = Flow(name="Motor", parent_id=node.id, datapoints={"power_total": "motor"})
        producer = Flow(name="PV", direction="in", category="pv", parent_id=node.id, datapoints={"power_total": "pv"})
        run = Flow(id="run-device", name="Pumpe", parent_id=node.id, run_power_w=200, datapoints={"run": "run"})
        battery = Flow(id="battery", name="Speicher", kind="storage", parent_id=node.id,
                       datapoints={"power_total": "bat", "soc": "soc"})
        flows = [node, consumer, producer, run, battery]
        values = {"l1": 600, "l2": 300, "l3": 100, "motor": 300, "pv": 100,
                  "run": 1, "bat": -200, "soc": 72}
        with patch.object(energy, "load_settings", AsyncMock(return_value=AppSettings(iobroker={"host": "test"}))), \
             patch.object(energy, "load_flows", AsyncMock(return_value=flows)), \
             patch.object(energy, "iob_get_bulk", AsyncMock(return_value=values)):
            report = await energy.live()
        self.assertEqual(report.nodes[0].meter_w, 1000)
        self.assertEqual(report.nodes[0].children_w, 600)
        self.assertEqual(report.nodes[0].difference_w, 400)
        self.assertEqual(report.nodes[0].phases, {"L1": 600, "L2": 300, "L3": 100})
        self.assertEqual(report.summary.out_w, 700)
        self.assertEqual(report.summary.in_w, 100)
        self.assertEqual(report.summary.consumption_w, 500)
        self.assertEqual(report.storages[0].soc_pct, 72)
        self.assertEqual(report.storages[0].charge_w, 200)
        self.assertTrue(next(f for f in report.flows if f.flow_id == run.id).estimated)
        self.assertNotIn(node.id, [f.flow_id for f in report.flows])

    async def test_run_energy_holds_state_and_uses_recorded_watts(self):
        flow = Flow(id="pump", name="Pumpe", run_power_w=200, datapoints={"run": "run"})
        points = [(0, 200), (15, 200), (30, 0), (45, 0)]
        source = History({sample_id(flow, "run"): points})
        rows, totals = await compute_all(history_flows([flow]), source, 0, 60, 60, 900)
        self.assertAlmostEqual(totals.out_kwh, 0.002, places=3)
        self.assertAlmostEqual(rows[0].total.kwh, 200 * 30 / 3.6e6, places=4)
        self.assertEqual(rows[0].total.method, "run_estimate")
        self.assertTrue(rows[0].total.complete)
        self.assertEqual(rows[0].phases["L1"].kwh, rows[0].total.kwh)

    async def test_missing_run_does_not_count_as_off(self):
        flow = Flow(id="pump", name="Pumpe", run_power_w=200, datapoints={"run": "run"})
        source = History({sample_id(flow, "run"): [(0, 200)]})
        rows, _ = await compute_all(history_flows([flow]), source, 0, 120, 60, 900)
        self.assertFalse(rows[0].total.complete)
        self.assertLess(rows[0].total.coverage, 0.4)
        self.assertGreater(len(rows[0].total.gaps), 0)
        self.assertEqual(derived_samples([flow], {"run": None}, 0), [])

    async def test_storage_polarity_and_energy_channels(self):
        for sign, value in (("negative", -1200), ("positive", 1200)):
            flow = Flow(id="bat", name="Akku", kind="storage", charge_sign=sign,
                        datapoints={"power_total": "p", "soc": "s"})
            docs = derived_samples([flow], {"p": value}, 0)
            self.assertEqual({d["dp"]: d["v"] for d in docs}, {
                sample_id(flow, "charge"): 1200, sample_id(flow, "discharge"): 0,
            })
            # Charge for 30 seconds, discharge for 30 seconds.
            source = History({
                sample_id(flow, "charge"): [(0, 1200), (15, 1200), (30, 0), (45, 0)],
                sample_id(flow, "discharge"): [(0, 0), (15, 0), (30, 600), (45, 600)],
            })
            rows, totals = await compute_all(history_flows([flow]), source, 0, 60, 60, 900)
            self.assertEqual(totals.out_kwh, 0.01)
            self.assertEqual(totals.in_kwh, 0.005)
            self.assertTrue(all(row.storage_id == "bat" for row in rows))

    async def test_fifty_devices_do_not_include_node_meter(self):
        node = Flow(id="node", name="Abschnitt", kind="node", datapoints={"power_total": "meter"})
        devices = [Flow(id=f"d{i}", name=f"Gerät {i}", parent_id="node", run_power_w=100, datapoints={"run": f"r{i}"}) for i in range(50)]
        source = History({sample_id(flow, "run"): [(0, 100), (15, 100), (30, 100), (45, 100)] for flow in devices})
        rows, totals = await compute_all(history_flows([node, *devices]), source, 0, 60, 60, 900)
        self.assertEqual(len(rows), 50)
        self.assertAlmostEqual(totals.out_kwh, 0.083, places=3)
        self.assertTrue(all(row.parent_id == "node" for row in rows))

    def test_legacy_flow_and_validation(self):
        self.assertEqual(Flow(name="Altbestand").kind, "device")
        with self.assertRaises(ValidationError):
            Flow(name="RUN fehlt", run_power_w=100)
        with self.assertRaises(ValidationError):
            Flow(name="SOC fehlt", kind="storage", datapoints={"power_total": "p"})
        self.assertEqual(_num("false"), 0)
        self.assertEqual(_num("true"), 1)


if __name__ == "__main__":
    unittest.main()
