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
    consumption = total(lambda f: f.direction == "out" and f.category not in ("grid", "battery"))
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
    s = await load_settings()
    flows = await load_flows(enabled_only=True)
    now = datetime.now(timezone.utc)
    errors: list[str] = []
    out: list[LiveFlow] = []
    nodes: list[LiveNode] = []
    storages: list[LiveStorage] = []
    ids = all_datapoints(flows)
    values: dict[str, float | None] = {}
    if not s.iobroker.host:
        errors.append("ioBroker ist nicht konfiguriert.")
    elif not ids:
        errors.append("Unter „Konfiguration“ müssen aktive Flüsse mit ioBroker-Datenpunkten angelegt werden.")
    else:
        try:
            values = await iob_get_bulk(s, ids)
        except Exception as exc:
            errors.append(f"ioBroker nicht erreichbar: {exc}")
    for f in flows:
        def get(key: str, raw: bool = False, f: Flow = f):
            v = values.get(f.datapoints.get(key))
            if v is None:
                return None
            if raw:
                return round(v, 3)
            if f.kind == "node":
                return v * (1000 if f.power_unit == "kW" else 1) * (-1 if f.invert else 1)
            return to_power_w(f, v)
        if f.kind == "storage":
            raw_power = values.get(f.datapoints.get("power_total"))
            signed = None if raw_power is None else raw_power * (1000 if f.power_unit == "kW" else 1)
            if signed is not None and f.charge_sign == "negative":
                signed = -signed
            soc = values.get(f.datapoints.get("soc"))
            storages.append(LiveStorage(
                id=f.id, name=f.name, parent_id=f.parent_id,
                soc_pct=soc if soc is not None and 0 <= soc <= 100 else None,
                charge_w=None if signed is None else max(signed, 0),
                discharge_w=None if signed is None else max(-signed, 0),
            ))
            for channel, direction, suffix in (("charge", "out", "Laden"), ("discharge", "in", "Entladen")):
                power = None if signed is None else max(signed if channel == "charge" else -signed, 0)
                virtual = f.model_copy(update={
                    "id": f"{f.id}:{channel}", "name": f"{f.name} · {suffix}", "category": "battery",
                    "direction": direction, "power_phase_mode": "single",
                })
                out.append(_live_flow(virtual, lambda key, raw=False, power=power: power if key == "power_total" else None))
        elif f.kind == "node":
            measured = _live_flow(f, get)
            nodes.append(LiveNode(
                id=f.id, name=f.name, phase_mode=f.power_phase_mode, phase=f.power_phase,
                phases=measured.phases, meter_w=measured.power_w, children_w=None, difference_w=None,
            ))
        elif f.run_power_w is not None:
            run = values.get(f.datapoints.get("run"))
            watts = None if run is None else f.run_power_w if run != 0 else 0
            virtual = f.model_copy(update={"power_phase_mode": "single"})
            out.append(_live_flow(virtual, lambda key, raw=False, watts=watts: watts if key == "power_total" else None))
        else:
            out.append(_live_flow(f, get))
    for node in nodes:
        children = [f for f in out if f.parent_id == node.id]
        if children and all(f.available for f in children):
            # Positive = consumption, negative = production, including charge/discharge.
            node.children_w = sum((f.power_w or 0) * (1 if f.direction == "out" else -1) for f in children)
            if node.meter_w is not None:
                node.difference_w = round(node.meter_w - node.children_w, 1)
    if not errors and not any(f.available for f in out):
        errors.append("ioBroker liefert keine Leistung für die konfigurierten Flüsse.")
    freq = next((f.frequency_hz for f in out if f.frequency_hz is not None), None)
    return LiveReport(
        ts=now,
        ok=not errors,
        errors=errors,
        site_name=s.site_name,
        poll_s=s.live_poll_s,
        frequency_hz=freq,
        flows=out,
        nodes=nodes,
        storages=storages,
        summary=_summary(out),
    )
