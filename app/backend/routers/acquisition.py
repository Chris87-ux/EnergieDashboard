from fastapi import APIRouter, HTTPException
from lib.db import db
from lib.store import load_settings
from lib.acquisition import read_measurements
from models.acquisition import Connection, Measurement, API_PRESETS, validate_measurement

from lib.config_lock import locked

router = APIRouter(tags=["Datenerfassung"])


@router.get("/connections")
@locked
async def connections():
    docs = await db.connections.find({}, {"_id": 0}).to_list()
    return [{**Connection(**d).model_dump(), "password": "", "token":"", "password_set": bool(d.get("password")), "token_set":bool(d.get("token"))} for d in docs]


@router.put("/connections/{id}")
@locked
async def save_connection(id: str, body: Connection):
    old = await db.connections.find_one({"id": id})
    body.id = id
    if old and not body.password:
        body.password = old.get("password", "")
    if body.clear_token:body.token=""
    elif old and not body.token:body.token=old.get("token","")
    await db.connections.replace_one({"id": id}, body.model_dump(), upsert=True)
    return {**body.model_dump(), "password": "", "token":"", "password_set": bool(body.password), "token_set":bool(body.token)}


@router.delete("/connections/{id}", status_code=204)
@locked
async def delete_connection(id: str):
    if await db.measurements.find_one({"connection_id": id}):
        raise HTTPException(409, "Zuerst die zugeordneten Messpunkte verschieben oder löschen.")
    await db.connections.delete_one({"id": id})


@router.get("/measurements")
@locked
async def measurements():
    return await db.measurements.find({}, {"_id": 0}).to_list()


@router.put("/measurements/{id}")
@locked
async def save_measurement(id: str, body: Measurement):
    if not await db.connections.find_one({"id": body.connection_id}):
        raise HTTPException(422, "Verbindung existiert nicht.")
    connection = await db.connections.find_one({"id": body.connection_id})
    try:validate_measurement(Connection(**connection),body)
    except ValueError as exc:raise HTTPException(422,str(exc)) from exc
    old = await db.measurements.find_one({"id": id})
    body.id = id
    if await db.forecast_sites.find_one({'curtailment_point':'point:'+id}) and (body.unit!='bool' or not body.enabled or not body.record):
        raise HTTPException(409,'Zuerst das Abregelungssignal in der PV-Prognose ändern.')
    body.history_key = old.get("history_key", "") if old else ""
    body.legacy_until = old.get("legacy_until") if old else None
    await db.measurements.replace_one({"id": id}, body.model_dump(), upsert=True)
    return body


@router.delete("/measurements/{id}", status_code=204)
@locked
async def delete_measurement(id: str):
    if await db.forecast_sites.find_one({"curtailment_point":"point:"+id}):raise HTTPException(409,"Messpunkt wird noch als Abregelungssignal verwendet.")
    if await db.charts.find_one({"series":{"$elemMatch":{"kind":"measurement","reference_id":id}}}):
        raise HTTPException(409,"Messpunkt wird noch in einem Chart verwendet.")
    for flow in await db.flows.find({}, {"_id": 0}).to_list():
        if "point:" + id in flow.get("datapoints", {}).values() or flow.get("cycle_tracking",{}).get("signal_point")=="point:"+id:
            raise HTTPException(409, "Messpunkt wird noch von einem Gerät verwendet.")
    await db.measurements.delete_one({"id": id})


@router.get("/measurements/live")
@locked
async def preview_measurements():
    _, errors, states = await read_measurements(await load_settings(), force=True)
    return {"states": states, "errors": errors}


@router.get("/schemas/measurement")
async def measurement_schema():
    return Measurement.model_json_schema()


@router.get("/api-presets")
async def api_presets():
    return API_PRESETS
