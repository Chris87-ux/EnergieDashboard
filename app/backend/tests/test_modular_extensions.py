import unittest
from pydantic import ValidationError
from lib.live import evaluate
from lib.hybrid import hybrid_reports
from lib.residuals import with_residuals
from lib.consumer_groups import group_summaries
from lib.topology import history_flows,derived_samples
from models.flow import Flow
from models.consumer_group import ConsumerGroup

class ModularExtensionsTests(unittest.TestCase):
    def bus(self):
        battery=Flow(id='bat',name='Battery',kind='storage',electrical_side='dc',capacity_kwh=10,datapoints={'power_total':'bat','soc':'soc'})
        mppt=Flow(id='pv',name='PV',category='pv',pv_type='mppt',datapoints={'power_total':'pv'})
        hybrid=Flow(id='h',name='Hybrid',category='pv',pv_type='hybrid',storage_ids=['bat'],mppt_ids=['pv'],dc_load_ids=['dc1','dc2'],dc_balance_complete=True,datapoints={'power_total':'ac'})
        load=Flow(id='dc1',name='DC load',electrical_side='dc',datapoints={'power_total':'dc1'})
        run=Flow(id='dc2',name='DC RUN',electrical_side='dc',run_power_w=100,datapoints={'run':'run'})
        return [battery,mppt,hybrid,load,run]

    def test_multiple_dc_loads_and_run_correct_converter_balance(self):
        flows=self.bus();values={'pv':1500,'bat':0,'soc':50,'dc1':-400,'run':1,'ac':950}
        _,_,storages=evaluate(flows,values,0)
        report=hybrid_reports(flows,values,storages)[0]
        self.assertEqual((report.dc_load_w,report.dc_net_w,report.efficiency_pct),(500,1000,95))
        self.assertEqual(report.loss_w,50)

    def test_missing_dc_load_does_not_become_zero(self):
        flows=self.bus();values={'pv':1500,'bat':0,'soc':50,'run':1,'ac':950}
        _,_,storages=evaluate(flows,values,0)
        report=hybrid_reports(flows,values,storages)[0]
        self.assertIsNone(report.dc_load_w);self.assertIsNone(report.efficiency_pct)
        self.assertIn('DC load',report.note)

    def test_dc_collection_meter_and_individual_loads_cannot_double_count(self):
        with self.assertRaises(ValidationError):
            Flow(name='Hybrid',category='pv',pv_type='hybrid',dc_load_ids=['a'],datapoints={'dc_load_power':'b'})
        with self.assertRaises(ValidationError):
            Flow(name='Hybrid',dc_load_ids=['a','a'])

    def node(self):
        return Flow(id='n',name='Section',kind='node',datapoints={'power_total':'n'},residual={'group_id':'g','name':'Other loads','color':'#123456'})

    def test_residual_virtual_device_has_no_measurements(self):
        node=self.node();flows=with_residuals([node]);rest=flows[1]
        self.assertEqual(rest.id,'n:rest_consumption');self.assertEqual(rest.kind,'residual')
        self.assertEqual(rest.name,'Other loads');self.assertEqual(rest.group_id,'g')
        self.assertFalse(any(rest.datapoints.model_dump().values()))
        self.assertEqual(node.kind,'node')
        self.assertEqual(len(with_residuals([Flow(name='Unmetered',kind='node')])),1)

    def test_residual_group_counts_only_residual_and_keeps_balance(self):
        node=self.node();load=Flow(id='c',name='Measured child',parent_id='n',datapoints={'power_total':'c'})
        rows,_,_=evaluate([node,load],{'n':1000,'c':300},0)
        readings={r.flow_id:r.power_w for r in rows}
        group=group_summaries([ConsumerGroup(id='g',name='Other')],[node,load],readings)[0]
        self.assertEqual(group.power_w,700);self.assertEqual(group.member_ids,['n:rest_consumption'])
        self.assertEqual(sum(r.power_w for r in rows if r.direction=='out'),1000)
        rest=next(r for r in rows if r.flow_id=='n:rest_consumption')
        self.assertEqual(rest.name,'Other loads');self.assertEqual(rest.color,'#123456')
        self.assertFalse(rest.name_is_generated)

    def test_residual_history_ids_and_channels_are_preserved(self):
        node=self.node();rows=history_flows([node]);rest=next(r for r in rows if r.id=='n:rest_consumption')
        self.assertEqual(rest.datapoints.power_total,'energieboard:n:rest_consumption')
        self.assertEqual(rest.name,'Other loads')
        samples=derived_samples([node],{'n':1000},0)
        self.assertTrue(any(s['dp']=='energieboard:n:rest_consumption' and s['v']==1000 for s in samples))

    def test_csv_preserves_residual_settings_and_dc_load_lists(self):
        from test_revision import RevisionTests
        from routers.config_csv import render_csv,prepare
        state=RevisionTests().state();state['consumer_group']=[ConsumerGroup(id='g',name='Other').model_dump()]
        node=self.node();node.datapoints.power_total='point:p';state['flow'].append(node.model_dump())
        updated,_=prepare(state,render_csv(state),'replace')
        restored=next(f for f in updated['flow'] if f['id']=='n')
        self.assertEqual(restored['residual']['group_id'],'g');self.assertEqual(restored['residual']['name'],'Other loads')
        state['flow'].append(with_residuals([node])[1].model_dump())
        with self.assertRaisesRegex(ValueError,'Restgeräte'):prepare(state,render_csv(state),'replace')

    def test_custom_residual_name_remains_verbatim_in_english(self):
        from lib.i18n import localise_payload
        name='My own · Restverbrauch'
        row={'flow_id':'n:rest_consumption','category':'custom','name':name,'name_is_generated':False}
        self.assertEqual(localise_payload(row,route='/api/live')['name'],name)
