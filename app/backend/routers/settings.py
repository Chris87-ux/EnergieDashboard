from fastapi import APIRouter

import httpx

from lib.db import db
from lib.recorder import STATUS, request_recheck
from lib.sources import _esc, _v1_query, _v2_query, iob_base, iob_get_bulk, influx_has_recent
from lib.store import all_datapoints, keep_secrets, load_flows, load_settings, save_settings, to_out
from models.settings import AppSettings, RecorderStatus, SettingsOut, TestResult

from lib.config_lock import locked

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsOut)
@locked
async def get_settings():
    return to_out(await load_settings())


@router.put("/settings", response_model=SettingsOut)
@locked
async def put_settings(body: AppSettings):
    merged = keep_secrets(body, await load_settings())
    await save_settings(merged)
    request_recheck()
    return to_out(merged)


@router.post("/settings/test/iobroker", response_model=TestResult)
async def test_iobroker(body: AppSettings):
    s = keep_secrets(body, await load_settings())
    if not s.iobroker.host:
        return TestResult(ok=False, message="Bitte Host bzw. IP-Adresse von ioBroker angeben.")
    dps = all_datapoints(await load_flows(enabled_only=True))
    try:
        if not dps:
            async with httpx.AsyncClient(timeout=s.iobroker.timeout_s) as c:
                r = await c.get(f"{iob_base(s)}/help")
                r.raise_for_status()
            return TestResult(ok=True, message="simple-api erreichbar (keine Datenpunkte konfiguriert).")
        values = await iob_get_bulk(s, dps)
    except Exception as exc:
        return TestResult(ok=False, message=f"Keine Verbindung zu {iob_base(s)}", details=[str(exc)])
    found = [dp for dp in dps if values.get(dp) is not None]
    missing = [dp for dp in dps if dp not in found]
    return TestResult(
        ok=bool(found),
        message=f"Verbunden – {len(found)} von {len(dps)} Datenpunkten liefern Werte.",
        details=[f"Ohne Wert: {dp}" for dp in missing[:30]],
    )


@router.post("/settings/test/influx", response_model=TestResult)
async def test_influx(body: AppSettings):
    s = keep_secrets(body, await load_settings())
    try:
        if s.influx.version == "v1":
            rows = await _v1_query(s, "SHOW MEASUREMENTS LIMIT 1000")
            info = f"InfluxDB 1.x – Datenbank „{s.influx.database}“ mit {len(rows)} Measurements"
        else:
            await _v2_query(s, f'from(bucket: "{_esc(s.influx.bucket)}") |> range(start: -1s) |> limit(n: 1)')
            info = f"InfluxDB 2.x – Bucket „{s.influx.bucket}“ erreichbar"
    except Exception as exc:
        return TestResult(ok=False, message="Keine Verbindung zur InfluxDB", details=[str(exc)])
    dps = all_datapoints(await load_flows(enabled_only=True))[:25]
    with_history = []
    for dp in dps:
        try:
            if await influx_has_recent(s, dp):
                with_history.append(dp)
        except Exception:
            pass
    return TestResult(
        ok=True,
        message=info,
        details=[f"{len(with_history)} von {len(dps)} geprüften Datenpunkten haben Historie (3 Tage)"]
        + [f"Ohne Historie (wird aufgezeichnet): {dp}" for dp in dps if dp not in with_history],
    )


@router.get("/recorder/status", response_model=RecorderStatus)
async def recorder_status():
    STATUS.samples_total = await db.samples.estimated_document_count()
    return STATUS
