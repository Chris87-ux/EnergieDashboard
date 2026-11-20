from fastapi import APIRouter, HTTPException
from lib.db import db
from lib.store import load_settings
from lib.acquisition import read_measurements
from models.acquisition import Connection, Measurement

from lib.config_lock import locked

router = APIRouter(tags=["Datenerfassung"])


@router.get("/connections")
@locked
async def connections():
    docs = await db.connections.find({}, {"_id": 0}).to_list()
    return [{**d, "password": "", "password_set": bool(d.get("password"))} for d in docs]


@router.put("/connections/{id}")
@locked
async def save_connection(id: str, body: Connection):
    old = await db.connections.find_one({"id": id})
    body.id = id
    if old and not body.password:
        body.password = old.get("password", "")
    await db.connections.replace_one({"id": id}, body.model_dump(), upsert=True)
    return {**body.model_dump(), "password": "", "password_set": bool(body.password)}


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
    if connection["protocol"] != "modbus" and (not body.address or "+" in body.address or "#" in body.address):
        raise HTTPException(422, "Eine konkrete Datenpunkt-ID bzw. ein Topic ohne Wildcards angeben.")
    old = await db.measurements.find_one({"id": id})
    body.id = id
    body.history_key = old.get("history_key", "") if old else ""
    body.legacy_until = old.get("legacy_until") if old else None
    await db.measurements.replace_one({"id": id}, body.model_dump(), upsert=True)
    return body


@router.delete("/measurements/{id}", status_code=204)
@locked
async def delete_measurement(id: str):
    for flow in await db.flows.find({}, {"_id": 0}).to_list():
        if "point:" + id in flow.get("datapoints", {}).values():
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
