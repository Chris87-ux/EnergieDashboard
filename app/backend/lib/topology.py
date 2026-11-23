from models.flow import Flow


def sample_id(flow: Flow, channel: str) -> str:
    return f"energieboard:{flow.id}:{channel}"


def derived_samples(flows: list[Flow], values: dict[str, float | None], now: float, interval_s: int = 15) -> list[dict]:
    samples = []
    from lib.live import evaluate
    live, _, storages = evaluate(flows, values, now)
    storage_by_id = {s.id:s for s in storages}
    for flow in flows:
        if flow.kind == "storage":
            storage = storage_by_id[flow.id]
            if storage.charge_w is None:
                continue
            channels = {"charge": storage.charge_w, "discharge": storage.discharge_w}
            if flow.electrical_side=="ac" and flow.power_phase_mode=="three":
                for p,value in storage.phases.items():
                    if value is not None:
                        signed=value*(1 if flow.charge_sign=="positive" else -1)
                        channels["charge:"+p.lower()]=signed if storage.charge_w>0 else 0
                        channels["discharge:"+p.lower()]=-signed if storage.discharge_w>0 else 0
        elif flow.kind == "device" and flow.run_power_w is not None:
            value = values.get(flow.datapoints.get("run"))
            if value is None:
                continue
            channels = {"run": flow.run_power_w if value != 0 else 0}
        else:
            continue
        samples.extend({"dp": sample_id(flow, key), "ts": now, "v": value, "valid_until": now + interval_s * 2.5} for key, value in channels.items())
    for item in live:
        if ":rest_" in item.flow_id or item.flow_id.endswith((":import", ":export", ":ac_production", ":ac_consumption")):
            if item.power_w is not None:
                owner, channel = item.flow_id.rsplit(":", 1)
                samples.append({"dp": f"energieboard:{owner}:{channel}", "ts": now,
                    "v": item.power_w, "valid_until": now + interval_s * 2.5})
                if ":rest_" in item.flow_id and item.power_phase_mode == "three":
                    samples.extend({"dp":f"energieboard:{owner}:{channel}:"+p.lower(),"ts":now,"v":v,"valid_until":now+interval_s*2.5}
                        for p,v in item.phases.items() if v is not None)
    return samples


def history_flows(flows: list[Flow]) -> list[Flow]:
    out = []
    for flow in flows:
        if flow.kind == "node" or (flow.kind == "grid" and flow.grid_mode == "signed") or (flow.category == "pv" and flow.pv_type == "hybrid"):
            if not any(flow.datapoints.get(key) for key in ("power_total", "power_l1", "power_l2", "power_l3")):
                continue
            channels = (("rest_consumption", "out", "Restverbrauch"), ("rest_production", "in", "Resterzeugung")) if flow.kind == "node" else (("import", "in", "Bezug"), ("export", "out", "Einspeisung"))
            if flow.category == "pv" and flow.pv_type == "hybrid":
                channels = (("ac_production", "in", "AC-Abgabe"), ("ac_consumption", "out", "AC-Aufnahme"))
            for channel, direction, suffix in channels:
                out.append(flow.model_copy(update={
                    "id": flow.id + ":" + channel, "name": flow.name + " · " + suffix,
                    "kind": "device", "category": "custom" if flow.kind == "node" else "grid" if flow.kind == "grid" else flow.category,
                    "direction": direction, "parent_id": flow.id if flow.kind == "node" else flow.parent_id,
                    "power_unit": "W", "invert": False,
                    "power_phase_mode": flow.power_phase_mode if flow.kind=="node" else "single",
                    "energy_phase_mode": flow.power_phase_mode if flow.kind=="node" else "single",
                    "extra": {**flow.extra, "total_only": flow.kind != "node" or flow.power_phase_mode != "three"},
                    "datapoints": flow.datapoints.model_copy(update={
                        **{key: "" for key in flow.datapoints.model_dump()}, "power_total": sample_id(flow, channel),
                        "energy_total": flow.datapoints.get("energy_" + channel) if flow.kind == "grid" else "",
                        **({"power_"+p.lower():sample_id(flow,channel)+":"+p.lower() for p in ("L1","L2","L3")} if flow.kind=="node" and flow.power_phase_mode=="three" else {})}),
                }))
            continue
        if flow.kind != "storage" and flow.pv_type != "mppt" and flow.electrical_side == "dc" and flow.direction != "in" and not flow.group_id:
            continue
        if flow.kind == "storage":
            for channel, direction, suffix in (("charge", "out", "Laden"), ("discharge", "in", "Entladen")):
                out.append(flow.model_copy(update={
                    "id": f"{flow.id}:{channel}", "name": f"{flow.name} · {suffix}",
                    "category": "battery", "direction": direction, "power_unit": "W",
                    "power_phase_mode": flow.power_phase_mode, "energy_phase_mode": flow.power_phase_mode,
                    "energy_phase": flow.power_phase, "invert": False,
                    "extra": {**flow.extra, "total_only": False},
                    "datapoints": flow.datapoints.model_copy(update={
                        **{key: "" for key in flow.datapoints.model_dump()},
                        "power_total": sample_id(flow, channel),
                        **({"power_"+p.lower():sample_id(flow,channel)+":"+p.lower() for p in ("L1","L2","L3")} if flow.electrical_side=="ac" and flow.power_phase_mode=="three" else {}),
                    }),
                }))
        elif flow.run_power_w is not None:
            out.append(flow.model_copy(update={
                "power_unit": "W", "invert": False, "power_phase_mode": flow.power_phase_mode,
                "energy_phase_mode": flow.power_phase_mode, "energy_phase": flow.power_phase,
                "datapoints": flow.datapoints.model_copy(update={
                    **{key: "" for key in flow.datapoints.model_dump()},
                    "power_total": sample_id(flow, "run"),
                }),
            }))
        else:
            out.append(flow.model_copy(update={"category":"grid"}) if flow.kind == "grid" else flow)
    return out
