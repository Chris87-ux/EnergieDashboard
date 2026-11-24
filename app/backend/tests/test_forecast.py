import unittest
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from lib.forecast_providers import daily_intervals,parse_solcast,parse_vrm,parse_forecast_solar,parse_open_meteo_arrays,duration_seconds
from models.forecast import ForecastSite

class ForecastNormalisationTests(unittest.TestCase):
    def test_dst_days_preserve_actual_23_and_25_hours(self):
        zone=ZoneInfo('Europe/Berlin')
        for day,hours in [('2026-03-29',23),('2026-10-25',25)]:
            a=datetime.fromisoformat(day).replace(tzinfo=zone);b=a+timedelta(days=1)
            intervals=[(t,t+3600,1) for t in range(int(a.timestamp()),int(b.timestamp()),3600)]
            result=daily_intervals(intervals,'Europe/Berlin')[day]
            self.assertEqual(result['kwh'],hours);self.assertTrue(result['complete'])
    def test_solcast_kw_half_hour_to_kwh_and_offset(self):
        data={'forecasts':[{'period_end':'2026-11-24T00:00:00Z','period':'PT30M','pv_estimate':2}]}
        out=parse_solcast(data,'Europe/Berlin')['2026-11-24']
        self.assertEqual(out['kwh'],1);self.assertFalse(out['complete'])
        self.assertEqual(duration_seconds('PT1H'),3600)
    def test_vrm_ms_hour_kwh_no_battery_or_consumption_added(self):
        t=datetime(2026,11,24,12,tzinfo=ZoneInfo('Europe/Berlin')).timestamp()
        data={'success':True,'records':{'solar_yield_forecast':[[t*1000,3]],'vrm_consumption_fc':[[t*1000,99]]}}
        self.assertEqual(parse_vrm(data,'Europe/Berlin')['2026-11-24']['kwh'],3)
    def test_forecast_solar_wh_to_kwh(self):
        result=parse_forecast_solar({'result':{'watt_hours_day':{'2026-11-24':4200}}},'Europe/Berlin')
        self.assertEqual(result['2026-11-24']['kwh'],4.2)
    def test_open_meteo_clips_total_ac_inverter_not_each_plane(self):
        site=ForecastSite(name='PV',latitude=50,longitude=10,arrays=[{'kwp':4},{'kwp':4}],actual_flow_ids=['pv'],measurement_side='ac',inverter_kw=5,performance_ratio=1)
        t=datetime(2026,11,24,12,tzinfo=ZoneInfo('Europe/Berlin')).timestamp()
        payload={'hourly':{'time':[t],'global_tilted_irradiance':[1000]}}
        self.assertEqual(parse_open_meteo_arrays([payload,payload],site,'Europe/Berlin')['2026-11-24']['kwh'],5)
    def test_invalid_values_and_overlaps_are_not_silent_zero(self):
        with self.assertRaises(ValueError):daily_intervals([(0,3600,1),(1800,5400,1)],'UTC')
        with self.assertRaises(ValueError):parse_forecast_solar({'result':{'watt_hours_day':{'2026-11-24':-1}}},'UTC')
        with self.assertRaises(ValueError):parse_solcast({'forecasts':[{'period_end':'2026-11-24T12:00:00','period':'PT30M','pv_estimate':1}]},'UTC')
