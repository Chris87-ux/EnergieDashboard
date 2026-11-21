import unittest
from lib.hybrid import hybrid_ac, hybrid_reports
from lib.live import evaluate
from lib.store import all_datapoints
from lib.topology import derived_samples, history_flows
from lib.energy import compute_all
from models.flow import Flow
from test_topology import History


class HybridTests(unittest.IsolatedAsyncioTestCase):
    def setup_bus(self, **kwargs):
        self.mppt=Flow(id="pv",name="MPPT",category="pv",pv_type="mppt",power_phase_mode="three",energy_phase_mode="three",datapoints={"power_total":"pv","energy_total":"e","power_l1":"obsolete","frequency":"hz"})
        self.battery=Flow(id="bat",name="Battery",kind="storage",electrical_side="dc",capacity_kwh=10,datapoints={"power_total":"bat","soc":"soc"})
        self.hybrid=Flow(id="wr",name="Hybrid",category="pv",pv_type="hybrid",storage_ids=["bat"],mppt_ids=["pv"],dc_balance_complete=True,datapoints={"power_total":"ac"},**kwargs)
        return [self.mppt,self.battery,self.hybrid]

    def report(self, flows, **values):
        _,_,storage=evaluate(flows,values,0)
        return hybrid_reports(flows,values,storage)[0]

    def test_dc_mppt_canonical_and_only_relevant_points(self):
        self.setup_bus()
        self.assertEqual(self.mppt.electrical_side,"dc")
        self.assertEqual(self.mppt.power_phase_mode,"single")
        self.assertEqual(self.mppt.energy_phase_mode,"single")
        self.assertEqual(all_datapoints([self.mppt]),["e","pv"])

    def test_discharge_and_solar_charge_balance(self):
        flows=self.setup_bus()
        r=self.report(flows,pv=1000,bat=1000,soc=70,ac=1900)
        self.assertEqual((r.dc_net_w,r.efficiency_pct,r.loss_w),(2000,95,100))
        r=self.report(flows,pv=2000,bat=-1000,soc=70,ac=950)
        self.assertEqual((r.dc_net_w,r.efficiency_pct,r.battery_charge_w),(1000,95,1000))

    def test_grid_charging_and_battery_polarity(self):
        flows=self.setup_bus()
        r=self.report(flows,pv=0,bat=-900,soc=70,ac=-1000)
        self.assertEqual((r.mode,r.efficiency_pct,r.loss_w),("charging",90,100))
        flows[1]=self.battery.model_copy(update={"charge_sign":"positive"})
        r=self.report(flows,pv=-2000,bat=1000,soc=70,ac=950)
        self.assertEqual(r.efficiency_pct,95)

    def test_passthrough_is_not_generation_or_phase_energy(self):
        flows=self.setup_bus(hybrid_ac_mode="terminals")
        flows[-1]=self.hybrid.model_copy(update={"datapoints":self.hybrid.datapoints.model_copy(update={"ac_input":"input"})})
        values={"pv":1000,"bat":0,"soc":70,"ac":2950,"input":2000}
        ac,phases,_,_=hybrid_ac(flows[-1],values)
        self.assertEqual(ac,950)
        self.assertTrue(all(v is None for v in phases.values()))
        self.assertEqual(self.report(flows,**values).efficiency_pct,95)
        samples={r["dp"]:r["v"] for r in derived_samples(flows,values,0)}
        self.assertEqual(samples["energieboard:wr:ac_production"],950)
        self.assertEqual(samples["energieboard:wr:ac_consumption"],0)
        self.assertIsNone(hybrid_ac(flows[-1],{**values,"input":None})[0])

    def test_direct_dc_units_polarity_and_priority(self):
        flows=self.setup_bus(dc_power_unit="kW",dc_invert=True)
        flows[-1]=self.hybrid.model_copy(update={"datapoints":self.hybrid.datapoints.model_copy(update={"dc_power":"dc"})})
        r=self.report(flows,dc=-1,ac=950)
        self.assertEqual((r.dc_net_w,r.dc_source,r.efficiency_pct),(1000,"measured",95))
        r=self.report(flows,dc=.9,ac=-1000)
        self.assertEqual((r.mode,r.efficiency_pct),("charging",90))
        self.assertIsNone(self.report(flows,ac=950).efficiency_pct)

    def test_invalid_and_idle_values_never_fabricate_efficiency(self):
        flows=self.setup_bus()
        for ac,pv,bat in [(1100,1000,0),(950,0,-1000),(0,1000,-1000),(50,60,0)]:
            with self.subTest(ac=ac,pv=pv,bat=bat):
                self.assertIsNone(self.report(flows,ac=ac,pv=pv,bat=bat,soc=70).efficiency_pct)
        self.assertIsNone(self.report(flows,ac=950,pv=1000).efficiency_pct)
        self.assertIsNone(self.report([flows[0],flows[2]],ac=950,pv=1000).efficiency_pct)
        flows[1]=self.battery.model_copy(update={"electrical_side":"ac"})
        self.assertIsNone(self.report(flows,ac=950,pv=1000,bat=0).efficiency_pct)

    def test_dc_loads_and_explicit_confirmation(self):
        flows=self.setup_bus()
        flows[-1]=self.hybrid.model_copy(update={"datapoints":self.hybrid.datapoints.model_copy(update={"dc_load_power":"load"})})
        r=self.report(flows,ac=950,pv=1200,bat=0,load=200)
        self.assertEqual((r.dc_net_w,r.efficiency_pct),(1000,95))
        self.assertIsNone(self.report(flows,ac=950,pv=1200,bat=0).efficiency_pct)
        flows[-1]=flows[-1].model_copy(update={"dc_balance_complete":False})
        self.assertIsNone(self.report(flows,ac=950,pv=1200,bat=0,load=200).efficiency_pct)

    async def test_dc_counter_separate_from_ac_totals_and_phases(self):
        self.setup_bus()
        source=History({"e":[(0,12),(60,13)],"pv":[(0,1000),(60,1000)],"ac":[(0,2000),(60,2000)]})
        ac=Flow(id="ac",name="AC",direction="in",datapoints={"power_total":"ac"})
        rows,totals=await compute_all(history_flows([self.mppt,ac]),source,0,60,60,900)
        self.assertEqual(rows[0].total.kwh,1)
        self.assertEqual(rows[0].total.method,"counter_delta")
        self.assertEqual(rows[0].electrical_side,"dc")
        self.assertTrue(all(p.method=="not_applicable" for p in rows[0].phases.values()))
        self.assertAlmostEqual(totals.in_kwh,round(2000*60/3600000,3),places=3)

    def test_three_phase_terminal_net_and_reverse_flow(self):
        self.setup_bus()
        f=self.hybrid.model_copy(update={"hybrid_ac_mode":"terminals","power_phase_mode":"three","datapoints":self.hybrid.datapoints.model_copy(update={"power_total":"","power_l1":"a","power_l2":"b","power_l3":"c","ac_input":"input"})})
        self.assertEqual(hybrid_ac(f,{"a":500,"b":500,"c":500,"input":2000})[0],-500)
        self.assertEqual(hybrid_ac(f,{"a":-100,"b":0,"c":0,"input":-600})[0],500)

    def test_multiple_sources_and_batteries(self):
        flows=self.setup_bus()
        flows.extend([self.mppt.model_copy(update={"id":"pv2"}),self.battery.model_copy(update={"id":"bat2"})])
        flows[2]=self.hybrid.model_copy(update={"mppt_ids":["pv","pv2"],"storage_ids":["bat","bat2"]})
        r=self.report(flows,pv=500,bat=500,ac=1900)
        self.assertEqual((r.dc_pv_w,r.battery_discharge_w,r.dc_net_w,r.efficiency_pct),(1000,1000,2000,95))

    async def test_terminal_history_records_converter_net_without_phase_claim(self):
        flows=self.setup_bus(hybrid_ac_mode="terminals")
        wr=self.hybrid.model_copy(update={"datapoints":self.hybrid.datapoints.model_copy(update={"ac_input":"input"})})
        docs=derived_samples([wr],{"ac":2950,"input":2000},0)
        source=History({d["dp"]:[(t,d["v"]) for t in (0,15,30,45)] for d in docs})
        rows,totals=await compute_all(history_flows([wr]),source,0,60,60,900)
        production=next(r for r in rows if r.direction=="in")
        self.assertAlmostEqual(production.total.kwh,950*60/3600000,places=4)
        self.assertTrue(all(p.method=="not_applicable" for p in production.phases.values()))
        self.assertAlmostEqual(totals.in_kwh,round(950*60/3600000,3),places=3)

    def test_csv_hybrid_roundtrip_and_invalid_ac_battery(self):
        from routers.config_csv import render_csv,prepare
        from test_revision import RevisionTests
        state=RevisionTests().state()
        flows=self.setup_bus(hybrid_ac_mode="terminals",dc_invert=True,hybrid_min_power_w=150)
        flows[-1]=self.hybrid.model_copy(update={"datapoints":self.hybrid.datapoints.model_copy(update={"ac_input":"legacy.input","dc_power":"legacy.dc"})})
        state["flow"].extend(f.model_dump() for f in flows)
        candidate,_=prepare(state,render_csv(state),"replace")
        hybrid=next(f for f in candidate["flow"] if f["id"]=="wr")
        self.assertEqual(hybrid["hybrid_ac_mode"],"terminals")
        self.assertEqual(hybrid["datapoints"]["dc_power"],"legacy.dc")
        self.assertTrue(hybrid["dc_invert"])
        state["flow"][2]["electrical_side"]="ac"
        with self.assertRaisesRegex(ValueError,"DC-Speicher"):
            prepare(state,render_csv(state),"replace")
