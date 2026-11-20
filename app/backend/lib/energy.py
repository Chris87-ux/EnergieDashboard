"""Energy engine: counter deltas (with reset handling) > phase sums > active-power integration."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

from models.energy import EnergyTotals, EnergyValue, FlowEnergy, Gap
from models.flow import PHASES, Flow


@dataclass
class Calc:
    kwh: float | None
    method: str
    coverage: float = 0.0
    complete: bool = False
    gaps: list[tuple[float, float]] = field(default_factory=list)
    resets: int = 0
    note: str = ""

    @property
    def ok(self) -> bool:
        return self.kwh is not None and self.method not in ("unavailable", "not_applicable")


def _merge(gaps: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for a, b in sorted(gaps):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def _edge_gaps(ts: np.ndarray, start: float, end: float, thr: float) -> list[tuple[float, float]]:
    g = []
    if ts[0] - start > thr:
        g.append((start, float(ts[0])))
    if end - ts[-1] > thr:
        g.append((float(ts[-1]), end))
    return g


def counter_delta(ts: np.ndarray, v: np.ndarray, start: float, end: float, thr: float) -> Calc | None:
    if len(ts) < 2:
        return None
    d = np.diff(v)
    prev = v[:-1]
    jitter = (d < 0) & (np.abs(d) <= np.maximum(np.abs(prev) * 1e-3, 1e-3))
    reset = (d < 0) & ~jitter
    segments = np.split(v, np.flatnonzero(reset) + 1)
    stable = np.concatenate([np.maximum.accumulate(segment) for segment in segments])
    inc = np.where(reset, np.clip(stable[1:], 0, None), np.maximum(np.diff(stable), 0))
    dt = np.diff(ts)
    left = np.maximum(ts[:-1], start)
    right = np.minimum(ts[1:], end)
    overlap = np.maximum(right - left, 0)
    intersects = (dt > 0) & (overlap > 0)
    boundary_gap = ((ts[:-1] < start) | (ts[1:] > end)) & (dt > thr)
    valid = intersects & ~boundary_gap
    if not np.any(valid):
        return None
    fraction = np.divide(overlap, dt, out=np.zeros(overlap.shape, dtype=float), where=dt > 0)
    inner = [(float(left[i]), float(right[i])) for i in np.nonzero(valid & (dt > thr))[0]]
    first, last = float(left[valid][0]), float(right[valid][-1])
    edges = _edge_gaps(np.array([first, last]), start, end, thr)
    # A stale counter outside the requested range cannot establish its boundary value.
    edges += [(float(left[i]), float(right[i])) for i in np.nonzero(intersects & boundary_gap)[0]]
    span = last - first
    resets = int(reset[valid].sum())
    notes = []
    if np.any(fraction[valid] < 1):
        notes.append("Randwerte zeitanteilig interpoliert")
    if resets:
        notes.append(f"{resets} Zähler-Reset(s) berücksichtigt")
    if inner:
        notes.append("Lücken durch Zählerstand überbrückt")
    return Calc(
        kwh=float(np.sum(inc[valid] * fraction[valid])),
        method="counter_delta",
        coverage=float(np.clip(span / (end - start), 0, 1)),
        complete=not edges,
        gaps=_merge(edges + inner),
        resets=resets,
        note="; ".join(notes),
    )


def power_integral(ts: np.ndarray, v: np.ndarray, start: float, end: float, thr: float) -> Calc | None:
    if len(ts) < 2:
        return None
    dt = np.diff(ts)
    left = np.maximum(ts[:-1], start)
    right = np.minimum(ts[1:], end)
    overlap = np.maximum(right - left, 0)
    intersects = (dt > 0) & (overlap > 0)
    ok = intersects & (dt <= thr)
    if not np.any(ok):
        return None
    slope = np.divide(np.diff(v), dt, out=np.zeros(dt.shape, dtype=float), where=dt > 0)
    left_value = v[:-1] + slope * (left - ts[:-1])
    right_value = v[:-1] + slope * (right - ts[:-1])
    kwh = float(np.sum((left_value[ok] + right_value[ok]) / 2 * overlap[ok]) / 3.6e6)
    covered = float(np.sum(overlap[ok]))
    first, last = float(left[intersects][0]), float(right[intersects][-1])
    gaps = _edge_gaps(np.array([first, last]), start, end, thr)
    gaps += [(float(left[i]), float(right[i])) for i in np.nonzero(intersects & ~ok)[0]]
    return Calc(
        kwh=kwh,
        method="power_integral",
        coverage=float(np.clip(covered / (end - start), 0, 1)),
        complete=not gaps,
        gaps=_merge(gaps),
        note="Aus historischer Wirkleistung integriert",
    )


def unavailable(start: float, end: float, note: str = "Keine Zähler- oder Leistungsdaten") -> Calc:
    return Calc(None, "unavailable", 0.0, False, [(start, end)], 0, note)


def not_applicable() -> Calc:
    return Calc(None, "not_applicable", 1.0, True, [], 0, "Phase nicht belegt")


def phase_sum(parts: list[Calc]) -> Calc:
    ok = [p for p in parts if p.ok]
    methods = sorted({p.method for p in ok})
    labels = {"counter_delta": "Zählerdelta", "power_integral": "Leistungsintegration"}
    return Calc(
        kwh=float(sum(p.kwh or 0 for p in ok)),
        method="phase_sum",
        coverage=min(p.coverage for p in ok),
        complete=all(p.complete for p in ok),
        gaps=_merge([g for p in ok for g in p.gaps]),
        resets=sum(p.resets for p in ok),
        note="Summe der Phasen (" + ", ".join(labels.get(m, m) for m in methods) + ")",
    )


def _to_model(c: Calc) -> EnergyValue:
    def dt(x: float) -> datetime:
        return datetime.fromtimestamp(x, timezone.utc)

    return EnergyValue(
        kwh=None if c.kwh is None else round(c.kwh, 6),
        method=c.method,  # type: ignore[arg-type]
        coverage=round(c.coverage, 4),
        complete=c.complete,
        gaps=[Gap(start=dt(a), end=dt(b)) for a, b in c.gaps[:50]],
        resets=c.resets,
        note=c.note,
    )


async def compute_flow(flow: Flow, src, start: float, end: float, step: int, thr: float) -> FlowEnergy:
    cache: dict[tuple[str, str], object] = {}

    async def series(key: str, agg: str):
        k = (key, agg)
        if k not in cache:
            cache[k] = await src.series(flow, key, start, end, step, agg)
        return cache[k]

    async def counter(key: str) -> Calc | None:
        s = await series(key, "last")
        return counter_delta(s[0], s[1], start, end, thr) if s else None

    async def integ(key: str | None) -> Calc | None:
        if not key:
            return None
        if flow.datapoints.get(key).startswith("energieboard:") and hasattr(src, "recorded_integral"):
            return await src.recorded_integral(flow, start, end, thr)
        s = await series(key, "mean")
        if s and flow.datapoints.get(key).startswith("energieboard:"):
            ts, values = s
            duration = 0.0
            watts_seconds = 0.0
            gaps = []
            for i, timestamp in enumerate(ts):
                left = max(start, float(timestamp))
                right = min(end, float(ts[i + 1]) if i + 1 < len(ts) else end)
                valid_end = min(right, float(timestamp) + min(thr, src.s.recorder.interval_s * 2.5))
                if valid_end > left:
                    duration += valid_end - left
                    watts_seconds += float(values[i]) * (valid_end - left)
                if right > max(left, valid_end):
                    gaps.append((max(left, valid_end), right))
            if len(ts) and ts[0] > start:
                gaps.insert(0, (start, float(ts[0])))
            if duration <= 0:
                return None
            estimated = flow.run_power_w is not None
            return Calc(
                watts_seconds / 3.6e6, "run_estimate" if estimated else "power_integral",
                min(duration / (end - start), 1), not gaps, gaps,
                note="Geschätzt aus aufgezeichnetem RUN-Signal und fester Leistung" if estimated else "Getrennt aus vorzeichenbehafteter Speicherleistung aufgezeichnet",
            )
        return power_integral(s[0], s[1], start, end, thr) if s else None

    def power_key(p: str) -> str | None:
        if flow.power_phase_mode == "three":
            return f"power_{p.lower()}"
        return "power_total" if p == flow.power_phase else None

    phases: dict[str, Calc] = {}
    if flow.energy_phase_mode == "three":
        for p in PHASES:
            c = await counter(f"energy_{p.lower()}")
            if c is None:
                pk = power_key(p)
                c = not_applicable() if pk is None else (await integ(pk) or unavailable(start, end))
            phases[p] = c
        total = await counter("energy_total")
        vals = list(phases.values())
        if total is None and all(v.method == "counter_delta" for v in vals):
            total = phase_sum(vals)
        if total is None:
            total = await integ("power_total")
        if total is None and all(v.ok or v.method == "not_applicable" for v in vals) and any(v.ok for v in vals):
            total = phase_sum(vals)
        if total is None:
            total = unavailable(start, end, "Unvollständige Phasendaten – keine Summe möglich")
    else:
        sel = flow.energy_phase
        total = await counter("energy_total")
        if total is None:
            total = await integ("power_total")
        if total is None and flow.power_phase_mode == "three":
            total = await integ(f"power_{sel.lower()}")
        if total is None:
            total = unavailable(start, end)
        phases = {p: (total if p == sel else not_applicable()) for p in PHASES}

    return FlowEnergy(
        flow_id=flow.id,
        name=flow.name,
        category=flow.category,
        direction=flow.direction,
        color=flow.color,
        icon=flow.icon,
        energy_phase_mode=flow.energy_phase_mode,
        energy_phase=flow.energy_phase,
        total=_to_model(total),
        phases={p: _to_model(c) for p, c in phases.items()},
        parent_id=flow.parent_id,
        storage_id=flow.id.rsplit(":", 1)[0] if flow.kind == "storage" else None,
    )


def pick_step(start: float, end: float) -> int:
    return int(min(1800, max(60, (end - start) / 1440)))


async def compute_all(flows: list[Flow], src, start: float, end: float, step: int, thr: float):
    results = await asyncio.gather(*(compute_flow(f, src, start, end, step, thr) for f in flows))
    def total(direction: str) -> float | None:
        values = [r.total.kwh for r in results if r.direction == direction and r.total.kwh is not None and not r.storage_id]
        return round(sum(values), 3) if values else None

    incomplete = any(not r.total.complete for r in results if not r.storage_id)
    return list(results), EnergyTotals(in_kwh=total("in"), out_kwh=total("out"), incomplete=incomplete)
