from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter,HTTPException,Query
from lib.db import db
from lib.store import load_flows,load_settings
from lib.config_lock import locked
from models.cycles import CYCLE_PRESETS
from lib.cycles import UNKNOWN,OFF,READY

router=APIRouter(tags=["Gerätezyklen"])

@router.get("/cycles/presets")
async def presets():return CYCLE_PRESETS

@router.get("/cycles/status")
@locked
async def statuses():
    settings=await load_settings();now=datetime.now(timezone.utc).timestamp()
    zone=ZoneInfo(settings.timezone);local=datetime.now(zone)
    today=local.replace(hour=0,minute=0,second=0,microsecond=0).timestamp()
    month=local.replace(day=1,hour=0,minute=0,second=0,microsecond=0).timestamp()
    flows=[f for f in await load_flows(enabled_only=True) if f.kind=="device" and f.direction=="out" and f.cycle_tracking.enabled]
    states={s['id']:s for s in await db.cycle_states.find({}, {"_id":0}).to_list()}
    cursor=await db.cycle_events.aggregate([{"$match":{"outcome":"completed"}},{"$group":{"_id":"$device_id","count":{"$sum":1},"today":{"$sum":{"$cond":[{"$gte":["$ended_at",today]},1,0]}},"month":{"$sum":{"$cond":[{"$gte":["$ended_at",month]},1,0]}}}}])
    counts={c['_id']:c for c in await cursor.to_list()};out=[]
    for flow in flows:
        state=states.get(flow.id,{})
        valid=state.get('last_valid',0)
        status=state.get('status',UNKNOWN) if settings.recorder.enabled and now-valid<=max(3*settings.recorder.interval_s,30) else UNKNOWN
        out.append({"id":flow.id,"name":flow.name,"profile":flow.cycle_tracking.profile,"status":status,"count":counts.get(flow.id,{}).get('count',0),"today":counts.get(flow.id,{}).get('today',0),"month":counts.get(flow.id,{}).get('month',0),"started_at":state.get('started_at'),"runtime_s":max(0,now-state['started_at']) if state.get('started_at') is not None else None,"runtime_alarm":bool(state.get('runtime_alarm')),"had_gap":bool(state.get('had_gap')),"mean_w":state.get('mean_w'),"last_valid":valid or None})
    return out

@router.get("/cycles/{id}/events")
@locked
async def events(id:str,limit:int=Query(default=20,ge=1,le=200)):
    return await db.cycle_events.find({"device_id":id},{"_id":0}).sort("detected_at",-1).limit(limit).to_list()

@router.post("/cycles/{id}/ack")
@locked
async def acknowledge(id:str):
    state=await db.cycle_states.find_one({"id":id})
    if not state:raise HTTPException(404,"Kein Gerätestatus vorhanden.")
    if state.get('finished'):
        await db.cycle_states.update_one({"id":id},{"$set":{"finished":False,"status":OFF if state.get('last_power',0)<=0.5 else READY}})
    return {"ok":True}
