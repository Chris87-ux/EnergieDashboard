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

logger = logging.getLogger(__name__)

STATUS = RecorderStatus()
_wake = asyncio.Event()


def request_recheck() -> None:
    _wake.set()


def _set(state: str, message: str) -> None:
    STATUS.state = state  # type: ignore[assignment]
    STATUS.message = message


async def _tick() -> int:
    s = await load_settings()
    if not s.recorder.enabled:
        _set("disabled", "Aufzeichnung ist deaktiviert")
        return s.recorder.interval_s
    flows = await load_flows(enabled_only=True)
    dps = tuple(all_datapoints(flows))
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
        points = await db.measurements.find({}, {"_id": 0}).to_list()
        unrecorded = {"point:" + p["id"] for p in points if not p.get("record", True)}
        now = time.time()
        docs = [{"dp": dp, "ts": now, "v": v, "valid_until": now + s.recorder.interval_s * 2.5} for dp, v in values.items() if v is not None and dp not in unrecorded]
        docs.extend(derived_samples(flows, values, now, s.recorder.interval_s))
        if docs:
            await db.samples.insert_many(docs)
            STATUS.samples_written += len(docs)
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
