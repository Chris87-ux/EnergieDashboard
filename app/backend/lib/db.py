import os

from pymongo import ASCENDING, DESCENDING, AsyncMongoClient, IndexModel

client = AsyncMongoClient(
    os.getenv("MONGO_URL", "mongodb://127.0.0.1:27017"),
    serverSelectionTimeoutMS=5000,
    tz_aware=True,
)
db = client[os.getenv("DB_NAME", "energieboard")]


async def ensure_indexes() -> None:
    info = await client.admin.command("buildInfo")
    if info["versionArray"][0] < 5:
        raise RuntimeError("Für die Historienberechnung ist MongoDB ab Version 5.0 erforderlich.")
    await db.flows.create_indexes([
        IndexModel([("id", ASCENDING)], name="id", unique=True),
        IndexModel([("enabled", ASCENDING), ("sort_order", ASCENDING), ("created_at", ASCENDING)], name="enabled_sort"),
    ])
    await db.visibility.create_index("id", unique=True)
    await db.config_backups.create_index("id", unique=True)
    await db.cycle_states.create_index("id", unique=True)
    await db.cycle_events.create_index("id", unique=True)
    await db.cycle_events.create_index([("device_id",1),("outcome",1),("ended_at",-1)])
    for collection in ('forecast_sites','forecast_providers','forecast_days','forecast_actuals','forecast_state','forecast_usage'):
        await db[collection].create_index('id',unique=True)
    await db.forecast_usage.create_index('expires_at',expireAfterSeconds=0)
    await db.forecast_providers.create_index([('site_id',1),('kind',1)],unique=True)
    await db.forecast_snapshots.create_index([('site_id',1),('provider_id',1),('day',1),('fetched_at',-1)])
    await db.forecast_days.create_index([('site_id',1),('day',-1)])
    await db.forecast_exclusions.create_index([('day_id',1),('changed_at',1)])
    await db.charts.create_index("id", unique=True)
    await db.consumer_groups.create_index("id", unique=True)
    await db.connections.create_index("id", unique=True)
    await db.measurements.create_index("id", unique=True)
    await db.metadata.create_index("id", unique=True)
    await db.settings.create_index("id", name="id", unique=True)
    await db.samples.create_index([("dp", ASCENDING), ("ts", DESCENDING)], name="dp_ts")
