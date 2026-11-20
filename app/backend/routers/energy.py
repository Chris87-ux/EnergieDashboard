from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException

from lib.energy import compute_all, pick_step
from lib.sources import LiveSource, iob_get_bulk, to_power_w
from lib.store import all_datapoints, load_flows, load_settings
from lib.topology import history_flows
from models.energy import EnergyReport, LiveFlow, LiveNode, LiveStorage, LiveReport, LiveSummary, RangePreset
from models.flow import PHASES, Flow

router = APIRouter(tags=["energy"])

FMT = "%Y-%m-%dT%H:%M"


def _presets(tz: str) -> list[RangePreset]:
    zone = ZoneInfo(tz)
    now = datetime.now(zone)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    ranges = [
        ("today", "Heute", today, today + timedelta(days=1)),
        ("yesterday", "Gestern", today - timedelta(days=1), today),
        ("7d", "7 Tage", now - timedelta(days=7), now),
        ("30d", "30 Tage", now - timedelta(days=30), now),
        ("month", "Dieser Monat", today.replace(day=1), now),
    ]
    return [RangePreset(key=k, label=lbl, start=a.strftime(FMT), end=b.strftime(FMT)) for k, lbl, a, b in ranges]


def _parse(value: str, tz: str) -> datetime:
    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Ungültiges Datum: {value}") from exc
    return dt.replace(tzinfo=ZoneInfo(tz)) if dt.tzinfo is None else dt


@router.get("/energy/presets", response_model=list[RangePreset])
async def energy_presets():
    s = await load_settings()
    return _presets(s.timezone)


@router.get("/energy", response_model=EnergyReport)
async def energy(start: str | None = None, end: str | None = None, preset: str | None = None):
    s = await load_settings()
    tz = s.timezone
    if preset:
        match = next((p for p in _presets(tz) if p.key == preset), None)
        if not match:
            raise HTTPException(status_code=400, detail="Unbekannter Zeitraum")
        start, end = match.start, match.end
    if not start or not end:
        raise HTTPException(status_code=400, detail="Start und Ende sind erforderlich")
    a, b = _parse(start, tz), _parse(end, tz)
    if b.timestamp() <= a.timestamp():
        raise HTTPException(status_code=400, detail="Das Ende muss nach dem Start liegen")
    if b.timestamp() - a.timestamp() > 400 * 86400:
        raise HTTPException(status_code=400, detail="Maximal 400 Tage auswählbar")
    now = datetime.now(timezone.utc)
    t0 = a.timestamp()
    t1 = min(b.timestamp(), now.timestamp())
    if t1 <= t0:
        raise HTTPException(status_code=400, detail="Der Zeitraum liegt in der Zukunft")
    flows = await load_flows(enabled_only=True)
    step = pick_step(t0, t1)
    thr = max(s.gap_threshold_min * 60, 2.5 * step)
    src = LiveSource(s)
    results, totals = await compute_all(history_flows(flows), src, t0, t1, step, thr)
    zone = ZoneInfo(tz)
    return EnergyReport(
        start=a.astimezone(timezone.utc),
        end=b.astimezone(timezone.utc),
        effective_end=datetime.fromtimestamp(t1, timezone.utc),
        start_local=a.astimezone(zone).strftime(FMT),
        end_local=b.astimezone(zone).strftime(FMT),
        timezone=tz,
        step_s=step,
        gap_threshold_s=int(thr),
        flows=results,
        totals=totals,
        errors=sorted(set(src.errors))[:20],
    )


def _live_flow(flow: Flow, get) -> LiveFlow:
    if flow.power_phase_mode == "three":
        phases = {p: get(f"power_{p.lower()}") for p in PHASES}
        total = get("power_total")
        if total is None and all(v is not None for v in phases.values()):
            total = sum(v for v in phases.values() if v is not None)
    else:
        total = get("power_total")
        phases = {p: (total if p == flow.power_phase else None) for p in PHASES}
    return LiveFlow(
        flow_id=flow.id,
        name=flow.name,
        category=flow.category,
        direction=flow.direction,
        color=flow.color,
        icon=flow.icon,
        power_phase_mode=flow.power_phase_mode,
        power_phase=flow.power_phase,
        power_w=None if total is None else round(total, 1),
        phases={p: None if v is None else round(v, 1) for p, v in phases.items()},
        frequency_hz=get("frequency", raw=True),
        available=total is not None,
        parent_id=flow.parent_id,
        estimated=flow.run_power_w is not None,
        storage_id=flow.id.rsplit(":", 1)[0] if flow.kind == "storage" else None,
    )


def _summary(flows: list[LiveFlow]) -> LiveSummary:
    def total(pred) -> float | None:
        selected = [f for f in flows if pred(f)]
        if not selected or any(f.power_w is None for f in selected):
            return None
        return round(sum(f.power_w for f in selected), 1)

    in_w = total(lambda f: f.direction == "in")
    out_w = total(lambda f: f.direction == "out")
    pv = total(lambda f: f.category == "pv" and f.direction == "in")
    gi = total(lambda f: f.category == "grid" and f.direction == "in")
    ge = total(lambda f: f.category == "grid" and f.direction == "out")
    bc = total(lambda f: f.category == "battery" and f.direction == "out")
    bd = total(lambda f: f.category == "battery" and f.direction == "in")
    consumption = total(lambda f: f.direction == "out" and f.category not in ("grid", "battery") and not f.flow_id.endswith(":ac_consumption"))
    autarky = None if not consumption or gi is None else round(max(0.0, min(100.0, (1 - gi / consumption) * 100)), 1)
    selfc = None if not pv or ge is None else round(max(0.0, min(100.0, (pv - ge) / pv * 100)), 1)
    return LiveSummary(
        in_w=in_w, out_w=out_w, pv_w=pv, grid_import_w=gi,
        grid_export_w=ge, battery_charge_w=bc, battery_discharge_w=bd,
        consumption_w=consumption, house_rest_w=None if in_w is None or out_w is None else round(in_w - out_w, 1),
        autarky_pct=autarky, self_consumption_pct=selfc,
    )


@router.get("/live", response_model=LiveReport)
async def live():
    from lib.acquisition import read_values
    from lib.live import evaluate, aggregate_storage
    s = await load_settings()
    flows = await load_flows(enabled_only=True)
    values, errors = await read_values(s, all_datapoints(flows))
    now = datetime.now(timezone.utc)
    out, nodes, storages = evaluate(flows, values, now.timestamp())
    grid = any(f.category == "grid" and f.kind == "device" for f in flows)
    if not grid:
        errors.append("Bitte einen Netzanschluss unter Konfiguration anlegen.")
    if not any(f.available for f in out):
        errors.append("Keine aktuellen Leistungswerte verfügbar. Datenerfassung prüfen.")
    summary = _summary(out)
    if any(f.pv_type == "hybrid" for f in flows):
        # AC inverter output includes battery discharge; PV self-consumption cannot be inferred.
        summary.self_consumption_pct = None
        summary.pv_w = None
    dc = [{"id": f.id, "name": f.name, "hybrid_id": next((h.id for h in flows if f.id in h.mppt_ids), None),
           "hybrid_name": next((h.name for h in flows if f.id in h.mppt_ids), None),
           "power_w": None if values.get(f.datapoints.get("power_total")) is None else
           values[f.datapoints.get("power_total")] * (1000 if f.power_unit == "kW" else 1) * (-1 if f.invert else 1)}
          for f in flows if f.kind == "device" and (f.electrical_side == "dc" or f.pv_type == "mppt")]
    return LiveReport(ts=now, ok=grid and any(f.available for f in out), errors=errors,
        site_name=s.site_name, poll_s=s.live_poll_s,
        frequency_hz=next((f.frequency_hz for f in out if f.frequency_hz is not None), None),
        flows=out, nodes=nodes, storages=storages, storage_total=aggregate_storage(storages),
        dc_values=dc, grid_configured=grid, summary=summary)
