"""Persist zero intervals; missing observations never imply continuous zero."""
from pymongo import UpdateOne
from lib.db import db


def next_visibility(previous, power, now, threshold, delay, maximum_gap):
    zero = power is not None and (abs(power) < threshold if threshold > 0 else power == 0)
    since = None
    if zero:
        continuous = previous and 0 <= now - previous.get("last_seen", 0) <= maximum_gap and previous.get("threshold",threshold)==threshold and previous.get("delay",delay)==delay
        since = previous.get("zero_since") if continuous else None
        if since is None:
            since = now
    return {"threshold":threshold,"delay":delay,"last_seen":now,"zero_since":since,"hidden":since is not None and now-since>=delay}


async def update_visibility(flows, now, settings):
    ids = [f.flow_id for f in flows]
    previous = {d["id"]:d for d in await db.visibility.find({"id":{"$in":ids}},{"_id":0}).to_list()}
    operations = []
    gap = min(30, max(settings.live_poll_s,settings.recorder.interval_s if settings.recorder.enabled else 0)*2.5)
    for flow in flows:
        state = next_visibility(previous.get(flow.flow_id), flow.power_w, now,
            settings.appearance.zero_threshold_w,settings.appearance.zero_delay_s,gap)
        if flow.category == "grid":
            state["hidden"],state["zero_since"] = False,None
        flow.hidden, flow.zero_since = state["hidden"],state["zero_since"]
        operations.append(UpdateOne({"id":flow.flow_id},{"$set":state},upsert=True))
    if operations:
        await db.visibility.bulk_write(operations)
