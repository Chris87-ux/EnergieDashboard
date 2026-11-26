"""Additional real-MongoDB tests, run in a dedicated disposable database."""
import asyncio,time
from datetime import datetime,timedelta
from unittest.mock import patch,AsyncMock
from lib.db import db,client,ensure_indexes
from lib.cycles import tick_cycles
from lib.forecast import reserve,freeze_day,process_site,day_bounds,refresh_provider
from lib.forecast_model import site_revision,provider_revision
from lib.forecast_providers import ForecastError
from models.flow import Flow
from models.forecast import ForecastSite,ForecastProvider
from models.settings import AppSettings

async def main():
    await ensure_indexes()
    try:
        settings=AppSettings(recorder={'enabled':True,'interval_s':5})
        f=Flow(id='washer',name='Washer',datapoints={'run':'point:run'},run_power_w=500,cycle_tracking={'enabled':True,'mode':'bool','signal_point':'point:run','start_delay_s':0,'end_delay_s':0,'window_s':0,'minimum_run_s':0})
        for t,v in [(1000,0),(1005,1),(1010,1)]:await tick_cycles([f],{'point:run':v},t,settings)
        prior=await db.cycle_states.find_one({'id':f.id},{'_id':0})
        for retry in range(2):
            # Reproduce crash after durable event write, before new state write.
            if retry:await db.cycle_states.replace_one({'id':f.id},prior)
            await tick_cycles([f],{'point:run':0},1015,settings)
        assert await db.cycle_events.count_documents({'outcome':'completed'})==1
        assert (await db.cycle_states.find_one({'id':f.id}))['count']==1
        print('MongoDB cycles: crash/retry idempotence and durable event counts OK',flush=True)
        p=ForecastProvider(id='solcast',name='Solcast',site_id='site',kind='solcast',token='private-token',solcast_resource_ids=['roof'])
        now=1795478400.
        results=await asyncio.gather(*(reserve(p,now) for _ in range(12)),return_exceptions=True)
        assert sum(r is None for r in results)==8
        assert sum(isinstance(r,ForecastError) for r in results)==4
        assert 'private-token' not in str(await db.forecast_usage.find({}).to_list())
        await reserve(p,now+86400)
        print('MongoDB quota: concurrent reservations limited to 8/day/token; UTC reset and no stored token OK',flush=True)
        day='2026-11-24';a,b=day_bounds(day,'Europe/Berlin');cutoff=a+300
        pv=Flow(id='pv',name='MPPT',category='pv',pv_type='mppt',direction='in',datapoints={'power_total':'point:pv','energy_total':'point:e'})
        site=ForecastSite(id='site',name='Site',enabled=True,latitude=50,longitude=10,arrays=[{'kwp':5}],actual_flow_ids=['pv'],changed_at=a-86400)
        site.revision=site_revision(site,'Europe/Berlin');p.revision=provider_revision(p)
        await db.forecast_sites.insert_one(site.model_dump());await db.forecast_providers.insert_one(p.model_dump())
        await db.forecast_snapshots.insert_one({'site_id':site.id,'provider_id':p.id,'revision':p.revision,'site_revision':site.revision,'day':day,'raw_kwh':10,'complete':True,'fetched_at':cutoff-100,'family':'solcast','name':p.name})
        await freeze_day(site,[p],[pv],'Europe/Berlin',cutoff+1)
        first=await db.forecast_days.find_one({'site_id':site.id},{'_id':0});assert first['ensemble_kwh']==10
        await db.forecast_snapshots.insert_one({'site_id':site.id,'provider_id':p.id,'revision':p.revision,'site_revision':site.revision,'day':day,'raw_kwh':99,'complete':True,'fetched_at':cutoff+50,'family':'solcast','name':p.name})
        await freeze_day(site,[p],[pv],'Europe/Berlin',cutoff+60)
        assert first==await db.forecast_days.find_one({'id':first['id']},{'_id':0})
        await db.samples.insert_many([{'dp':'point:e','ts':a,'v':100},{'dp':'point:e','ts':b,'v':112}])
        await process_site(site,[p],[pv],settings,b+601)
        evaluated=await db.forecast_days.find_one({'id':first['id']})
        assert evaluated['actual_kwh']==12 and evaluated['eligible'],evaluated
        assert evaluated['errors'][0]['raw_absolute_error']==2
        print('MongoDB forecasts: frozen cutoff survives late updates; actual counter delta and completed-day errors OK',flush=True)
        with patch('lib.forecast.fetch_forecast',AsyncMock(side_effect=ForecastError('Provider unavailable',3600))):
            await refresh_provider(p,site,'Europe/Berlin',b+700)
        state=await db.forecast_state.find_one({'id':p.id});assert state['next_at']==b+4300 and state['error']=='Provider unavailable'
        assert (await db.forecast_days.find_one({'id':first['id']}))['ensemble_kwh']==10
        print('MongoDB provider failure: backoff and existing forecasts retained OK',flush=True)
        # Seed exactly the legacy 2.7.0 unit error; migration must be repeatable.
        from lib.migrations import migrate
        from lib.forecast_model import fingerprint
        legacy=ForecastProvider(id='legacy-vrm',site_id=site.id,name='Renamed provider',kind='vrm',vrm_installation_id='123')
        legacy.revision=fingerprint({'kind':legacy.kind,'site':legacy.site_id,'vrm':legacy.vrm_installation_id,'solcast':[]})
        await db.forecast_providers.insert_one(legacy.model_dump())
        await db.forecast_snapshots.insert_one({'provider_id':legacy.id,'site_id':site.id,'day':day,'revision':legacy.revision,'raw_kwh':38894.84,'family':'solcast','complete':True,'fetched_at':cutoff-100})
        old={'id':'legacy-unit-day','site_id':site.id,'day':'2026-11-23','revision':site.revision,'cutoff':cutoff-86400,'ensemble_kwh':9734.3975,'raw_ensemble_kwh':9734.3975,'actual_kwh':12,'base_eligible':True,'eligible':True,'errors':[],
             'forecasts':[{'provider_id':id,'revision':legacy.revision if id==legacy.id else 'p','name':id,'raw_kwh':value,'used_kwh':value,'candidate_kwh':value,'offset_kwh':0,'weight':weight,'candidate_factor':1,'applied_factor':1} for id,value,weight in [(legacy.id,38894.84,.25),('solcast',10.73,.25),('meteo',16.01,.5)]]}
        await db.forecast_days.insert_one(old)
        energy_before=await db.samples.find({'dp':'point:e'},{'_id':0}).to_list()
        await migrate();await migrate()
        fixed=await db.forecast_days.find_one({'id':old['id']},{'_id':0})
        assert abs(fixed['ensemble_kwh']-20.41121)<1e-8
        assert fixed['vrm_unit_correction_original']['ensemble_kwh']==9734.3975
        assert fixed['actual_kwh']==12 and fixed['eligible']
        snapshot=await db.forecast_snapshots.find_one({'provider_id':legacy.id})
        assert abs(snapshot['raw_kwh']-38.89484)<1e-8 and snapshot['normalization_version']==2
        assert (await db.forecast_providers.find_one({'id':legacy.id}))['revision']==provider_revision(legacy)
        assert (await db.metadata.find_one({'id':'schema'}))['version']==8
        assert energy_before==await db.samples.find({'dp':'point:e'},{'_id':0}).to_list()
        print('MongoDB VRM migration: legacy snapshots/daily blends/errors corrected once, original values audited, physical readings unchanged OK',flush=True)

    finally:
        await client.drop_database(db.name)
        await client.close()
if __name__=='__main__':asyncio.run(main())
