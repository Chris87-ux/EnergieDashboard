"""Record configured states and derived RUN/storage channels in MongoDB."""

import asyncio
import logging
import time
from datetime import datetime, timezone

from lib.db import db
from lib.sources import iob_get_bulk
from lib.topology import derived_samples
from lib.store import all_datapoints, load_flows, load_settings
from models.settings import RecorderStatus

from lib.config_lock import locked

logger = logging.getLogger(__name__)

STATUS = RecorderStatus()
_wake = asyncio.Event()


def request_recheck() -> None:
    _wake.set()


def _set(state: str, message: str) -> None:
    STATUS.state = state  # type: ignore[assignment]
    STATUS.message = message


@locked
async def _tick() -> int:
    s = await load_settings()
    if not s.recorder.enabled:
        _set("disabled", "Aufzeichnung ist deaktiviert")
        return s.recorder.interval_s
    flows = await load_flows(enabled_only=True)
    registry = await db.measurements.find({}, {"_id":0}).to_list()
    dps = tuple(sorted(set(all_datapoints(flows)) | {"point:"+p["id"] for p in registry if p.get("enabled",True) and p.get("record",True)}))
    if not dps:
        STATUS.influx_dps = []
        STATUS.recorded_dps = []
        _set("waiting", "Noch keine aktiven Datenpunkte konfiguriert")
        return s.recorder.interval_s
    STATUS.last_error = None
    missing = list(dps)
    STATUS.influx_dps = []
    STATUS.recorded_dps = missing
    if missing:
        from lib.acquisition import read_values
        values, errors = await read_values(s, missing)
        STATUS.last_error = "; ".join(errors) or None
        points = registry
        unrecorded = {"point:" + p["id"] for p in points if not p.get("record", True)}
        now = time.time()
        from lib.live import evaluate
        from lib.visibility import update_visibility
        live, _, _ = evaluate(flows, values, now)
        await update_visibility(live, now, s)
        docs = [{"dp": dp, "ts": now, "v": v, "valid_until": now + s.recorder.interval_s * 2.5} for dp, v in values.items() if v is not None and dp not in unrecorded]
        docs.extend(derived_samples(flows, values, now, s.recorder.interval_s))
        if docs:
            await db.samples.insert_many(docs)
            STATUS.samples_written += len(docs)
        try:
            from lib.cycles import tick_cycles
            cycle_docs=await tick_cycles(flows,values,now,s)
            if cycle_docs:
                await db.samples.insert_many(cycle_docs)
                STATUS.samples_written += len(cycle_docs)
        except Exception as exc:
            STATUS.last_error = "Gerätezykluserkennung: " + type(exc).__name__
            logger.warning("Device cycle processing failed: %s",type(exc).__name__)
    STATUS.last_run = datetime.now(timezone.utc).isoformat()
    if missing and not docs:
        _set("waiting", "ioBroker liefert keine Messwerte für die konfigurierten Datenpunkte")
    else:
        _set("recording", f"{len(missing)} Datenpunkt(e) werden aufgezeichnet, einschließlich RUN und Speicher")
    return s.recorder.interval_s


async def recorder_loop() -> None:
    while True:
        _wake.clear()
        interval = 15
        try:
            interval = await _tick()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            STATUS.last_error = str(exc)
            _set("error", "Fehler beim Aufzeichnen")
            logger.warning("recorder: %s", exc)
        try:
            await asyncio.wait_for(_wake.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass
