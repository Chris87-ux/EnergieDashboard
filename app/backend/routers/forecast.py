"""Private-use PV forecasting configuration and transparent score reports."""
import time
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from lib.db import db
from lib.config_lock import locked
from lib.store import load_flows,load_settings
from lib.forecast import validate_site,validate_provider,wake,estimates_for
from lib.forecast_model import site_revision,provider_revision,build_prediction,actual_signature
from lib.forecast_providers import PROVIDERS
from models.forecast import ForecastSite,ForecastProvider

router=APIRouter(tags=['PV-Prognose'])

def public_provider(doc):
    out=ForecastProvider(**doc).model_dump();out['token_set']=bool(out.get('token'));out['token']='';return out

@router.get('/forecast/config')
@locked
async def config():
    return {'sites':[ForecastSite(**s).model_dump() for s in await db.forecast_sites.find({},{'_id':0}).to_list()],'providers':[public_provider(p) for p in await db.forecast_providers.find({},{'_id':0}).to_list()],'catalog':PROVIDERS}

@router.put('/forecast/sites/{id}')
@locked
async def save_site(id:str,body:ForecastSite):
    settings=await load_settings();flows=await load_flows();points={p['id']:p for p in await db.measurements.find({},{'_id':0}).to_list()}
    try:validate_site(body,flows,points)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    old=await db.forecast_sites.find_one({'id':id}) or {};body.id=id
    body.revision=site_revision(body,body.timezone or settings.timezone)
    body.changed_at=time.time() if body.revision!=old.get('revision') else old.get('changed_at',0)
    await db.forecast_sites.replace_one({'id':id},body.model_dump(),upsert=True);wake.set()
    return body

@router.delete('/forecast/sites/{id}',status_code=204)
@locked
async def delete_site(id:str):
    if await db.forecast_providers.find_one({'site_id':id}):raise HTTPException(409,'Zuerst die Prognosequellen dieser Anlage entfernen.')
    if not (await db.forecast_sites.delete_one({'id':id})).deleted_count:raise HTTPException(404,'PV-Anlage nicht gefunden.')

@router.put('/forecast/providers/{id}')
@locked
async def save_provider(id:str,body:ForecastProvider):
    old=await db.forecast_providers.find_one({'id':id}) or {};body.id=id
    if not body.token and not body.clear_token:body.token=old.get('token','')
    if body.clear_token:body.token=''
    if body.kind not in ('vrm','solcast'):body.token=''
    sites={s['id']:s for s in await db.forecast_sites.find({},{'_id':0}).to_list()}
    try:validate_provider(body,sites)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    if await db.forecast_providers.find_one({'site_id':body.site_id,'kind':body.kind,'id':{'$ne':id}}):raise HTTPException(409,'Je Anbieter und Anlage nur eine Prognosequelle anlegen; Solcast unterstützt darin zwei Dachflächen.')
    body.revision=provider_revision(body);body.changed_at=time.time() if body.revision!=old.get('revision') else old.get('changed_at',0)
    await db.forecast_providers.replace_one({'id':id},body.model_dump(),upsert=True)
    if body.token!=old.get('token','') or body.enabled!=old.get('enabled',False):
        await db.forecast_state.update_one({'id':id},{'$set':{'next_at':0}},upsert=True)
    wake.set()
    return public_provider(body.model_dump())

@router.delete('/forecast/providers/{id}',status_code=204)
@locked
async def delete_provider(id:str):
    if not (await db.forecast_providers.delete_one({'id':id})).deleted_count:raise HTTPException(404,'Prognosequelle nicht gefunden.')

@router.post('/forecast/refresh')
@locked
async def refresh():
    # Queue only. Provider quotas and Retry-After still apply to manual requests.
    now=time.time()
    await db.forecast_state.update_many({'error':'','last_success':{'$lt':now-900}},{'$set':{'next_at':now}})
    wake.set();return {'queued':True}

class Exclusion(BaseModel):
    excluded:bool
    reason:str=Field(default='',max_length=300)

@router.put('/forecast/days/{id}/exclusion')
@locked
async def exclusion(id:str,body:Exclusion):
    row=await db.forecast_days.find_one({'id':id})
    if not row:raise HTTPException(404,'Prognosetag nicht gefunden.')
    if body.excluded and not body.reason.strip():raise HTTPException(422,'Bitte einen Ausschlussgrund angeben.')
    now=time.time()
    # Audit every change. Training uses the exclusion history as it existed at cutoff.
    await db.forecast_exclusions.insert_one({'day_id':id,'changed_at':now,'excluded':body.excluded,'reason':body.reason.strip()})
    await db.forecast_days.update_one({'id':id},{'$push':{'exclusion_log':{'changed_at':now,'excluded':body.excluded,'reason':body.reason.strip()}},'$set':{'excluded_at':now if body.excluded else None,'exclusion_reason':body.reason.strip() if body.excluded else '', 'eligible':bool(row.get('base_eligible') and not body.excluded)}})
    return {'ok':True}

@router.get('/forecast/report')
async def report():
    settings=await load_settings();now=time.time();out=[]
    for doc in await db.forecast_sites.find({},{'_id':0}).to_list():
        site=ForecastSite(**doc);zone=ZoneInfo(site.timezone or settings.timezone);today=datetime.fromtimestamp(now,zone).date()
        providers=[ForecastProvider(**v) for v in await db.forecast_providers.find({'site_id':site.id,'enabled':True},{'_id':0}).to_list()]
        history=await db.forecast_days.find({'site_id':site.id},{'_id':0}).sort('day',-1).limit(120).to_list()
        selected=[f for f in await load_flows() if f.id in site.actual_flow_ids]
        signature=actual_signature(selected,await db.measurements.find({}, {'_id':0}).to_list(),[site.curtailment_point])
        training=[r for r in history if r.get('source_signature')==signature]
        latest={}
        for day in (today.isoformat(),(today+timedelta(days=1)).isoformat()):
            estimates=await estimates_for(site,providers,day,now)
            latest[day]=build_prediction(site,day,now,estimates,training)
        scored=[r for r in history if r.get('eligible') and r.get('revision')==site.revision]
        ranking=[]
        for p in providers:
            matching=[r for r in scored if any(f['provider_id']==p.id and f.get('revision')==p.revision for f in r.get('forecasts',[]))]
            errors=[e for r in matching for e in r.get('errors',[]) if e['provider_id']==p.id]
            n=len(errors)
            state=await db.forecast_state.find_one({'id':p.id},{'_id':0}) or {}
            ranking.append({'id':p.id,'name':p.name,'kind':p.kind,'days':n,'raw_mae':sum(e['raw_absolute_error'] for e in errors)/n if n else None,'used_mae':sum(e['used_absolute_error'] for e in errors)/n if n else None,'wins':sum(r.get('winner_provider_id')==p.id for r in matching),'state':state})
        paired=[r for r in scored if r.get('ensemble_absolute_error') is not None]
        out.append({'site':doc,'today':today.isoformat(),'latest':latest,'days':history,'actual':await db.forecast_actuals.find_one({'id':site.id},{'_id':0}),'ranking':ranking,'ensemble_mae':sum(r['ensemble_absolute_error'] for r in paired)/len(paired) if paired else None,'scored_days':len(paired)})
    return {'sites':out,'updated_at':now}
