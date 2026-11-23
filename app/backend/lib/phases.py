"""AC phase completion. Total means the whole device, never one phase."""
from models.flow import PHASES


def complete_phases(total, phases, three, selected="L1"):
    if not three:
        return total, {p: total if p == selected else None for p in PHASES}, []
    known = [v for v in phases.values() if v is not None]
    missing = [p for p in PHASES if phases[p] is None]
    if total is None and known:
        # Symmetry applies to uninstrumented phases, not to zero-filled samples.
        total = sum(known) * 3 / len(known)
    if total is not None and missing:
        share = (total - sum(known)) / len(missing)
        phases = {p: share if p in missing else phases[p] for p in PHASES}
    return total, phases, missing if total is not None else []


def measured_power(flow, values):
    factor = (1000 if flow.power_unit == "kW" else 1) * (-1 if flow.invert else 1)
    def value(key):
        raw = values.get(flow.datapoints.get(key))
        return None if raw is None else raw * factor
    return complete_phases(value("power_total"), {p:value("power_"+p.lower()) for p in PHASES},
        flow.power_phase_mode == "three", flow.power_phase)
