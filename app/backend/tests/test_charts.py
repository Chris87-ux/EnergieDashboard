import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from datetime import date,timedelta
import numpy as np
from models.flow import Flow
from models.charts import ChartConfig,ChartSeries
from lib.charts import chart_report,bucket_values,source_catalog,validate_chart

class ChartTests(unittest.IsolatedAsyncioTestCase):
    async def test_signed_tiny_values_gaps_and_bounded_output(self):
        f=Flow(id='pv',name='PV',category='pv',direction='in',datapoints={'power_total':'point:p'})
        src=SimpleNamespace(s=SimpleNamespace(recorder=SimpleNamespace(interval_s=1)),errors=[],series=AsyncMock(return_value=(np.array([0.,10.,20.]),np.array([-.1,-500.,float('nan')]))))
        chart=ChartConfig(name='PV',series=[ChartSeries(kind='power',reference_id='pv')])
        result=await chart_report(chart,[f],[],src,0,600,60)
        values=[v for _,v in result['series'][0]['points']]
        self.assertEqual(values[:3],[-.1,-500.,None]);self.assertLessEqual(len(values),60)
        self.assertTrue(src.series.call_args.kwargs['bucket_derived'])
    async def test_symmetric_phases_and_raw_units(self):
        f=Flow(id='motor',name='Motor',power_unit='kW',power_phase_mode='three',datapoints={'power_l1':'point:p'})
        src=SimpleNamespace(s=SimpleNamespace(recorder=SimpleNamespace(interval_s=1)),errors=[],series=AsyncMock(return_value=(np.array([0.]),np.array([.25]))))
        chart=ChartConfig(name='Both',series=[ChartSeries(kind='power',reference_id='motor'),ChartSeries(kind='measurement',reference_id='p')])
        result=await chart_report(chart,[f],[{'id':'p','name':'Raw','unit':'kW'}],src,0,60)
        self.assertEqual(result['series'][0]['points'][0][1],750)
        self.assertEqual(result['series'][1]['points'][0][1],.25)
        self.assertEqual(result['series'][1]['unit'],'kW')
    async def test_bool_and_status_use_last_not_mean(self):
        f=Flow(id='w',name='Washer');src=SimpleNamespace(s=SimpleNamespace(recorder=SimpleNamespace(interval_s=1)),errors=[],series=AsyncMock(return_value=None))
        c=ChartConfig(name='Digital',series=[ChartSeries(kind='measurement',reference_id='b'),ChartSeries(kind='status',reference_id='w')])
        r=await chart_report(c,[f],[{'id':'b','name':'Bool','unit':'bool'}],src,0,60)
        self.assertTrue(all(call.args[-1]=='last' for call in src.series.call_args_list))
        self.assertTrue(all(s['digital'] for s in r['series']))
        self.assertTrue(all(v is None for s in r['series'] for _,v in s['points']))
    def test_source_validation_and_duplicate_series(self):
        f=Flow(id='node',name='N',kind='node',datapoints={'power_total':'point:x'})
        catalog=source_catalog([f],[]);c=ChartConfig(name='Rest',series=[ChartSeries(kind='power',reference_id='node:rest_consumption',unit='nonsense')])
        validate_chart(c,catalog);self.assertEqual(c.series[0].unit,'W')
        with self.assertRaises(ValueError):validate_chart(c,source_catalog([],[]))
        with self.assertRaises(ValueError):ChartConfig(name='Duplicate',series=[c.series[0],c.series[0]])
    def test_bucket_never_fills_missing_with_zero(self):
        self.assertEqual(bucket_values((np.array([0,10,20]),np.array([0,float('inf'),-0.2])),0,30,10),[0,None,-.2])
