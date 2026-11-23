"""Orthogonal display aggregation, never additional flows in the site balance."""
from models.energy import ConsumerGroupSummary


def group_summaries(groups, flows, readings, complete=None, energy=False):
    result=[]
    for group in sorted(groups,key=lambda g:(g.sort_order,g.name,g.id)):
        members=[f for f in flows if f.group_id==group.id and f.kind=="device" and f.direction=="out" and not (f.category=="pv" and f.pv_type=="hybrid")]
        vals=[readings.get(f.id) for f in members]
        value=None if any(v is None for v in vals) else sum(abs(v) for v in vals)
        ok=value is not None and all((complete or {}).get(f.id,True) for f in members)
        result.append(ConsumerGroupSummary(id=group.id,name=group.name,color=group.color,
            member_ids=[f.id for f in members],complete=ok,
            power_w=None if energy else value,energy_kwh=value if energy else None))
    return result
