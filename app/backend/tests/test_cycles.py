import unittest,json
from lib.cycles import advance,OFF,READY,RUNNING,PAUSED,FINISHED,UNKNOWN
from models.cycles import CycleSettings

class CycleDetectionTests(unittest.TestCase):
    def config(self,**kwargs):
        return CycleSettings(enabled=True,start_delay_s=20,end_delay_s=40,window_s=20,minimum_run_s=60,maximum_run_s=600,**kwargs)
    def simulate(self,segments,config=None,state=None,start=0):
        events=[];now=start
        for value,seconds in segments:
            for _ in range(seconds//10):
                state,event=advance(state,config or self.config(),value,now,10)
                if event:events.append(event)
                now+=10
        return state,events,now
    def test_wash_pauses_do_not_create_extra_cycles(self):
        state,events,_=self.simulate([(0,30),(2000,100),(0,20),(60,100),(0,80)])
        self.assertEqual(len(events),1);self.assertEqual(events[0]['outcome'],'completed')
        self.assertEqual(state['status'],FINISHED)
        self.assertEqual(events[0]['ended_at']-events[0]['started_at'],220)
    def test_short_power_spike_not_counted(self):
        _,events,_=self.simulate([(0,30),(100,10),(0,100)])
        self.assertEqual(events,[])
        _,events,_=self.simulate([(0,30),(100,30),(0,100)])
        self.assertEqual(events[0]['outcome'],'aborted')
    def test_initial_running_device_has_no_fabricated_start(self):
        state,events,_=self.simulate([(100,100),(0,80)])
        self.assertEqual(events[0]['outcome'],'unobserved');self.assertNotEqual(state['status'],FINISHED)
    def test_boolean_edges_count_once(self):
        config=CycleSettings(enabled=True,mode='bool',signal_point='point:run')
        _,events,_=self.simulate([(0,30),(1,50),(0,100),(1,80),(0,20)],config)
        self.assertEqual([e['outcome'] for e in events],['completed','completed'])
    def test_restart_preserves_session_and_single_completion(self):
        state,events,now=self.simulate([(0,30),(100,120)])
        session=state['session_id'];state=json.loads(json.dumps(state))
        state,later,_=self.simulate([(100,30),(0,100)],state=state,start=now)
        self.assertEqual(events,[]);self.assertEqual(later[0]['id'],session);self.assertEqual(len(later),1)
        repeated,event=advance(state,self.config(),0,state['last_tick'],10)
        self.assertIsNone(event);self.assertEqual(repeated,state)
    def test_long_data_gap_interrupts_without_false_finish(self):
        state,_,now=self.simulate([(0,30),(100,120)])
        state,event=advance(state,self.config(),None,now+90,10)
        self.assertEqual(event['outcome'],'interrupted');self.assertEqual(state['status'],UNKNOWN)
        state,event=advance(state,self.config(),0,now+100,10)
        self.assertIsNone(event);self.assertNotEqual(state['status'],FINISHED)
    def test_unknown_reading_does_not_advance_end_timer(self):
        state,_,now=self.simulate([(0,30),(100,120),(0,20)])
        state,event=advance(state,self.config(),None,now,10)
        self.assertIsNone(event);self.assertEqual(state['status'],UNKNOWN)
        state,events,_=self.simulate([(0,30)],state=state,start=now+10)
        self.assertEqual(events,[]);self.assertEqual(state['status'],PAUSED)
    def test_minimum_and_maximum_runtime_alarm(self):
        state,events,now=self.simulate([(0,30),(100,700)])
        self.assertTrue(state['runtime_alarm']);self.assertEqual(events,[])
        state,events,_=self.simulate([(0,100)],state=state,start=now)
        self.assertEqual(events[0]['outcome'],'completed');self.assertFalse(state['runtime_alarm'])
    def test_standby_distinct_from_off(self):
        state,_,_=self.simulate([(0,30),(2,30)])
        self.assertEqual(state['status'],READY)
