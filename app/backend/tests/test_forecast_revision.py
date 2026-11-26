import copy
import unittest
from datetime import datetime,timedelta,timezone
from pydantic import ValidationError
from models.forecast import ForecastSite,ForecastProvider
from models.flow import Flow
from lib.forecast_providers import parse_vrm
from lib.forecast_model import build_prediction,normalise_weights,provider_revision
from lib.forecast_migrations import corrected_day
from lib.forecast import validate_site

def site(**fields):return ForecastSite(id='s',name='PV',latitude=50,longitude=10,arrays=[{'kwp':10}],actual_flow_ids=['ac'],**fields)
def estimates():
    return [{'provider_id':id,'revision':'legacy','name':id,'raw_kwh':value,'complete':True,'family':family} for id,value,family in [('vrm',38.89484,'solcast'),('solcast',10.73,'solcast'),('meteo',16.01,'open_meteo')]]
def prediction(s,values=None):return build_prediction(s,'2026-11-26',1,estimates() if values is None else values,[])

class ForecastRevisionTests(unittest.TestCase):
    def test_vrm_realistic_hourly_wh_sum_matches_screenshot(self):
        start=datetime(2026,11,26,tzinfo=timezone.utc).timestamp()
        hours=[[1000*(start+i*3600),38894.84/24] for i in range(24)]
        result=parse_vrm({'success':True,'records':{'solar_yield_forecast':hours}},'UTC')['2026-11-26']
        self.assertAlmostEqual(result['kwh'],38.89484,places=5);self.assertTrue(result['complete'])
        self.assertAlmostEqual(prediction(site())['ensemble_kwh'],20.41121)
    def test_default_dependency_weights_explain_25_25_50(self):
        self.assertEqual([f['weight'] for f in prediction(site())['forecasts']],[.25,.25,.5])
    def test_independent_or_equal_sources_each_receive_third(self):
        for s in (site(group_correlated_sources=False),site(weighting_mode='equal')):
            self.assertTrue(all(abs(f['weight']-1/3)<1e-12 for f in prediction(s)['forecasts']))
    def test_custom_groups_and_explicit_independence(self):
        values=estimates();values[2]['dependency_group']='solcast'
        self.assertTrue(all(abs(f['weight']-1/3)<1e-12 for f in prediction(site(),values)['forecasts']))
        values=estimates();values[0]['dependency_group']='independent'
        self.assertTrue(all(abs(f['weight']-1/3)<1e-12 for f in prediction(site(),values)['forecasts']))
    def test_manual_relative_weights_ignore_groups_and_auto_cap(self):
        values=estimates()
        for f,w in zip(values,(0,1,3)):f['manual_weight']=w
        p=prediction(site(weighting_mode='manual'),values)
        self.assertEqual([f['weight'] for f in p['forecasts']],[0,.25,.75])
        self.assertAlmostEqual(p['ensemble_kwh'],10.73*.25+16.01*.75)
        self.assertEqual(p['weighting']['mode'],'manual')
    def test_missing_manual_source_is_renormalised_no_zero_forecast(self):
        values=estimates()[1:]
        for f in values:f['manual_weight']=0
        p=prediction(site(weighting_mode='manual'),values)
        self.assertIsNone(p['ensemble_kwh']);self.assertTrue(p['weighting_note'])
        values[0]['manual_weight']=2
        p=prediction(site(weighting_mode='manual'),values)
        self.assertEqual(p['ensemble_kwh'],10.73)
    def test_user_cap_50_to_100_percent_and_invalid_weights(self):
        self.assertEqual(normalise_weights({'best':0,'other':100},cap=.5)['best'],.5)
        self.assertGreater(normalise_weights({'best':0,'other':100},cap=1)['best'],.99)
        for weight in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValidationError):ForecastProvider(site_id='s',name='P',kind='vrm',manual_weight=weight)
    def test_weight_preferences_do_not_reset_physical_source_revision(self):
        p=ForecastProvider(site_id='s',name='P',kind='vrm',vrm_installation_id='123')
        before=provider_revision(p);p.manual_weight=0;p.dependency_group='independent'
        self.assertEqual(before,provider_revision(p))
    def test_ac_pv_requires_no_battery(self):
        flow=Flow(id='ac',name='AC rooftop',category='pv',direction='in',electrical_side='ac',datapoints={'power_total':'point:ac'})
        self.assertEqual(validate_site(site(measurement_side='ac'),[flow],{}),[flow])
        self.assertFalse(flow.storage_ids)
        with self.assertRaises(ValueError):validate_site(site(measurement_side='dc'),[flow],{})
    def test_audited_legacy_day_repair_preserves_weights_and_actuals(self):
        values=estimates();values[0]['raw_kwh']*=1000
        for f,w in zip(values,(.25,.25,.5)):f.update(used_kwh=f['raw_kwh'],candidate_kwh=f['raw_kwh'],offset_kwh=0,weight=w,applied_factor=1)
        row={'id':'day','forecasts':values,'ensemble_kwh':9734.3975,'raw_ensemble_kwh':9734.3975,'actual_kwh':12,'base_eligible':True,'eligible':False,'excluded_at':5,'exclusion_reason':'Snow','errors':[],'cutoff':123,'frozen_at':125}
        original=copy.deepcopy(row);fixed=corrected_day(row,{'vrm'},200)
        self.assertEqual(row,original)
        self.assertAlmostEqual(fixed['ensemble_kwh'],20.41121)
        self.assertEqual(fixed['vrm_unit_correction_original']['ensemble_kwh'],9734.3975)
        self.assertEqual(fixed['actual_kwh'],12);self.assertFalse(fixed['eligible']);self.assertEqual(fixed['excluded_at'],5)
        self.assertEqual(fixed['forecasts'][1],row['forecasts'][1])
        self.assertEqual(fixed['cutoff'],123);self.assertEqual(fixed['frozen_at'],125)
        self.assertIsNone(corrected_day(fixed,{'vrm'},300))
        self.assertAlmostEqual(fixed['ensemble_absolute_error'],8.41121)
    def test_unknown_and_already_corrected_sources_are_never_guessed(self):
        values=estimates();values[0]['normalization_version']=2
        self.assertIsNone(corrected_day({'forecasts':values},{'vrm'},1))
        self.assertIsNone(corrected_day({'forecasts':estimates()},set(),1))
