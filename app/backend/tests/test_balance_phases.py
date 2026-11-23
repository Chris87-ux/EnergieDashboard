import unittest
from unittest.mock import AsyncMock, patch
from lib.balance import balance
from lib.phases import measured_power
from lib.live import evaluate
from lib.energy import compute_all
from lib.topology import history_flows,derived_samples
from models.flow import Flow
from models.settings import AppSettings
from test_topology import History


def grid():return Flow(id="grid",name="Netz",kind="grid",grid_mode="signed",datapoints={"power_total":"g","frequency":"hz"})
def pv():return Flow(id="pv",name="PV",category="pv",direction="in",datapoints={"power_total":"p"})
def live_balance(flows,values):
    live,_,storages=evaluate(flows,values,0)
    readings={r.flow_id:None if r.power_w is None else abs(r.power_w) for r in live}
    for f in flows:
        if f.pv_type=="mppt":readings[f.id]=values.get(f.datapoints.get("power_total"))
    return balance(flows,readings,{b.id:(b.charge_w,b.discharge_w) for b in storages})


class BalancePhaseTests(unittest.IsolatedAsyncioTestCase):
    def test_grid_is_transfer_not_production(self):
        r=live_balance([grid(),pv()],{"g":500,"p":1000})
        self.assertEqual((r["production"],r["consumption"],r["grid_import"]),(1000,1500,500))
        self.assertEqual((r["autarky_pct"],r["self_consumption_pct"]),(66.7,100))

    def test_export_and_negative_source(self):
        r=live_balance([grid(),pv()],{"g":-200,"p":-1000})
        self.assertEqual((r["production"],r["consumption"],r["grid_export"]),(1000,800,200))
        self.assertEqual((r["autarky_pct"],r["self_consumption_pct"]),(100,80))

    def test_zero_and_absent_generation_are_real_zero(self):
        r=live_balance([grid()],{"g":790})
        self.assertEqual((r["production"],r["consumption"],r["self_consumption_pct"]),(0,790,0))
        r=live_balance([grid(),pv()],{"g":0,"p":0})
        self.assertEqual((r["autarky_pct"],r["self_consumption_pct"]),(0,0))

    def test_missing_values_do_not_become_zero(self):
        r=live_balance([grid(),pv()],{"g":500})
        self.assertIsNone(r["production"]);self.assertIsNone(r["consumption"])
        self.assertTrue(r["notes"])

    def test_hybrid_dc_production_not_battery_or_ac_output_twice(self):
        bat=Flow(id="bat",name="B",kind="storage",electrical_side="dc",capacity_kwh=10,datapoints={"power_total":"b","soc":"soc"})
        mppt=Flow(id="mppt",name="MPPT",category="pv",pv_type="mppt",datapoints={"power_total":"mp"})
        wr=Flow(id="wr",name="WR",category="pv",pv_type="hybrid",storage_ids=["bat"],mppt_ids=["mppt"],datapoints={"power_total":"ac"})
        r=live_balance([grid(),bat,mppt,wr],{"g":-375,"b":1000,"soc":70,"mp":1500,"ac":2375})
        self.assertEqual((r["production"],r["consumption"]),(1500,2000))
        self.assertFalse(r["production_estimated"])
        wr.mppt_ids=[]
        r=live_balance([grid(),bat,wr],{"g":0,"b":1000,"soc":70,"ac":1400})
        self.assertEqual(r["production"],400);self.assertTrue(r["production_estimated"])

    def test_ac_storage_charge_and_invert(self):
        bat=Flow(id="bat",name="B",kind="storage",electrical_side="ac",capacity_kwh=10,charge_sign="positive",invert=True,datapoints={"power_total":"b","soc":"soc"})
        r=live_balance([grid(),bat],{"g":1000,"b":-900,"soc":70})
        self.assertEqual((r["production"],r["consumption"]),(0,100))

    def test_inconsistent_negative_load_is_diagnosed(self):
        r=live_balance([grid(),pv()],{"g":-2000,"p":1000})
        self.assertIsNone(r["consumption"])
        self.assertTrue(any("Negative" in n for n in r["notes"]))

    def test_total_three_phase_is_divided_not_tripled(self):
        f=Flow(name="Motor",power_phase_mode="three",datapoints={"power_total":"p"})
        total,phases,estimated=measured_power(f,{"p":900})
        self.assertEqual(total,900);self.assertEqual(list(phases.values()),[300]*3)
        self.assertEqual(len(estimated),3)

    def test_one_phase_sensor_is_scaled_only_without_total(self):
        f=Flow(name="Motor",power_phase_mode="three",datapoints={"power_l2":"p"})
        total,phases,estimated=measured_power(f,{"p":300})
        self.assertEqual(total,900);self.assertEqual(list(phases.values()),[300]*3)
        self.assertEqual(estimated,["L1","L3"])

    def test_actual_asymmetry_wins(self):
        f=Flow(name="Motor",power_phase_mode="three",datapoints={"power_total":"p","power_l1":"a","power_l2":"b","power_l3":"c"})
        total,phases,estimated=measured_power(f,{"p":900,"a":100,"b":300,"c":500})
        self.assertEqual(list(phases.values()),[100,300,500]);self.assertEqual(estimated,[])

    def test_three_phase_run_and_node_rest(self):
        n=Flow(id="n",name="N",kind="node",power_phase_mode="three",datapoints={"power_total":"n"})
        motor=Flow(id="m",name="M",parent_id="n",power_phase_mode="three",run_power_w=300,datapoints={"run":"run"})
        rows,nodes,_=evaluate([n,motor],{"n":900,"run":1},0)
        self.assertEqual(rows[0].phases,{"L1":100,"L2":100,"L3":100})
        self.assertEqual(nodes[0].difference_phases,{"L1":200,"L2":200,"L3":200})
        samples=derived_samples([n,motor],{"n":900,"run":1},0)
        self.assertEqual(next(d["v"] for d in samples if d["dp"]=="energieboard:n:rest_consumption:l2"),200)

    def test_ac_battery_is_subtracted_inside_node(self):
        n=Flow(id="n",name="N",kind="node",datapoints={"power_total":"n"})
        bat=Flow(id="b",name="B",kind="storage",parent_id="n",capacity_kwh=10,charge_sign="positive",datapoints={"power_total":"b","soc":"soc"})
        _,nodes,_=evaluate([n,bat],{"n":1000,"b":100,"soc":60},0)
        self.assertEqual((nodes[0].children_w,nodes[0].difference_w),(100,900))

    async def test_history_total_counter_is_split_into_three(self):
        f=Flow(id="m",name="M",power_phase_mode="three",energy_phase_mode="three",datapoints={"energy_total":"e"})
        rows,_=await compute_all([f],History({"e":[(0,10),(60,13)]}),0,60,60,900)
        self.assertEqual(rows[0].total.kwh,3)
        self.assertEqual([p.kwh for p in rows[0].phases.values()],[1,1,1])
        self.assertEqual(len(rows[0].estimated_phases),3)

    async def test_history_single_power_phase_scales_to_whole_device(self):
        f=Flow(id="m",name="M",power_phase_mode="three",datapoints={"power_l1":"p"})
        rows,_=await compute_all([f],History({"p":[(0,1000),(60,1000)]}),0,60,60,900)
        self.assertAlmostEqual(rows[0].total.kwh,.05)
        self.assertAlmostEqual(sum(p.kwh for p in rows[0].phases.values()),.05,places=5)

    async def test_history_and_live_share_balance_without_grid_double_count(self):
        fs=[grid(),pv()];raw={"g":500,"p":1000}
        samples={}
        for t in (0,15,30,45,60):
            for d in derived_samples(fs,raw,t):samples.setdefault(d["dp"],[]).append((t,d["v"]))
        samples["p"]=[(0,1000),(60,1000)]
        _,totals=await compute_all(history_flows(fs),History(samples),0,60,60,900,configuration=fs)
        self.assertAlmostEqual(totals.production_kwh,1000/60_000,places=5)
        self.assertAlmostEqual(totals.consumption_kwh,1500/60_000,places=5)
        self.assertEqual(totals.autarky_pct,66.7)
        self.assertEqual(totals.self_consumption_pct,100)

    async def test_frequency_comes_only_from_grid(self):
        from routers.energy import live
        f=pv();f.datapoints.frequency="bad"
        with patch("routers.energy.load_consumer_groups",AsyncMock(return_value=[])),patch("routers.energy.load_settings",AsyncMock(return_value=AppSettings())),patch("routers.energy.load_flows",AsyncMock(return_value=[f,grid()])),patch("lib.acquisition.read_values",AsyncMock(return_value=({"g":100,"p":100,"hz":49.98,"bad":60},[]))),patch("lib.visibility.update_visibility",AsyncMock()):
            report=await live()
        self.assertEqual(report.frequency_hz,49.98)
        self.assertEqual(report.summary.production_w,100)

    async def test_partial_measured_phase_energy_preserved_and_rest_divided(self):
        f=Flow(id="m",name="M",power_phase_mode="three",energy_phase_mode="three",datapoints={"energy_total":"total","energy_l1":"a"})
        rows,_=await compute_all([f],History({"total":[(0,10),(60,13)],"a":[(0,1),(60,1.5)]}),0,60,60,900)
        self.assertEqual([p.kwh for p in rows[0].phases.values()],[.5,1.25,1.25])
        self.assertEqual(sum(p.kwh for p in rows[0].phases.values()),rows[0].total.kwh)

    async def test_grid_counters_are_separate_and_preferred(self):
        g=grid();g.datapoints.energy_import="ei";g.datapoints.energy_export="ee"
        p=pv();p.datapoints.energy_total="ep"
        source=History({"ei":[(0,100),(60,101)],"ee":[(0,20),(60,20.2)],"ep":[(0,50),(60,52)]})
        _,t=await compute_all(history_flows([g,p]),source,0,60,60,900,configuration=[g,p])
        self.assertEqual((t.production_kwh,t.grid_import_kwh,t.grid_export_kwh),(2,1,.2))
        self.assertAlmostEqual(t.consumption_kwh,2.8)

    def test_inactive_linked_mppt_does_not_silently_become_zero(self):
        wr=Flow(id="wr",name="WR",category="pv",pv_type="hybrid",mppt_ids=["inactive"],datapoints={"power_total":"ac"})
        r=live_balance([grid(),wr],{"g":100,"ac":900})
        self.assertIsNone(r["production"])
        self.assertEqual(r["consumption"],1000)

    async def test_three_phase_ac_storage_has_recorded_phase_energy(self):
        f=Flow(id="b",name="B",kind="storage",capacity_kwh=10,power_phase_mode="three",charge_sign="positive",datapoints={"power_total":"p","soc":"s"})
        samples={}
        for t in (0,15,30,45):
            for d in derived_samples([f],{"p":900,"s":60},t):samples.setdefault(d["dp"],[]).append((t,d["v"]))
        rows,_=await compute_all(history_flows([f]),History(samples),0,60,60,900)
        charge=next(r for r in rows if r.direction=="out")
        self.assertAlmostEqual(charge.total.kwh,.015)
        self.assertEqual([p.kwh for p in charge.phases.values()],[.005,.005,.005])
