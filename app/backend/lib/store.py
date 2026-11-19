"""Settings + flow persistence helpers shared by routers and the recorder."""

from lib.db import db
from models.flow import Flow
from models.settings import AppSettings, SettingsOut

SETTINGS_ID = "app"


async def load_settings() -> AppSettings:
    doc = await db.settings.find_one({"id": SETTINGS_ID}, {"_id": 0, "id": 0})
    return AppSettings(**doc) if doc else AppSettings()


async def save_settings(settings: AppSettings) -> None:
    await db.settings.replace_one(
        {"id": SETTINGS_ID}, {"id": SETTINGS_ID, **settings.model_dump()}, upsert=True
    )


def keep_secrets(new: AppSettings, old: AppSettings) -> AppSettings:
    """Blank secret fields in a submitted form mean 'keep the stored value'."""
    if not new.influx.password:
        new.influx.password = old.influx.password
    if not new.influx.token:
        new.influx.token = old.influx.token
    return new


def to_out(settings: AppSettings) -> SettingsOut:
    data = settings.model_dump()
    data["influx"]["password"] = ""
    data["influx"]["token"] = ""
    return SettingsOut(
        **data,
        influx_password_set=bool(settings.influx.password),
        influx_token_set=bool(settings.influx.token),
    )


async def load_flows(enabled_only: bool = False) -> list[Flow]:
    query = {"enabled": True} if enabled_only else {}
    docs = await db.flows.find(query, {"_id": 0}).sort([("sort_order", 1), ("created_at", 1)]).to_list()
    flows = [Flow(**d) for d in docs]
    if enabled_only:
        nodes = {flow.id for flow in flows if flow.kind == "node"}
        flows = [flow for flow in flows if not flow.parent_id or flow.parent_id in nodes]
    return flows


def all_datapoints(flows: list[Flow]) -> list[str]:
    ids: set[str] = set()
    for flow in flows:
        keys = flow.datapoints.model_dump()
        if flow.kind == "storage":
            keys = {"power_total": "", "soc": ""}
        elif flow.run_power_w is not None:
            keys = {"run": ""}
        ids.update(flow.datapoints.get(key) for key in keys if flow.datapoints.get(key))
    return sorted(ids)
