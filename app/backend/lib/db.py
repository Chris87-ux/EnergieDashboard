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
    await db.connections.create_index("id", unique=True)
    await db.measurements.create_index("id", unique=True)
    await db.metadata.create_index("id", unique=True)
    await db.settings.create_index("id", name="id", unique=True)
    await db.samples.create_index([("dp", ASCENDING), ("ts", DESCENDING)], name="dp_ts")
