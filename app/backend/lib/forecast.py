"""Isolated PV forecast scheduler; immutable morning predictions and durable quotas."""
import asyncio
import hashlib
import logging
import math
import time
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from lib.db import db
from lib.store import load_flows,load_settings
from lib.forecast_providers import PROVIDERS,ForecastError,fetch_forecast
from lib.forecast_model import site_revision,provider_revision,actual_signature,build_prediction,evaluate_prediction
from models.forecast import ForecastSite,ForecastProvider

logger=logging.getLogger(__name__)
wake=asyncio.Event()

def validate_site(site,flows,points):
    selected=[];seen=set();by_id={f.id:f for f in flows}
    for id in site.actual_flow_ids:
        f=by_id.get(id)
        if not f or f.kind!='device' or f.category!='pv' or f.pv_type=='hybrid' or f.direction!='in':
            raise ValueError('PV-Istquellen müssen PV-Wechselrichter oder DC-MPPTs sein; Hybrid-AC enthält Speicherenergie.')
        if site.measurement_side!='mixed' and f.electrical_side!=site.measurement_side:raise ValueError('Messseite der PV-Istquelle passt nicht zur Anlage.')
        keys=('power_total','power_l1','power_l2','power_l3','energy_total','energy_l1','energy_l2','energy_l3')
        refs={f.datapoints.get(k) for k in keys if f.datapoints.get(k)}
        if not refs or refs&seen:raise ValueError('PV-Istquellen benötigen unterschiedliche Messdatenpunkte ohne Doppelzählung.')
        seen|=refs;selected.append(f)
    if site.curtailment_point:
        point=points.get(site.curtailment_point.removeprefix('point:'))
        if not site.curtailment_point.startswith('point:') or not point or not point.get('record',True) or not point.get('enabled',True) or point.get('unit')!='bool':
            raise ValueError('Abregelung benötigt einen aktiven aufgezeichneten Bool-Messpunkt.')
    return selected

def validate_provider(provider,sites):
    if provider.site_id not in sites:raise ValueError('PV-Anlage fehlt.')
    if provider.enabled and provider.kind=='vrm' and (not provider.token or not provider.vrm_installation_id):raise ValueError('VRM benötigt Installations-ID und persönlichen API-Token.')
    if provider.enabled and provider.kind=='solcast' and (not provider.token or not provider.solcast_resource_ids):raise ValueError('Solcast benötigt Token und mindestens eine Ressourcen-ID.')

async def reserve(provider,now):
    spec=PROVIDERS[provider.kind]
    identity=hashlib.sha256((provider.kind+':'+(provider.token if spec['account'] else 'public')).encode()).hexdigest()
    for duration,limit in ((86400,spec['daily_limit']),(3600,spec['hourly_limit'])):
        bucket=int(now//duration);id=f'{identity}:{duration}:{bucket}'
        try:
            doc=await db.forecast_usage.find_one_and_update({'id':id,'count':{'$lt':limit}},{'$inc':{'count':1},'$setOnInsert':{'expires_at':datetime.fromtimestamp((bucket+1)*duration+90*86400,timezone.utc)}},upsert=True,return_document=ReturnDocument.AFTER)
        except DuplicateKeyError:doc=None
        if not doc:raise ForecastError('Lokales API-Anfragelimit erreicht.',(bucket+1)*duration-now+1)

async def refresh_provider(provider,site,tz,now):
    state=await db.forecast_state.find_one({'id':provider.id}) or {}
    if state.get('next_at',0)>now and state.get('revision')==provider.revision and state.get('site_revision')==site.revision:return
    try:
        days=await fetch_forecast(provider,site,tz,now,reserve)
        # Response completion time, never request start, determines cutoff eligibility.
        fetched=time.time()
        current=await db.forecast_providers.find_one({'id':provider.id})
        current_site=await db.forecast_sites.find_one({'id':site.id})
        if not current or not current_site or current.get('revision')!=provider.revision or current_site.get('revision')!=site.revision:return
        for day,value in days.items():
            kwh=value['kwh']
            if not math.isfinite(kwh) or kwh<0:raise ForecastError('Ungültiger Prognosewert.')
            await db.forecast_snapshots.insert_one({'provider_id':provider.id,'site_id':site.id,'day':day,'revision':provider.revision,'site_revision':site.revision,'fetched_at':fetched,'raw_kwh':kwh,'complete':value['complete'],'coverage':value['coverage'],'family':PROVIDERS[provider.kind]['family'],'name':provider.name,'provider_kind':provider.kind,'normalization_version':2})
        await db.forecast_state.replace_one({'id':provider.id},{'id':provider.id,'revision':provider.revision,'site_revision':site.revision,'last_success':fetched,'last_attempt':now,'next_at':fetched+6*3600,'error':''},upsert=True)
    except ForecastError as exc:
        await db.forecast_state.update_one({'id':provider.id},{'$set':{'revision':provider.revision,'site_revision':site.revision,'last_attempt':now,'next_at':now+exc.retry_after,'error':str(exc)}},upsert=True)

def day_bounds(day,tz):
    date=datetime.fromisoformat(day).date();zone=ZoneInfo(tz)
    return datetime.combine(date,datetime.min.time(),zone).timestamp(),datetime.combine(date+timedelta(days=1),datetime.min.time(),zone).timestamp()

async def estimates_for(site,providers,day,before):
    out=[]
    for p in providers:
        doc=await db.forecast_snapshots.find_one({'site_id':site.id,'provider_id':p.id,'day':day,'revision':p.revision,'site_revision':site.revision,'fetched_at':{'$lte':before,'$gte':before-18*3600},'complete':True},{'_id':0},sort=[('fetched_at',-1)])
        if doc:
            doc.update(manual_weight=p.manual_weight,dependency_group=p.dependency_group,provider_kind=p.kind)
            out.append(doc)
    return out

async def freeze_day(site,providers,flows,tz,now):
    local=datetime.fromtimestamp(now,ZoneInfo(tz));day=local.date().isoformat()
    cutoff=datetime.fromisoformat(day+'T'+site.freeze_time).replace(tzinfo=ZoneInfo(tz)).timestamp()
    if now<cutoff:return
    id=site.id+':'+day
    if await db.forecast_days.find_one({'id':id}):return
    records=await db.forecast_days.find({'site_id':site.id,'day':{'$lt':day}},{'_id':0}).sort('day',-1).limit(site.training_days+1).to_list()
    estimates=await estimates_for(site,providers,day,cutoff)
    selected=[f for f in flows if f.id in site.actual_flow_ids]
    signature=actual_signature(selected,await db.measurements.find({}, {'_id':0}).to_list(),[site.curtailment_point])
    records=[r for r in records if r.get('source_signature')==signature]
    prediction=build_prediction(site,day,cutoff,estimates,records)
    record={'id':id,'site_id':site.id,'day':day,'timezone':tz,'revision':site.revision,'source_signature':signature,'cutoff':cutoff,'frozen_at':now,'site_changed_at':site.changed_at,**prediction}
    await db.forecast_days.update_one({'id':id},{'$setOnInsert':record},upsert=True)

async def measured_actual(site,flows,settings,start,end):
    from lib.energy import compute_flow
    from lib.sources import LiveSource
    selected=[f for f in flows if f.id in site.actual_flow_ids]
    if len(selected)!=len(site.actual_flow_ids):return None,False,'PV-Istquelle fehlt.'
    src=LiveSource(settings);values=[];complete=True
    for f in selected:
        result=await compute_flow(f,src,start,end,max(settings.recorder.interval_s,60),settings.gap_threshold_min*60)
        v=result.total;values.append(v.kwh);complete=complete and v.complete and v.coverage>=.98
    actual=sum(values) if all(v is not None and math.isfinite(v) and v>=0 for v in values) else None
    reason='' if complete and actual is not None else 'Messhistorie unvollständig.'
    if site.curtailment_point:
        from models.flow import Flow,Datapoints
        proxy=Flow(name='Abregelung',datapoints=Datapoints(power_total=site.curtailment_point))
        check=await src.recorded_integral(proxy,start,end,max(30,settings.recorder.interval_s*3))
        if not check or not check.complete:complete=False;reason='Abregelungssignal unvollständig.'
        elif check.kwh and check.kwh>0:complete=False;reason='Abregelung erkannt; Tag vom Lernen ausgeschlossen.'
    return actual,complete,reason

async def process_site(site,providers,flows,settings,now):
    tz=site.timezone or settings.timezone
    await freeze_day(site,providers,flows,tz,now)
    pending=await db.forecast_days.find({'site_id':site.id,'evaluated_at':{'$exists':False}},{'_id':0}).sort('day',1).limit(10).to_list()
    selected=[f for f in flows if f.id in site.actual_flow_ids]
    signature=actual_signature(selected,await db.measurements.find({}, {'_id':0}).to_list(),[site.curtailment_point])
    for row in pending:
        a,b=day_bounds(row['day'],row['timezone'])
        if now<b+600:continue
        if row['revision']!=site.revision or row.get('source_signature')!=signature or row.get('site_changed_at',0)>row['cutoff']:
            patch=evaluate_prediction(row,None,False,'PV-Konfiguration während oder nach dem Prognosetag geändert.')
        else:
            actual,complete,reason=await measured_actual(site,flows,settings,a,b)
            patch=evaluate_prediction(row,actual,complete,reason)
        patch['evaluated_at']=now
        await db.forecast_days.update_one({'id':row['id'],'evaluated_at':{'$exists':False}},{'$set':patch})
    cache=await db.forecast_actuals.find_one({'id':site.id}) or {}
    day=datetime.fromtimestamp(now,ZoneInfo(tz)).date().isoformat()
    if now-cache.get('updated_at',0)>=300:
        start,_=day_bounds(day,tz)
        if now>start+1:
            actual,complete,reason=await measured_actual(site,flows,settings,start,now)
            await db.forecast_actuals.replace_one({'id':site.id},{'id':site.id,'day':day,'kwh':actual,'complete':complete,'reason':reason,'updated_at':now},upsert=True)

async def forecast_tick(now=None):
    from lib.config_lock import config_lock
    now=now or time.time()
    async with config_lock:
        settings=await load_settings();flows=await load_flows()
        sites=[ForecastSite(**v) for v in await db.forecast_sites.find({'enabled':True},{'_id':0}).to_list()]
        points={p['id']:p for p in await db.measurements.find({},{'_id':0}).to_list()}
        all_providers=[ForecastProvider(**v) for v in await db.forecast_providers.find({'enabled':True},{'_id':0}).to_list()]
    for site in sites:
        try:
            current_revision=site_revision(site,site.timezone or settings.timezone)
            if site.revision!=current_revision:
                site.revision=current_revision;site.changed_at=now
                await db.forecast_sites.update_one({'id':site.id},{'$set':{'revision':current_revision,'changed_at':now}})
            validate_site(site,flows,points)
            providers=[p for p in all_providers if p.site_id==site.id]
            # Freeze before HTTP: a late response cannot become a morning forecast.
            await process_site(site,providers,flows,settings,now)
            for provider in providers:await refresh_provider(provider,site,site.timezone or settings.timezone,now)
            await db.forecast_actuals.update_one({'id':site.id},{'$unset':{'error':''}})
        except Exception:
            logger.exception('PV-Prognose konnte nicht verarbeitet werden (Anlage %s).',site.id)
            await db.forecast_actuals.update_one({'id':site.id},{'$set':{'error':'PV-Prognose prüfen: Konfiguration oder Messhistorie nicht verfügbar.'}},upsert=True)

async def forecast_loop():
    while True:
        try:await forecast_tick()
        except asyncio.CancelledError:raise
        except Exception:logger.exception('PV-Prognosedienst: Verarbeitung fehlgeschlagen.')
        try:await asyncio.wait_for(wake.wait(),60)
        except asyncio.TimeoutError:pass
        wake.clear()
