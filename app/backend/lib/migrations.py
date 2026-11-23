"""Idempotent additive migration. Historical sample keys and all IDs are retained."""
import hashlib
import time
from lib.db import db
from models.acquisition import Connection, Measurement


async def migrate():
    version = await db.metadata.find_one({"id": "schema"})
    if version and version.get("version", 0) > 6:
        raise RuntimeError("Die Datenbank stammt aus einer neueren Version. Passende Sicherung wiederherstellen.")
    settings = await db.settings.find_one({"id": "app"})
    docs = await db.flows.find({}, {"_id": 0}).to_list()
    legacy = sorted({value for doc in docs for value in doc.get("datapoints", {}).values()
                     if isinstance(value, str) and value and not value.startswith(("point:", "energieboard:"))})
    io = (settings or {}).get("iobroker", {})
    if legacy and io.get("host"):
        connection = Connection(id="legacy-iobroker", name="ioBroker (übernommen)", protocol="iobroker",
            host=io["host"], port=io.get("port", 8087), tls=io.get("protocol") == "https")
        await db.connections.update_one({"id": connection.id}, {"$setOnInsert": connection.model_dump()}, upsert=True)
        mapping = {}
        for address in legacy:
            unit = next((doc.get("power_unit", "W") if key.startswith("power") else doc.get("energy_unit", "kWh") if key.startswith("energy") else "%" if key == "soc" else "bool" if key == "run" else "Hz"
                for doc in docs for key, value in doc.get("datapoints", {}).items() if value == address), "W")
            point = Measurement(id=hashlib.sha256(address.encode()).hexdigest()[:24], name=address[:100],
                connection_id=connection.id, address=address, history_key=address, unit=unit, legacy_until=time.time())
            await db.measurements.update_one({"id": point.id}, {"$setOnInsert": point.model_dump()}, upsert=True)
            mapping[address] = "point:" + point.id
        for doc in docs:
            datapoints = {key: mapping.get(value, value) for key, value in doc.get("datapoints", {}).items()}
            await db.flows.update_one({"id": doc["id"]}, {"$set": {"datapoints": datapoints, "schema_version": 6}})
    await db.flows.update_many({"category":"grid","kind":{"$ne":"grid"}}, {"$set":{"kind":"grid","schema_version":6}})
    await db.flows.update_many({"kind":{"$in":["grid","storage"]}}, {"$set":{"category":"custom","schema_version":6}})
    await db.flows.update_many({"kind":"storage","electrical_side":{"$exists":False}}, {"$set":{"electrical_side":"dc"}})
    await db.flows.update_many({"kind":"device","category":"pv","pv_type":"mppt"}, {"$set":{"electrical_side":"dc","power_phase_mode":"single","energy_phase_mode":"single","direction":"in","schema_version":6}})
    for doc in await db.connections.find({"protocol":"iobroker"}, {"_id":0}).to_list():
        await db.connections.update_one({"id":doc["id"]},{"$set":Connection(**doc).model_dump()})
    await db.flows.update_many({"group_id":{"$exists":False}}, {"$set":{"group_id":None}})
    await db.flows.update_many({}, {"$set":{"schema_version":6}})
    await db.metadata.update_one({"id": "schema"}, {"$set": {"version": 6}}, upsert=True)
