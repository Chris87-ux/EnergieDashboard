"""Persisted, elapsed-time device cycle detection; no device control or notifications."""
from copy import deepcopy
import hashlib
import json
import uuid
from lib.db import db

OFF, READY, RUNNING, PAUSED, FINISHED, UNKNOWN, STARTING = range(7)


def weighted_mean(samples, now, window):
    if not samples: return None
    if window<=0: return samples[-1][1]
    left=now-window;energy=0.;duration=0.
    for index,(timestamp,value) in enumerate(samples):
        end=min(now,samples[index+1][0] if index+1<len(samples) else now)
        seconds=max(0,end-max(left,timestamp))
        energy+=value*seconds;duration+=seconds
    return energy/duration if duration else samples[-1][1]


def advance(previous, config, value, now, interval=15):
    """Pure transition. An existing session ID makes completion retries idempotent."""
    state=deepcopy(previous) if previous else {"phase":"idle","seen_idle":False,"finished":False,"samples":[],"status":UNKNOWN}
    if state.get("last_tick") is not None and now<=state["last_tick"]:
        return state,None
    state["last_tick"]=now;event=None
    def close(outcome, end):
        nonlocal event
        event={"id":state["session_id"],"started_at":state["started_at"],"ended_at":end,"detected_at":now,"outcome":outcome,"observed_start":state.get("observed_start",False),"had_gap":state.get("had_gap",False)}
        state.update(phase="idle",samples=[],finished=outcome=="completed",seen_idle=True,runtime_alarm=False)
        for key in ("session_id","started_at","observed_start","low_since","start_since"):state.pop(key,None)
    if state.get("last_valid") is not None and now-state["last_valid"]>max(3*interval,30):
        if state.get("session_id"):close("interrupted",state["last_valid"])
        state.update(phase="idle",samples=[],seen_idle=False,finished=False)
        state.pop("start_since",None);state.pop("low_since",None)
    if value is None:
        state["status"]=UNKNOWN;state["had_gap"]=True
        state.pop("low_since",None);state.pop("start_since",None)
        if state["phase"]=="starting":state["phase"]="idle"
        return state,event
    value=abs(float(value));state["last_valid"]=now;state["last_power"]=value
    samples=state.setdefault("samples",[]);samples.append([now,value])
    while len(samples)>1 and samples[1][0]<now-config.window_s:samples.pop(0)
    mean=weighted_mean(samples,now,config.window_s);state["mean_w"]=mean
    high=value!=0 if config.mode=="bool" else value>=config.start_w
    low=value==0 if config.mode=="bool" else value<=config.end_w
    delay_start=0 if config.mode=="bool" else config.start_delay_s
    delay_end=0 if config.mode=="bool" else config.end_delay_s
    minimum=0 if config.mode=="bool" else config.minimum_run_s
    if state["phase"] in ("idle","starting"):
        if high:
            state.setdefault("start_since",now)
            state["phase"]="starting";state["status"]=STARTING
            if now-state["start_since"]>=delay_start:
                state.update(phase="running",status=RUNNING,session_id=str(uuid.uuid4()),started_at=state["start_since"],observed_start=state.get("seen_idle",False),finished=False,had_gap=False,runtime_alarm=False)
                state.pop("low_since",None)
        else:
            state.update(phase="idle",seen_idle=True)
            state.pop("start_since",None)
            state["status"]=FINISHED if state.get("finished") else OFF if value<=config.standby_w else READY
    elif state["phase"] in ("running","ending"):
        state["runtime_alarm"]=now-state["started_at"]>config.maximum_run_s
        if low:
            state.setdefault("low_since",now);state["phase"]="ending";state["status"]=PAUSED
            if now-state["low_since"]>=delay_end and (config.mode=="bool" or mean<=config.end_w):
                observed=state.get("observed_start",False)
                duration=state["low_since"]-state["started_at"]
                close("completed" if observed and duration>=minimum else "aborted" if observed else "unobserved",state["low_since"])
                state["status"]=FINISHED if state["finished"] else OFF if value<=config.standby_w else READY
        else:
            state.pop("low_since",None);state["phase"]="running";state["status"]=RUNNING
    return state,event


def tracking_signature(flow):
    data={"config":flow.cycle_tracking.model_dump(),"datapoints":flow.datapoints.model_dump(),"power_unit":flow.power_unit,"run_power_w":flow.run_power_w,"invert":flow.invert,"power_phase_mode":flow.power_phase_mode}
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()


async def tick_cycles(flows,values,now,settings):
    from lib.hybrid import dc_device_power
    from lib.sources import LiveSource
    from lib.topology import history_flows
    from lib.energy import compute_flow,pick_step
    samples=[]
    for flow in flows:
        config=flow.cycle_tracking
        if not config.enabled or flow.kind!="device" or flow.direction!="out":continue
        prior=await db.cycle_states.find_one({"id":flow.id},{"_id":0})
        signature=tracking_signature(flow)
        if prior and prior.get("signature")!=signature:
            if prior.get("session_id"):
                await db.cycle_events.update_one({"id":prior["session_id"]},{"$setOnInsert":{"id":prior["session_id"],"device_id":flow.id,"name":flow.name,"started_at":prior["started_at"],"ended_at":prior.get("last_valid",now),"detected_at":now,"outcome":"reconfigured"}},upsert=True)
            prior=None
        value=values.get(config.signal_point or flow.datapoints.get("run")) if config.mode=="bool" else dc_device_power(flow,values)
        state,event=advance(prior,config,value,now,settings.recorder.interval_s)
        if event:
            document={**event,"device_id":flow.id,"name":flow.name,"energy_kwh":None,"energy_complete":False}
            result=await db.cycle_events.update_one({"id":event["id"]},{"$setOnInsert":document},upsert=True)
            if result.upserted_id and event["outcome"]=="completed" and event["ended_at"]>event["started_at"]:
                try:
                    mapped=history_flows([flow])[0]
                    energy=await compute_flow(mapped,LiveSource(settings),event["started_at"],event["ended_at"],pick_step(event["started_at"],event["ended_at"]),settings.gap_threshold_min*60)
                    await db.cycle_events.update_one({"id":event["id"]},{"$set":{"energy_kwh":energy.total.kwh,"energy_complete":energy.total.complete}})
                except Exception:
                    # The completed cycle is durable even when its energy query is unavailable.
                    pass
        count=await db.cycle_events.count_documents({"device_id":flow.id,"outcome":"completed"})
        state.update(id=flow.id,signature=signature,count=count)
        await db.cycle_states.replace_one({"id":flow.id},state,upsert=True)
        samples.extend([{"dp":"cycles:"+flow.id+":status","ts":now,"v":state["status"],"valid_until":now+settings.recorder.interval_s*2.5},{"dp":"cycles:"+flow.id+":cycles","ts":now,"v":count,"valid_until":now+settings.recorder.interval_s*2.5}])
    return samples
