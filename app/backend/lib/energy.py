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
    from dataclasses import replace
    cache = {}
    async def series(key, agg):
        if (key,agg) in cache: return cache[(key,agg)]
        result = None
        if flow.datapoints.get(key):
            result = await src.series(flow,key,start,end,step,agg)
        elif key.startswith("power") and flow.power_phase_mode == "three" and flow.electrical_side == "ac":
            if key != "power_total":
                base = await series("power_total",agg)
                result = (base[0],base[1]/3) if base else None
            else:
                keys = ["power_"+p.lower() for p in PHASES if flow.datapoints.get("power_"+p.lower())]
                parts = [await series(k,agg) for k in keys]
                if parts and all(part is not None for part in parts):
                    timestamps = parts[0][0]
                    for part in parts[1:]: timestamps=np.intersect1d(timestamps,part[0])
                    if len(timestamps):
                        vals=sum(part[1][np.searchsorted(part[0],timestamps)] for part in parts)*3/len(parts)
                        result=(timestamps,vals)
        cache[(key,agg)] = result
        return result
    async def counter(key):
        data=await series(key,"last")
        return counter_delta(data[0],data[1],start,end,thr) if data else None
    async def integ(key):
        dp=flow.datapoints.get(key)
        if dp.startswith("energieboard:") and hasattr(src,"recorded_integral"):
            mapped=flow.model_copy(update={"datapoints":flow.datapoints.model_copy(update={"power_total":dp})})
            return await src.recorded_integral(mapped,start,end,thr)
        data=await series(key,"mean")
        if data and dp.startswith("energieboard:"):
            ts,values=data; duration=0.; watts_seconds=0.; gaps=[]
            for i,t in enumerate(ts):
                left=max(start,float(t));right=min(end,float(ts[i+1]) if i+1<len(ts) else end)
                valid_end=min(right,float(t)+min(thr,src.s.recorder.interval_s*2.5))
                if valid_end>left:duration+=valid_end-left;watts_seconds+=float(values[i])*(valid_end-left)
                if right>max(left,valid_end):gaps.append((max(left,valid_end),right))
            if len(ts) and ts[0]>start:gaps.insert(0,(start,float(ts[0])))
            if duration<=0:return None
            return Calc(watts_seconds/3.6e6,"run_estimate" if flow.run_power_w is not None else "power_integral",
                min(duration/(end-start),1),not gaps,gaps,note="Aus aufgezeichneten Zustandsintervallen")
        return power_integral(data[0],data[1],start,end,thr) if data else None
    total=await counter("energy_total")
    phase_counters={p:await counter("energy_"+p.lower()) for p in PHASES} if flow.energy_phase_mode=="three" else {}
    if total is None and len(phase_counters)==3 and all(c is not None for c in phase_counters.values()):total=phase_sum(list(phase_counters.values()))
    if total is None and phase_counters:
        configured=[p for p in PHASES if flow.datapoints.get("energy_"+p.lower())]
        if configured and all(phase_counters[p] is not None for p in configured):
            part=phase_sum([phase_counters[p] for p in configured])
            total=replace(part,kwh=part.kwh*3/len(configured),note="Symmetrisch aus vorhandenen Phasenzählern hochgerechnet")
    if total is None:total=await integ("power_total")
    if total is None:total=unavailable(start,end)
    estimated_phases=[]
    three=flow.electrical_side=="ac" and (flow.power_phase_mode=="three" or flow.energy_phase_mode=="three")
    if three and not flow.extra.get("total_only"):
        phases={}
        missing=[]
        for p in PHASES:
            key="power_"+p.lower();c=phase_counters.get(p)
            if c is None and flow.datapoints.get(key):c=await integ(key)
            if c is None and not flow.datapoints.get(key) and not flow.datapoints.get("energy_"+p.lower()):missing.append(p)
            phases[p]=c
        known=[c for c in phases.values() if c is not None]
        if missing and total.kwh is not None and all(c is not None and c.kwh is not None for p,c in phases.items() if p not in missing):
            share=(total.kwh-sum(c.kwh for c in known if c.kwh is not None))/len(missing)
            for p in missing:
                phases[p]=replace(total,kwh=share,complete=total.complete and all(c.complete for c in known),
                    coverage=min([total.coverage]+[c.coverage for c in known]),
                    gaps=_merge(total.gaps+[g for c in known for g in c.gaps]),
                    note="Berechnet: symmetrische Aufteilung der verbleibenden Gesamtenergie.")
                estimated_phases.append(p)
        phases={p:c or unavailable(start,end) for p,c in phases.items()}
        if total.kwh is None and all(v.ok for v in phases.values()):total=phase_sum(list(phases.values()))
    else:
        phases={p:total if p==flow.energy_phase else not_applicable() for p in PHASES}
    if flow.electrical_side=="dc" or flow.extra.get("total_only"):
        phases={p:not_applicable() for p in PHASES}
    return FlowEnergy(
        estimated_phases=estimated_phases,
        electrical_side=flow.electrical_side,
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


async def compute_all(flows: list[Flow], src, start: float, end: float, step: int, thr: float, configuration=None):
    results = await asyncio.gather(*(compute_flow(f, src, start, end, step, thr) for f in flows))
    def total(direction: str) -> float | None:
        values = [r.total.kwh for r in results if r.direction == direction and r.total.kwh is not None and not r.storage_id and r.electrical_side == "ac"]
        return round(sum(values), 3) if values else None

    incomplete = any(not r.total.complete for r in results if not r.storage_id and r.electrical_side == "ac")
    totals=EnergyTotals(in_kwh=total("in"),out_kwh=total("out"),incomplete=incomplete)
    if configuration is not None:
        from lib.balance import balance
        inferred_storage={id for f in configuration if f.category=="pv" and f.pv_type=="hybrid" and not f.mppt_ids for id in f.storage_ids}
        incomplete=any(not r.total.complete for r in results if not r.storage_id or r.electrical_side=="ac" or r.storage_id in inferred_storage)
        readings={r.flow_id:r.total.kwh for r in results}
        batteries={f.id:(readings.get(f.id+":charge"),readings.get(f.id+":discharge")) for f in configuration if f.kind=="storage"}
        b=balance(configuration,readings,batteries)
        totals=EnergyTotals(in_kwh=b["production"],out_kwh=b["consumption"],incomplete=incomplete,
            production_kwh=b["production"],consumption_kwh=b["consumption"],grid_import_kwh=b["grid_import"],
            grid_export_kwh=b["grid_export"],autarky_pct=b["autarky_pct"],self_consumption_pct=b["self_consumption_pct"],
            production_estimated=b["production_estimated"],notes=b["notes"])
    return list(results),totals
