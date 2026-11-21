"""Live connectors: ioBroker simple-api, InfluxDB 1.x/2.x and the app's own Mongo sample store."""

import csv
import io
import re
from datetime import datetime, timezone
from urllib.parse import quote

import httpx
import numpy as np

from lib.db import db
from models.flow import Flow
from models.settings import AppSettings

LOOKBACK_S = 30 * 86400


def _num(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    if isinstance(v, str) and v.lower() in ("true", "false"):
        return 1.0 if v.lower() == "true" else 0.0
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if np.isfinite(f) else None


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_time(s: str) -> float:
    s = s.strip().replace("Z", "+00:00")
    s = re.sub(r"(\.\d{6})\d+", r"\1", s)
    return datetime.fromisoformat(s).timestamp()


# ---------- ioBroker simple-api ----------

def iob_base(s: AppSettings) -> str:
    host = f"[{s.iobroker.host}]" if ":" in s.iobroker.host else s.iobroker.host
    return f"{s.iobroker.protocol}://{host}:{s.iobroker.port}"


async def iob_get_bulk(s: AppSettings, ids: list[str]) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    if not ids or not s.iobroker.host:
        return out
    async with httpx.AsyncClient(timeout=s.iobroker.timeout_s) as c:
        for i in range(0, len(ids), 40):
            chunk = ids[i : i + 40]
            path = ",".join(quote(x, safe="._-:") for x in chunk)
            r = await c.get(f"{iob_base(s)}/getBulk/{path}")
            r.raise_for_status()
            data = r.json()
            if isinstance(data, dict) and "id" not in data:
                out.update({key: _num(state.get("val")) for key, state in data.items() if isinstance(state, dict)})
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict) and item.get("id"):
                    out[str(item["id"])] = _num(item.get("val"))
    return out


# ---------- InfluxDB ----------

def _esc(name: str) -> str:
    return name.replace("\\", "\\\\").replace('"', '\\"')


async def _v1_query(s: AppSettings, q: str) -> list[list]:
    params = {"db": s.influx.database, "q": q, "epoch": "s"}
    auth = (s.influx.username, s.influx.password) if s.influx.username else None
    async with httpx.AsyncClient(timeout=s.influx.timeout_s, auth=auth) as c:
        r = await c.get(f"{s.influx.url.rstrip('/')}/query", params=params)
        r.raise_for_status()
        data = r.json()
    rows: list[list] = []
    for res in data.get("results", []):
        if "error" in res:
            raise RuntimeError(res["error"])
        for ser in res.get("series", []) or []:
            rows.extend(ser.get("values", []))
    return rows


async def _v2_query(s: AppSettings, flux: str) -> list[dict[str, str]]:
    headers = {
        "Authorization": f"Token {s.influx.token}",
        "Content-Type": "application/vnd.flux",
        "Accept": "application/csv",
    }
    async with httpx.AsyncClient(timeout=s.influx.timeout_s) as c:
        r = await c.post(
            f"{s.influx.url.rstrip('/')}/api/v2/query", params={"org": s.influx.org}, headers=headers, content=flux
        )
        r.raise_for_status()
        text = r.text
    rows: list[dict[str, str]] = []
    header: list[str] | None = None
    for row in csv.reader(io.StringIO(text)):
        if not row or (row[0].startswith("#")):
            header = None if not row else header
            continue
        if header is None or ("_value" in row and "_time" in row) or ("error" in row and "reference" in row):
            header = row
            continue
        record = dict(zip(header, row))
        if record.get("error"):
            raise RuntimeError(record["error"])
        rows.append(record)
    return rows


def _flux_base(s: AppSettings, dp: str, start: float, stop: float) -> str:
    return (
        f'from(bucket: "{_esc(s.influx.bucket)}") |> range(start: {_iso(start)}, stop: {_iso(stop)}) '
        f'|> filter(fn: (r) => r._measurement == "{_esc(dp)}" and r._field == "{_esc(s.influx.field)}")'
    )


async def influx_series(s: AppSettings, dp: str, start: float, end: float, step: int, agg: str) -> list[tuple[float, float]]:
    fn = "mean" if agg == "mean" else "last"
    pts: list[tuple[float, float]] = []
    if s.influx.version == "v1":
        q = (
            f'SELECT {fn}("{_esc(s.influx.field)}") FROM "{_esc(dp)}" WHERE time >= {int(start)}s '
            f"AND time <= {int(end)}s GROUP BY time({step}s, {int(start) % step}s) fill(none)"
        )
        for row in await _v1_query(s, q):
            v = _num(row[1]) if len(row) > 1 else None
            if v is not None:
                pts.append((float(row[0]), v))
    else:
        flux = (
            _flux_base(s, dp, start, end + 1)
            + f' |> aggregateWindow(every: {step}s, offset: {int(start) % step}s, fn: {fn}, timeSrc: "_start", createEmpty: false)'
            + ' |> keep(columns: ["_time", "_value"])'
        )
        for row in await _v2_query(s, flux):
            v = _num(row.get("_value"))
            if v is not None and row.get("_time"):
                pts.append((_parse_time(row["_time"]), v))
    return pts


async def influx_last_before(s: AppSettings, dp: str, start: float) -> tuple[float, float] | None:
    if s.influx.version == "v1":
        q = (
            f'SELECT last("{_esc(s.influx.field)}") FROM "{_esc(dp)}" WHERE time < {int(start)}s '
            f"AND time > {int(start - LOOKBACK_S)}s"
        )
        rows = await _v1_query(s, q)
        if rows and _num(rows[0][1]) is not None:
            return float(rows[0][0]), float(rows[0][1])
        return None
    rows = await _v2_query(s, _flux_base(s, dp, start - LOOKBACK_S, start) + " |> last()")
    for row in rows:
        v = _num(row.get("_value"))
        if v is not None and row.get("_time"):
            return _parse_time(row["_time"]), v
    return None


async def influx_has_recent(s: AppSettings, dp: str, days: int = 3) -> bool:
    now = datetime.now(timezone.utc).timestamp()
    if s.influx.version == "v1":
        rows = await _v1_query(
            s, f'SELECT count("{_esc(s.influx.field)}") FROM "{_esc(dp)}" WHERE time > now() - {days}d'
        )
        return bool(rows) and (_num(rows[0][1]) or 0) > 0
    rows = await _v2_query(s, _flux_base(s, dp, now - days * 86400, now + 1) + " |> count()")
    return any((_num(r.get("_value")) or 0) > 0 for r in rows)


# ---------- Mongo sample store (recorder output) ----------

async def mongo_series(dp: str, start: float, end: float, step: int, agg: str) -> list[tuple[float, float]]:
    if agg == "raw":
        cursor = db.samples.find({"dp": dp, "ts": {"$gte": start, "$lte": end}}).sort("ts", 1)
        return [(float(d["ts"]), float(d["v"])) async for d in cursor]
    acc = {"$avg": "$v"} if agg == "mean" else {"$last": "$v"}
    pipeline = [
        {"$match": {"dp": dp, "ts": {"$gte": start, "$lte": end}}},
        {"$sort": {"ts": 1}},
        {"$group": {"_id": {"$floor": {"$divide": [{"$subtract": ["$ts", start]}, step]}}, "ts": {"$avg" if agg == "mean" else "$last": "$ts"}, "v": acc}},
        {"$sort": {"ts": 1}},
    ]
    cursor = await db.samples.aggregate(pipeline)
    return [(float(d["ts"]), float(d["v"])) async for d in cursor if d.get("v") is not None]


async def mongo_last_before(dp: str, start: float) -> tuple[float, float] | None:
    d = await db.samples.find_one({"dp": dp, "ts": {"$lt": start, "$gt": start - LOOKBACK_S}}, sort=[("ts", -1)])
    return (float(d["ts"]), float(d["v"])) if d else None


# ---------- unit handling ----------

def to_power_w(flow: Flow, v: float | None) -> float | None:
    if v is None:
        return None
    v = v * (1000.0 if flow.power_unit == "kW" else 1.0)
    if flow.invert:
        v = -v
    return v


def to_energy_kwh(flow: Flow, v: float) -> float:
    return v * (0.001 if flow.energy_unit == "Wh" else 1.0)


class LiveSource:
    """History for live mode: InfluxDB first, the app's own recorded samples fill the rest."""

    def __init__(self, settings: AppSettings):
        self.s = settings
        self.errors: list[str] = []

    async def recorded_integral(self, flow: Flow, start: float, end: float, threshold: float):
        from lib.energy import Calc, unavailable

        dp = flow.datapoints.get("power_total")
        hold = min(threshold, self.s.recorder.interval_s * 2.5)
        pipeline = [
            # Stored intervals remain valid after the polling interval is changed.
            {"$match": {"dp": dp, "ts": {"$gte": start - 9000, "$lte": end}}},
            {"$setWindowFields": {"sortBy": {"ts": 1}, "output": {
                "next": {"$shift": {"output": "$ts", "by": 1, "default": end}},
            }}},
            {"$set": {
                "left": {"$max": [start, "$ts"]},
                "right": {"$min": [end, "$next"]},
                "valid_end": {"$min": [end, "$next", {"$add": ["$ts", threshold]}, {"$ifNull": ["$valid_until", {"$add": ["$ts", hold]}]}]},
            }},
            {"$set": {"duration": {"$max": [0, {"$subtract": ["$valid_end", "$left"]}]}}},
            {"$facet": {
                "totals": [{"$group": {
                    "_id": None, "first": {"$min": "$ts"},
                    "seconds": {"$sum": "$duration"},
                    "watt_seconds": {"$sum": {"$multiply": ["$v", "$duration"]}},
                }}],
                "gaps": [
                    {"$match": {"$expr": {"$gt": ["$right", {"$max": ["$left", "$valid_end"]}]}}},
                    {"$project": {"_id": 0, "start": {"$max": ["$left", "$valid_end"]}, "end": "$right"}},
                    {"$limit": 50},
                ],
            }},
        ]
        try:
            cursor = await db.samples.aggregate(pipeline)
            documents = await cursor.to_list(1)
        except Exception as exc:
            self.errors.append(f"Recorder {flow.name}: {exc}")
            return unavailable(start, end)
        if not documents or not documents[0]["totals"]:
            return unavailable(start, end)
        result = documents[0]
        totals = result["totals"][0]
        if totals["seconds"] <= 0:
            return unavailable(start, end)
        gaps = [(gap["start"], gap["end"]) for gap in result["gaps"]]
        if totals["first"] > start:
            gaps.insert(0, (start, totals["first"]))
        estimated = flow.run_power_w is not None
        return Calc(
            totals["watt_seconds"] / 3.6e6, "run_estimate" if estimated else "power_integral",
            min(totals["seconds"] / (end - start), 1), not gaps, gaps,
            note="Geschätzt aus aufgezeichnetem RUN-Signal und fester Leistung" if estimated else "Aus aufgezeichneter abgeleiteter Leistung",
        )

    async def series(self, flow: Flow, key: str, start: float, end: float, step: int, agg: str):
        dp = flow.datapoints.get(key)
        if not dp:
            return None
        pts: list[tuple[float, float]] = []
        history_key = ""
        history_end = end
        if dp.startswith("point:"):
            point = await db.measurements.find_one({"id": dp[6:]})
            history_key = (point or {}).get("history_key", "")
            history_end = min(end, (point or {}).get("legacy_until") or end)
        influx_dp = history_key or dp
        derived = dp.startswith("energieboard:")
        if self.s.influx.enabled and not derived and (not dp.startswith("point:") or history_key) and history_end >= start:
            try:
                pts += await influx_series(self.s, influx_dp, start, history_end, step, agg)
                if agg == "last":
                    prev = await influx_last_before(self.s, influx_dp, start)
                    if prev:
                        pts.append(prev)
            except Exception as exc:
                self.errors.append(f"InfluxDB {dp}: {exc}")
        try:
            local = await mongo_series(dp, start, end, step, "raw" if derived else agg)
            if history_key and history_end >= start:
                local += await mongo_series(history_key, start, history_end, step, agg)
            # Keep recorder samples in windows without an InfluxDB point.
            if pts:
                windows = {int((t - start) // step) for t, _ in pts if t >= start}
                local = [(t, v) for t, v in local if int((t - start) // step) not in windows]
            pts += local
            if agg == "last" or derived:
                prev = await mongo_last_before(dp, start)
                if history_key:
                    old_prev = await mongo_last_before(history_key, start)
                    if old_prev and (not prev or old_prev[0] > prev[0]):
                        prev = old_prev
                if prev:
                    pts.append(prev)
        except Exception as exc:
            self.errors.append(f"Recorder {dp}: {exc}")
        if not pts:
            return None
        before = [(t, v) for t, v in pts if t < start]
        pts = [(t, v) for t, v in pts if start <= t <= end]
        if before:
            pts.append(max(before, key=lambda point: point[0]))
        pts.sort()
        ts: list[float] = []
        vs: list[float] = []
        for t, v in pts:
            if ts and t == ts[-1]:
                continue
            ts.append(t)
            vs.append(v)
        arr = np.array(vs, dtype=float)
        if key.startswith("power"):
            arr = arr * (1000.0 if flow.power_unit == "kW" else 1.0) * (-1.0 if flow.invert else 1.0)
            arr = np.abs(arr)
        elif key.startswith("energy"):
            arr = arr * (0.001 if flow.energy_unit == "Wh" else 1.0)
        return np.array(ts, dtype=float), arr
