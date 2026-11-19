from models.flow import Flow


def sample_id(flow: Flow, channel: str) -> str:
    return f"energieboard:{flow.id}:{channel}"


def derived_samples(flows: list[Flow], values: dict[str, float | None], now: float, interval_s: int = 15) -> list[dict]:
    samples = []
    for flow in flows:
        if flow.kind == "storage":
            value = values.get(flow.datapoints.get("power_total"))
            if value is None:
                continue
            signed = value * (1000 if flow.power_unit == "kW" else 1)
            signed *= 1 if flow.charge_sign == "positive" else -1
            channels = {"charge": max(signed, 0), "discharge": max(-signed, 0)}
        elif flow.kind == "device" and flow.run_power_w is not None:
            value = values.get(flow.datapoints.get("run"))
            if value is None:
                continue
            channels = {"run": flow.run_power_w if value != 0 else 0}
        else:
            continue
        samples.extend({"dp": sample_id(flow, key), "ts": now, "v": value, "valid_until": now + interval_s * 2.5} for key, value in channels.items())
    return samples


def history_flows(flows: list[Flow]) -> list[Flow]:
    out = []
    for flow in flows:
        if flow.kind == "node":
            continue
        if flow.kind == "storage":
            for channel, direction, suffix in (("charge", "out", "Laden"), ("discharge", "in", "Entladen")):
                out.append(flow.model_copy(update={
                    "id": f"{flow.id}:{channel}", "name": f"{flow.name} · {suffix}",
                    "category": "battery", "direction": direction, "power_unit": "W",
                    "power_phase_mode": "single", "energy_phase_mode": "single",
                    "energy_phase": flow.power_phase, "invert": False,
                    "datapoints": flow.datapoints.model_copy(update={
                        **{key: "" for key in flow.datapoints.model_dump()},
                        "power_total": sample_id(flow, channel),
                    }),
                }))
        elif flow.run_power_w is not None:
            out.append(flow.model_copy(update={
                "power_unit": "W", "invert": False, "power_phase_mode": "single",
                "energy_phase_mode": "single", "energy_phase": flow.power_phase,
                "datapoints": flow.datapoints.model_copy(update={
                    **{key: "" for key in flow.datapoints.model_dump()},
                    "power_total": sample_id(flow, "run"),
                }),
            }))
        else:
            out.append(flow)
    return out
