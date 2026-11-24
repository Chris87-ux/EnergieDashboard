from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter,HTTPException,Query
from lib.db import db
from lib.store import load_flows,load_settings
from lib.config_lock import locked
from lib.sources import LiveSource
from lib.charts import source_catalog,validate_chart,chart_report
from models.charts import ChartConfig

router=APIRouter(tags=["Charts"])

async def sources():
    return source_catalog(await load_flows(),await db.measurements.find({}, {"_id":0}).to_list())

@router.get("/chart-sources")
@locked
async def available_sources():return await sources()

@router.get("/charts",response_model=list[ChartConfig])
@locked
async def list_charts():
    return await db.charts.find({}, {"_id":0}).sort([("sort_order",1),("name",1)]).to_list()

@router.put("/charts/{id}",response_model=ChartConfig)
@locked
async def save_chart(id:str,body:ChartConfig):
    try:validate_chart(body,await sources())
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    body.id=id
    await db.charts.replace_one({"id":id},body.model_dump(),upsert=True)
    return body

@router.delete("/charts/{id}",status_code=204)
@locked
async def delete_chart(id:str):
    if not (await db.charts.delete_one({"id":id})).deleted_count:raise HTTPException(404,"Chart nicht gefunden.")

@router.get("/charts/{id}/data")
@locked
async def data(id:str,start:str,end:str,points:int=Query(default=480,ge=60,le=1000)):
    doc=await db.charts.find_one({"id":id},{"_id":0})
    if not doc:raise HTTPException(404,"Chart nicht gefunden.")
    settings=await load_settings()
    try:
        a,b=datetime.fromisoformat(start),datetime.fromisoformat(end)
        if a.tzinfo is None:a=a.replace(tzinfo=ZoneInfo(settings.timezone))
        if b.tzinfo is None:b=b.replace(tzinfo=ZoneInfo(settings.timezone))
        first,last=a.timestamp(),b.timestamp()
        if not 0<last-first<=400*86400:raise ValueError()
        last=min(last,datetime.now(timezone.utc).timestamp())
        if last<=first:raise ValueError()
    except (ValueError,OverflowError):raise HTTPException(400,"Gültigen Zeitraum von höchstens 400 Tagen wählen.")
    return await chart_report(ChartConfig(**doc),await load_flows(),await db.measurements.find({}, {"_id":0}).to_list(),LiveSource(settings),first,last,points)
