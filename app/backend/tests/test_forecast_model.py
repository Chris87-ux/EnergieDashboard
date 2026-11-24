import unittest
from datetime import date,timedelta
from lib.forecast_model import build_prediction,evaluate_prediction,eligible_history,normalise_weights,site_revision
from lib.forecast import validate_site
from models.forecast import ForecastSite
from models.flow import Flow

def site():return ForecastSite(id='s',name='S',latitude=50,longitude=10,arrays=[{'kwp':5}],actual_flow_ids=['pv'],revision='revision',minimum_training_days=3,training_days=45)
def estimate(id='p',value=10,family='independent'):return {'provider_id':id,'revision':'p1','raw_kwh':value,'complete':True,'family':family}
class ForecastLearningTests(unittest.TestCase):
    def test_no_lookahead_or_late_evaluation(self):
        s=site();rows=[{'day':'2026-11-23','revision':s.revision,'base_eligible':True,'actual_kwh':12,'evaluated_at':999}]
        self.assertEqual(eligible_history(rows,s,'2026-11-23',2000),[])
        self.assertEqual(eligible_history(rows,s,'2026-11-24',500),[])
        self.assertEqual(len(eligible_history(rows,s,'2026-11-24',1000)),1)
    def test_correction_must_prove_itself_on_later_days(self):
        s=site();rows=[];results=[]
        for n in range(12):
            day=(date(2026,11,1)+timedelta(days=n)).isoformat();prediction=build_prediction(s,day,100+n,[estimate()],rows)
            record={'day':day,'revision':s.revision,**prediction};record.update(evaluate_prediction(record,12,True));record['evaluated_at']=100+n;rows.append(record);results.append(prediction)
        self.assertEqual(results[2]['forecasts'][0]['candidate_factor'],1)
        self.assertNotEqual(results[3]['forecasts'][0]['candidate_factor'],1)
        self.assertFalse(results[3]['forecasts'][0]['use_corrected'])
        self.assertTrue(results[6]['forecasts'][0]['use_corrected'])
        self.assertLess(abs(12-results[-1]['ensemble_kwh']),2)
        self.assertEqual(results[0]['ensemble_kwh'],10)
    def test_bad_corrections_fall_back_to_original(self):
        s=site();rows=[]
        for n in range(5):rows.append({'day':f'2026-11-{n+1:02d}','revision':s.revision,'base_eligible':True,'actual_kwh':10,'evaluated_at':n,'forecasts':[{**estimate(),'candidate_factor':1.5,'candidate_kwh':15,'used_kwh':10}]})
        prediction=build_prediction(s,'2026-11-24',100,[estimate()],rows)
        self.assertEqual(prediction['forecasts'][0]['applied_factor'],1)
    def test_correlated_family_does_not_double_its_weight(self):
        s=site();r=build_prediction(s,'2026-11-24',100,[estimate('vrm',10,'solcast'),estimate('solcast',10,'solcast'),estimate('solar',20,'solar')],[])
        self.assertEqual(r['ensemble_kwh'],15)
        self.assertAlmostEqual(sum(f['weight'] for f in r['forecasts']),1)
        self.assertEqual(normalise_weights({'a':0,'b':1000})['a'],.7)
    def test_manual_exclusion_history_applies_at_cutoff_only(self):
        s=site();row={'day':'2026-11-23','revision':s.revision,'base_eligible':True,'actual_kwh':1,'evaluated_at':1,'exclusion_log':[{'changed_at':10,'excluded':True},{'changed_at':20,'excluded':False}]}
        self.assertEqual(eligible_history([row],s,'2026-11-24',15),[])
        self.assertEqual(len(eligible_history([row],s,'2026-11-24',25)),1)
        self.assertEqual(len(eligible_history([row],s,'2026-11-24',5)),1)
    def test_missing_zero_and_configuration_change(self):
        s=site();r=build_prediction(s,'2026-11-24',1,[estimate(value=0)],[])
        self.assertEqual(r['ensemble_kwh'],0)
        self.assertEqual(build_prediction(s,'2026-11-24',1,[],[])['ensemble_kwh'],None)
        self.assertFalse(evaluate_prediction(r,None,False)['eligible'])
        before=site_revision(s,'Europe/Berlin');s.name='New name';self.assertEqual(before,site_revision(s,'Europe/Berlin'));s.arrays[0].kwp=10;self.assertNotEqual(before,site_revision(s,'Europe/Berlin'))
    def test_pv_actual_validation_excludes_hybrid_and_duplicate_measurements(self):
        s=site();f=Flow(id='pv',name='MPPT',category='pv',pv_type='mppt',direction='in',datapoints={'power_total':'point:pv'})
        self.assertEqual(validate_site(s,[f],{}),[f])
        other=f.model_copy(update={'id':'other'});s.actual_flow_ids=['pv','other']
        with self.assertRaises(ValueError):validate_site(s,[f,other],{})
        s.actual_flow_ids=['pv'];f=f.model_copy(update={'pv_type':'hybrid'})
        with self.assertRaises(ValueError):validate_site(s,[f],{})
