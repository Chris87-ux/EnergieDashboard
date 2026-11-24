"""Bounded, signed historical chart series; absent observations remain gaps."""
import asyncio
import math
from datetime import datetime, timezone
from models.flow import Flow
from lib.residuals import with_residuals, has_meter
from lib.phases import measured_power


def source_catalog(flows, points):
    sources = [{"kind":"measurement", "reference_id":p["id"], "name":p["name"], "unit":p.get("unit", ""), "enabled":p.get("enabled", True), "record":p.get("record", True)} for p in points]
    for flow in with_residuals(flows):
        sources.append({"kind":"power", "reference_id":flow.id, "name":flow.name,"name_is_generated":flow.kind=="residual" and not flow.residual.name, "unit":"W", "enabled":flow.enabled})
        if flow.kind == "storage":
            for kind, unit in (("soc", "%"), ("charge", "W"), ("discharge", "W")):
                sources.append({"kind":kind,"reference_id":flow.id,"name":flow.name,"unit":unit,"enabled":flow.enabled})
        tracking = getattr(flow, "cycle_tracking", None)
        if flow.kind=="device" and flow.direction=="out" and flow.pv_type not in ("hybrid","mppt"):
            for kind, unit in (("status", "status"), ("cycles", "cycles")):
                sources.append({"kind":kind,"reference_id":flow.id,"name":flow.name,"unit":unit,"enabled":flow.enabled,"record":bool(tracking and tracking.enabled)})
    return sources


def validate_chart(chart, catalog):
    lookup = {(s["kind"], s["reference_id"]): s for s in catalog}
    for series in chart.series:
        source = lookup.get((series.kind, series.reference_id))
        if not source:
            raise ValueError("Die ausgewählte Chart-Quelle existiert nicht.")
        series.unit = source["unit"]


def bucket_values(data, start, end, step, agg="mean"):
    count = max(1, math.ceil((end-start)/step))
    buckets = [[] for _ in range(count)]
    if data is not None:
        timestamps, values = data
        for timestamp, value in zip(timestamps, values):
            if start <= timestamp < end and math.isfinite(float(value)):
                index = min(count-1, int((timestamp-start)//step))
                buckets[index].append(float(value))
    return [(values[-1] if agg=="last" else sum(values)/len(values)) if values else None for values in buckets]


async def chart_report(chart, flows, points, source, start, end, max_points=480):
    interval = getattr(getattr(getattr(source,"s",None),"recorder",None),"interval_s",15)
    step = max(5, interval, math.ceil((end-start)/max_points))
    size = max(1, math.ceil((end-start)/step))
    by_id = {f.id:f for f in flows}
    catalog = {(s["kind"],s["reference_id"]):s for s in source_catalog(flows, points)}
    limit=asyncio.Semaphore(4);columns={};powers={};errors=[]
    def empty(): return [None]*size
    async def read(dp, agg="mean"):
        if not dp: return empty()
        key=(dp,agg)
        if key not in columns:
            async def fetch():
                async with limit:
                    proxy=Flow(name="Chart", datapoints={"chart":dp})
                    data=await source.series(proxy,"chart",start,end,step,agg,bucket_derived=True)
                    return bucket_values(data,start,end,step,agg)
            columns[key]=asyncio.create_task(fetch())
        return await columns[key]
    def combine(parts, operation):
        return [None if any(v is None for v in values) else operation(values) for values in zip(*parts)]
    async def power(id, seen=frozenset()):
        if id in seen: return empty()
        if id in powers: return await powers[id]
        async def calculate():
            if id.endswith(":rest_consumption") and id[:-17] in by_id:
                return await read("energieboard:"+id)
            flow=by_id.get(id)
            if not flow: return empty()
            if flow.kind=="storage":
                a,b=await asyncio.gather(read("energieboard:"+id+":charge"),read("energieboard:"+id+":discharge"))
                return combine([a,b],lambda v:v[0]-v[1])
            if flow.category=="pv" and flow.pv_type=="hybrid":
                a,b=await asyncio.gather(read("energieboard:"+id+":ac_production"),read("energieboard:"+id+":ac_consumption"))
                return combine([a,b],lambda v:v[0]-v[1])
            if flow.run_power_w is not None:
                return await read("energieboard:"+id+":run")
            if flow.kind=="node" and not has_meter(flow):
                children=[f for f in flows if f.parent_id==id and f.electrical_side=="ac"]
                if not children:return [0.0]*size
                parts=await asyncio.gather(*(power(f.id,seen|{id}) for f in children))
                def net(values):
                    return sum(v if child.kind in ("node","storage") else -v if child.pv_type=="hybrid" and child.category=="pv" else abs(v)*(1 if child.direction=="out" else -1) for child,v in zip(children,values))
                return combine(parts,net)
            keys=[key for key in ("power_total","power_l1","power_l2","power_l3") if flow.datapoints.get(key)]
            data=await asyncio.gather(*(read(flow.datapoints.get(key)) for key in keys))
            return [measured_power(flow,{flow.datapoints.get(key):col[i] for key,col in zip(keys,data)})[0] for i in range(size)]
        powers[id]=asyncio.create_task(calculate())
        return await powers[id]
    async def output(series):
        item=catalog.get((series.kind,series.reference_id));flow=by_id.get(series.reference_id)
        if not item:
            errors.append("Chart-Quelle nicht mehr verfügbar: "+series.reference_id);values=empty()
        elif series.kind=="measurement": values=await read("point:"+series.reference_id,"last" if item.get("unit")=="bool" else "mean")
        elif series.kind=="power": values=await power(series.reference_id)
        elif series.kind=="soc":
            values=await read(flow.datapoints.get("soc"));values=[v if v is not None and 0<=v<=100 else None for v in values]
        elif series.kind in ("charge","discharge"): values=await read("energieboard:"+series.reference_id+":"+series.kind)
        else: values=await read("cycles:"+series.reference_id+":"+series.kind,"last")
        return {"kind":series.kind,"reference_id":series.reference_id,"name":series.label or (item or {}).get("name",series.reference_id),"name_is_generated":not series.label and (item or {}).get("name_is_generated",False),"color":series.color,"unit":(item or {}).get("unit",series.unit),"digital":series.kind in ("status","cycles") or (item or {}).get("unit")=="bool","points":[[datetime.fromtimestamp(start+i*step,timezone.utc).isoformat(),v] for i,v in enumerate(values)]}
    output_series=await asyncio.gather(*(output(series) for series in chart.series))
    return {"id":chart.id,"name":chart.name,"start":datetime.fromtimestamp(start,timezone.utc).isoformat(),"end":datetime.fromtimestamp(end,timezone.utc).isoformat(),"step_s":step,"series":output_series,"errors":errors+source.errors}
