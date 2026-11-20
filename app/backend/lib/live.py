"""Pure topology evaluation plus time-based storage smoothing; no source IO."""
import math
from models.energy import LiveFlow, LiveNode, LiveStorage
from models.flow import PHASES

_averages = {}


def evaluate(flows, values, now):
    out, nodes, storages, meters = [], [], [], {}
    def measured(flow):
        factor = (1000 if flow.power_unit == "kW" else 1) * (-1 if flow.invert else 1)
        def value(key):
            raw = values.get(flow.datapoints.get(key))
            return None if raw is None else raw * factor
        phases = {p: value("power_" + p.lower()) for p in PHASES}
        total = value("power_total")
        if flow.power_phase_mode == "three":
            if total is None and all(v is not None for v in phases.values()):
                total = sum(phases.values())
        else:
            phases = {p: total if p == flow.power_phase else None for p in PHASES}
        return total, phases
    def row(flow, power, phases=None, id=None, name=None, direction=None, category=None):
        return LiveFlow(flow_id=id or flow.id, name=name or flow.name, category=category or flow.category,
            direction=direction or flow.direction, color=flow.color, icon=flow.icon,
            power_phase_mode=flow.power_phase_mode, power_phase=flow.power_phase,
            power_w=None if power is None else round(power, 2),
            phases=phases or {p: None for p in PHASES}, frequency_hz=values.get(flow.datapoints.get("frequency")),
            available=power is not None, parent_id=flow.parent_id, estimated=flow.run_power_w is not None,
            telemetry={**{k:values.get(flow.datapoints.get(k)) for k in ("engine_temperature","efficiency","fuel_consumption","operating_hours")},"fuel_unit":flow.fuel_unit} if flow.category == "generator" else {})
    for flow in flows:
        total, phases = measured(flow)
        if flow.kind == "storage":
            factor = (1000 if flow.power_unit == "kW" else 1) * (-1 if flow.invert else 1)
            raw = None if total is None else total / factor
            power = None if raw is None else raw * (1000 if flow.power_unit == "kW" else 1) * (1 if flow.charge_sign == "positive" else -1)
            soc = values.get(flow.datapoints.get("soc"))
            soc = soc if soc is not None and 0 <= soc <= 100 else None
            remaining = None if soc is None or flow.capacity_kwh is None else flow.capacity_kwh * soc / 100
            reserve = values.get(flow.datapoints.get("soc_reserve")) if flow.datapoints.get("soc_reserve") else flow.reserve_soc_pct
            reserve = reserve if reserve is not None and 0 <= reserve <= 100 else None
            usable = None if soc is None or flow.capacity_kwh is None or reserve is None else flow.capacity_kwh * max(0, soc - reserve) / 100
            previous = _averages.get(flow.id)
            # Signed 5-minute exponential mean, reset after missing data/gaps.
            average = power
            if power is not None and previous and 0 <= now - previous[0] <= 120:
                alpha = 1 - math.exp(-(now - previous[0]) / 300)
                average = previous[1] + alpha * (power - previous[1])
            if power is None:
                _averages.pop(flow.id, None)
            else:
                _averages[flow.id] = (now, average)
            runtime = None
            if power is not None and power < -50 and average is not None and average < -50 and usable is not None:
                runtime = round(usable * 1000 / -average, 2)
            storages.append(LiveStorage(id=flow.id, name=flow.name, parent_id=flow.parent_id, soc_pct=soc,
                hybrid_name=next((h.name for h in flows if flow.id in h.storage_ids), None),
                charge_w=None if power is None else max(power, 0), discharge_w=None if power is None else max(-power, 0),
                capacity_kwh=flow.capacity_kwh, remaining_kwh=remaining, usable_kwh=usable,
                electrical_side=flow.electrical_side, phases=phases if flow.electrical_side == "ac" else {}, reserve_soc_pct=reserve,
                runtime_h=runtime, max_power_w=flow.max_power_w, smoothed_power_w=average))
        elif flow.kind == "node":
            meters[flow.id] = (total, phases)
        elif flow.electrical_side == "dc" or flow.pv_type == "mppt":
            continue
        elif (flow.kind == "grid" and flow.grid_mode == "signed") or (flow.category == "pv" and flow.pv_type == "hybrid"):
            hybrid = flow.pv_type == "hybrid" and flow.category == "pv"
            for direction, channel in ((("in", "ac_production"), ("out", "ac_consumption")) if hybrid else (("in", "import"), ("out", "export"))):
                polarity = (1 if direction == "in" else -1)
                out.append(row(flow, None if total is None else max(0, total * polarity),
                    {p: None if v is None else max(0, v * polarity) for p, v in phases.items()},
                    id=flow.id + ":" + channel, name=flow.name + ((" · AC-Abgabe" if direction == "in" else " · AC-Aufnahme") if hybrid else (" · Bezug" if direction == "in" else " · Einspeisung")), direction=direction, category="pv" if hybrid else "grid"))
        elif flow.run_power_w is not None:
            run = values.get(flow.datapoints.get("run"))
            power = None if run is None else flow.run_power_w if run else 0
            out.append(row(flow, power, {p: power if p == flow.power_phase else None for p in PHASES}))
        else:
            # Directional devices are nonnegative, inversion selects the source side.
            out.append(row(flow, None if total is None else max(0, total),
                {p: None if v is None else max(0, v) for p, v in phases.items()}, category="grid" if flow.kind == "grid" else flow.category))
    by_parent = {}
    for flow in flows:
        by_parent.setdefault(flow.parent_id, []).append(flow)
    def contribution(flow, seen):
        if flow.id in seen:
            return None
        if flow.kind == "storage" or flow.electrical_side == "dc" or flow.pv_type == "mppt":
            return 0
        if flow.kind == "node":
            if any(flow.datapoints.get(k) for k in ("power_total", "power_l1", "power_l2", "power_l3")):
                return meters[flow.id][0]
            children = [contribution(c, seen | {flow.id}) for c in by_parent.get(flow.id, [])]
            return None if any(v is None for v in children) else sum(children)
        rows = [r for r in out if r.flow_id == flow.id or r.flow_id in (flow.id + ":import", flow.id + ":export", flow.id + ":ac_production", flow.id + ":ac_consumption")]
        return None if any(r.power_w is None for r in rows) else sum(r.power_w * (1 if r.direction == "out" else -1) for r in rows)
    for flow in flows:
        if flow.kind != "node":
            continue
        total, phases = meters[flow.id]
        children = [contribution(c, {flow.id}) for c in by_parent.get(flow.id, [])]
        child_total = None if any(v is None for v in children) else sum(children)
        rest = None if total is None or child_total is None else total - child_total
        nodes.append(LiveNode(id=flow.id, name=flow.name, parent_id=flow.parent_id, icon=flow.icon, color=flow.color, sort_order=flow.sort_order,
            phase_mode=flow.power_phase_mode, phase=flow.power_phase, phases=phases,
            meter_w=total, children_w=child_total, difference_w=rest))
        if any(flow.datapoints.get(k) for k in ("power_total", "power_l1", "power_l2", "power_l3")):
            # Always two stable channels so a sign change never changes historical IDs.
            for direction, suffix, sign in (("out", "rest_consumption", 1), ("in", "rest_production", -1)):
                item = row(flow, None if rest is None else max(0, rest * sign), id=flow.id + ":" + suffix,
                    name=flow.name + (" · Restverbrauch" if sign == 1 else " · Resterzeugung"), direction=direction, category="custom")
                item.parent_id = flow.id
                out.append(item)
    return out, nodes, storages


def aggregate_storage(storages):
    if len(storages) < 2:
        return None
    complete_soc = all(s.capacity_kwh is not None and s.soc_pct is not None for s in storages)
    capacity = sum(s.capacity_kwh or 0 for s in storages) if all(s.capacity_kwh is not None for s in storages) else None
    remaining = sum(s.remaining_kwh for s in storages) if complete_soc else None
    power_ok = all(s.charge_w is not None and s.discharge_w is not None for s in storages)
    power = sum(s.charge_w - s.discharge_w for s in storages) if power_ok else None
    average = sum(s.smoothed_power_w for s in storages) if power_ok else None
    usable = sum(s.usable_kwh for s in storages) if all(s.usable_kwh is not None for s in storages) else None
    runtime = usable * 1000 / -average if power is not None and power < -50 and average < -50 and usable is not None else None
    return LiveStorage(id="aggregate", name="Gesamtspeicher", parent_id=None,
        capacity_kwh=capacity, soc_pct=remaining / capacity * 100 if complete_soc and capacity else None,
        remaining_kwh=remaining, usable_kwh=usable, runtime_h=runtime, smoothed_power_w=average,
        charge_w=max(0, power) if power_ok else None, discharge_w=max(0, -power) if power_ok else None,
        max_power_w=sum(s.max_power_w for s in storages), electrical_side=storages[0].electrical_side if len({s.electrical_side for s in storages})==1 else "mixed")
