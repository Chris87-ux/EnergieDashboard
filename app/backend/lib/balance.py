"""One accounting model for instantaneous W and period kWh.
Grid and storage are transfers; hybrid AC and its DC MPPT are not two producers.
"""
def strict_sum(values):
    values = list(values)
    return None if any(v is None for v in values) else sum(values)


def balance(flows, readings, batteries):
    notes = []
    def val(id): return readings.get(id)
    ac_production = []; loads = []; hybrid_out = []; hybrid_in = []
    production = []; ac_charge = []; ac_discharge = []
    grid_import = []; grid_export = []
    estimated = False
    active_ids={f.id for f in flows}
    for f in flows:
        if f.kind == "grid":
            if f.grid_mode == "signed":
                grid_import.append(val(f.id+":import")); grid_export.append(val(f.id+":export"))
            else:
                (grid_import if f.direction == "in" else grid_export).append(val(f.id))
        elif f.kind == "storage":
            charge, discharge = batteries.get(f.id, (None, None))
            if f.electrical_side == "ac": ac_charge.append(charge); ac_discharge.append(discharge)
        elif f.kind == "node":
            if any(f.datapoints.get(k) for k in ("power_total","power_l1","power_l2","power_l3")):
                ac_production.append(val(f.id+":rest_production")); loads.append(val(f.id+":rest_consumption"))
                production.append(val(f.id+":rest_production"))
        elif f.category == "pv" and f.pv_type == "hybrid":
            out, inp = val(f.id+":ac_production"), val(f.id+":ac_consumption")
            hybrid_out.append(out); hybrid_in.append(inp)
            if f.mppt_ids and any(id not in active_ids for id in f.mppt_ids):production.append(None)
            if not f.mppt_ids:
                # With no independent PV meter this is an explicitly labelled estimate,
                # excluding measured battery discharge. Never silently call AC output PV.
                powers = [batteries.get(id,(None,None)) for id in f.storage_ids]
                charge = strict_sum(c for c,d in powers); discharge = strict_sum(d for c,d in powers)
                pv = None if not powers or any(v is None for v in (out,inp,charge,discharge)) else max(0,out-inp+charge-discharge)
                production.append(pv); estimated = True
                notes.append(f"{f.name}: Produktion aus AC/Batteriebilanz geschätzt; für gemessene DC-Produktion MPPTs zuordnen (Wandlerverluste nicht erfasst).")
        elif f.electrical_side == "dc" or f.pv_type == "mppt":
            if f.direction == "in": production.append(val(f.id))
        elif f.direction == "in":
            ac_production.append(val(f.id)); production.append(val(f.id))
        else: loads.append(val(f.id))
    gi = strict_sum(grid_import) if grid_import or grid_export else None
    ge = strict_sum(grid_export) if grid_import or grid_export else None
    p = strict_sum(production)
    measured = strict_sum(loads)
    supply = strict_sum([strict_sum(ac_production),strict_sum(hybrid_out),strict_sum(ac_discharge)])
    converter_load = strict_sum(hybrid_in); charging = strict_sum(ac_charge)
    c = None if any(v is None for v in (gi,ge,supply,converter_load,charging)) else gi-ge+supply-converter_load-charging
    if c is not None and c < -1e-6:
        notes.append("Negative Anlagenlast: Messgrenzen, Vorzeichen und zeitgleiche Quellen prüfen."); c = None
    elif c is not None: c = max(0,c)
    if c is None and gi is None and ge is None:
        c = measured; notes.append("Verbrauch aus erfassten Geräten; Netzbilanz fehlt.")
    def ratio(numerator, denominator):
        if numerator is None or denominator is None: return None
        return round(max(0,min(100,100*numerator/denominator)),1) if denominator>0 else 0.0
    autarky = ratio(None if c is None or gi is None else c-gi,c)
    selfc = ratio(None if p is None or ge is None else p-ge,p)
    if any(f.kind=="storage" for f in flows):
        notes.append("Autarkie/Eigenverbrauch sind bilanzielle Kennzahlen; Netzladung und Speicherexport erlauben keine eindeutige Herkunftszuordnung.")
    if p is None or c is None or gi is None or ge is None: notes.append("Unvollständige Messwerte: zugeordnete Quellen und deren Messgrenzen prüfen.")
    return dict(production=p,consumption=c,grid_import=gi,grid_export=ge,
        autarky_pct=autarky,self_consumption_pct=selfc,production_estimated=estimated,
        measured_consumption=measured,rest=None if c is None or measured is None else c-measured,
        notes=notes)
