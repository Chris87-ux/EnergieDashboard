"""Hybrid converter accounting. AC through-feed is not inverter generation."""
from models.flow import PHASES


def hybrid_ac(flow, values):
    from lib.phases import measured_power, complete_phases
    output, phases, _ = measured_power(flow,values)
    factor=(1000 if flow.power_unit=="kW" else 1)*(-1 if flow.invert else 1)
    if flow.hybrid_ac_mode=="terminals":
        raw=values.get(flow.datapoints.get("ac_input"))
        input=None if raw is None else raw*factor
        net=None if output is None or input is None else output-input
        _, phases, _ = complete_phases(net,{p:None for p in PHASES},flow.power_phase_mode=="three",flow.power_phase)
        return net,phases if flow.power_phase_mode=="three" else {p:None for p in PHASES},output,input
    return output,phases,None,None


def dc_device_power(flow, values):
    """Whole-device DC power, including a configured RUN estimate."""
    if flow.run_power_w is not None:
        run = values.get(flow.datapoints.get("run"))
        return None if run is None else flow.run_power_w if run != 0 else 0
    from lib.phases import measured_power
    return measured_power(flow, values)[0]


def hybrid_reports(flows, values, storages):
    from models.energy import LiveHybrid
    by_id={f.id:f for f in flows}
    batteries={s.id:s for s in storages}
    reports=[]
    for flow in flows:
        if flow.kind!="device" or flow.category!="pv" or flow.pv_type!="hybrid":continue
        ac,_,port_out,port_in=hybrid_ac(flow,values)
        missing=[];pv_values=[];charges=[];discharges=[]
        for id in flow.mppt_ids:
            mppt=by_id.get(id)
            value=values.get(mppt.datapoints.get("power_total")) if mppt else None
            if not mppt or mppt.pv_type!="mppt" or value is None:
                missing.append(mppt.name if mppt else id);continue
            pv_values.append(abs(value)*(1000 if mppt.power_unit=="kW" else 1))
        for id in flow.storage_ids:
            config=by_id.get(id);battery=batteries.get(id)
            if not config or config.electrical_side!="dc" or not battery or battery.charge_w is None:
                missing.append(config.name if config else id);continue
            charges.append(battery.charge_w);discharges.append(battery.discharge_w)
        pv=sum(pv_values) if len(pv_values)==len(flow.mppt_ids) else None
        charge=sum(charges) if len(charges)==len(flow.storage_ids) else None
        discharge=sum(discharges) if len(discharges)==len(flow.storage_ids) else None
        factor=1000 if flow.dc_power_unit=="kW" else 1
        loads=values.get(flow.datapoints.get("dc_load_power")) if flow.datapoints.get("dc_load_power") else 0
        loads=None if loads is None else abs(loads)*factor
        if flow.dc_load_ids:
            parts = []
            for id in flow.dc_load_ids:
                config = by_id.get(id)
                power = dc_device_power(config, values) if config and config.kind == "device" and config.electrical_side == "dc" and config.direction == "out" else None
                if power is None: missing.append(config.name if config else id)
                parts.append(power)
            loads = sum(abs(p) for p in parts) if all(p is not None for p in parts) else None
        dc=None;source="unavailable";notes=[]
        if flow.datapoints.get("dc_power"):
            raw=values.get(flow.datapoints.get("dc_power"))
            dc=None if raw is None else raw*factor*(-1 if flow.dc_invert else 1)
            source="measured"
            if dc is None:notes.append("DC-Leistung am WR fehlt.")
        elif flow.dc_balance_complete:
            source="balance"
            if all(v is not None for v in (pv,charge,discharge,loads)):
                dc=pv+discharge-charge-loads
            notes.append("Schätzung aus DC-Busbilanz; Messgrenzen und zeitgleiche Werte erforderlich.")
        else:
            notes.append("Für Wirkungsgrad DC-Leistung am WR zuordnen oder vollständige DC-Busbilanz bestätigen.")
        if missing:notes.append("Fehlende/inaktive DC-Zuordnung: "+", ".join(missing))
        efficiency=None;loss=None;mode="unavailable"
        if ac is None:notes.append("AC-Nettoleistung fehlt.")
        elif dc is not None:
            minimum=flow.hybrid_min_power_w
            if abs(ac)<minimum or abs(dc)<minimum:
                mode="idle";notes.append("Zu geringe AC-/DC-Leistung für einen belastbaren Wirkungsgrad.")
            elif ac*dc<=0:
                mode="inconsistent";notes.append("AC-/DC-Vorzeichen widersprechen sich.")
            else:
                input,output=(dc,ac) if ac>0 else (-ac,-dc)
                ratio=output/input*100
                if not 0<=ratio<=100:
                    mode="inconsistent";notes.append("Wirkungsgrad über 100 %: Messgrenzen, Vorzeichen und Messzeitpunkte prüfen.")
                else:
                    efficiency=round(ratio,2);loss=input-output
                    mode="inverting" if ac>0 else "charging"
        reports.append(LiveHybrid(id=flow.id,name=flow.name,parent_id=flow.parent_id,
            ac_net_w=ac,ac_output_w=port_out,ac_input_w=port_in,dc_pv_w=pv,
            battery_charge_w=charge,battery_discharge_w=discharge,dc_load_w=loads,
            dc_net_w=dc,dc_source=source,efficiency_pct=efficiency,loss_w=loss,mode=mode,note=" ".join(notes),notes=notes))
    return reports
