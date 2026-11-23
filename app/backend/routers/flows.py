from fastapi import APIRouter, HTTPException

from lib.db import db
from lib.recorder import request_recheck
from lib.store import load_flows
from models.flow import Flow, FlowCreate

router = APIRouter(tags=["flows"])
from lib.config_lock import config_lock, locked
topology_lock = config_lock


async def validate_parent(flow: Flow) -> None:
    if flow.group_id and not await db.consumer_groups.find_one({"id":flow.group_id}):
        raise HTTPException(422,"Die ausgewählte Verbrauchergruppe existiert nicht.")
    if flow.kind == "device" and flow.category == "pv" and flow.pv_type == "mppt":
        if not flow.datapoints.get("power_total") or flow.run_power_w is not None or flow.datapoints.get("run"):
            raise HTTPException(422,"DC-MPPT benötigt einen DC-Leistungsdatenpunkt und unterstützt keine RUN-Schätzung.")
    if flow.kind == "device" and flow.category == "pv" and flow.pv_type == "hybrid":
        if flow.electrical_side != "ac" or flow.run_power_w is not None:
            raise HTTPException(422,"Hybrid-WR verwendet gemessene AC-Leistung, keine RUN-Schätzung.")
        if not (flow.datapoints.get("power_total") or flow.power_phase_mode == "three" and all(flow.datapoints.get("power_"+p.lower()) for p in ("L1","L2","L3"))):
            raise HTTPException(422,"Hybrid-WR benötigt AC-Gesamtleistung oder vollständige Phasenwerte.")
        if flow.hybrid_ac_mode == "terminals" and not flow.datapoints.get("ac_input"):
            raise HTTPException(422,"Für AC-In/Out ist auch ein AC-Eingangsleistungsdatenpunkt erforderlich.")
    if flow.kind == "storage" and flow.capacity_kwh is None:
        raise HTTPException(422, "Bitte die feste Gesamtkapazität des Speichers in kWh angeben.")
    if flow.kind == "device" and flow.category == "pv" and flow.pv_type == "hybrid" and not flow.storage_ids:
        raise HTTPException(422, "Ein Hybrid-WR benötigt mindestens einen zugeordneten DC-Speicher.")
    if flow.kind == "node" and flow.electrical_side != "ac":
        raise HTTPException(422, "Abschnittszähler bilden das AC-Netz ab. DC-Messungen als Gerät/MPPT anlegen.")
    if flow.kind == "grid":
        if not any(flow.datapoints.get(k) for k in ("power_total", "power_l1", "power_l2", "power_l3")):
            raise HTTPException(422, "Der Netzanschluss benötigt einen Leistungsdatenpunkt.")
        if flow.enabled:
            other = await db.flows.find({"kind": "grid", "enabled": True, "id": {"$ne": flow.id}}).to_list()
            if any(flow.grid_mode == "signed" or d.get("grid_mode") == "signed" or d.get("direction") == flow.direction for d in other):
                raise HTTPException(422, "Netzanschluss entweder als einen vorzeichenbehafteten Wert oder als je einen Wert für Bezug und Einspeisung anlegen.")
    if flow.parent_id == flow.id:
        raise HTTPException(status_code=422, detail="Ein Eintrag kann nicht seinem eigenen Knoten zugeordnet werden.")
    if flow.parent_id and not await db.flows.find_one({"id": flow.parent_id, "kind": "node"}):
        raise HTTPException(status_code=422, detail="Der ausgewählte Knoten existiert nicht.")
    seen = {flow.id}
    parent = flow.parent_id
    while parent:
        if parent in seen:
            raise HTTPException(422, "Die Knotenzuordnung würde einen Kreis erzeugen.")
        seen.add(parent)
        doc = await db.flows.find_one({"id": parent})
        parent = doc.get("parent_id") if doc else None
    for ids, kind in ((flow.storage_ids, "storage"), (flow.mppt_ids, "device")):
        for id in ids:
            doc = await db.flows.find_one({"id": id, "kind": kind})
            if not doc or id == flow.id or (kind == "device" and doc.get("pv_type") != "mppt"):
                raise HTTPException(422, "Ungültige Hybrid-Zuordnung. Speicher bzw. DC-MPPT zuerst anlegen.")
            if kind == "storage" and doc.get("electrical_side","dc") != "dc":
                raise HTTPException(422,"Einem Hybrid-WR dürfen nur DC-Speicher zugeordnet werden.")
            field = "storage_ids" if kind == "storage" else "mppt_ids"
            if await db.flows.find_one({"id": {"$ne": flow.id}, field: id}):
                raise HTTPException(422, "Dieser Eintrag ist bereits einem Hybrid-WR zugeordnet.")
    if flow.storage_ids or flow.mppt_ids:
        if flow.kind != "device" or flow.category != "pv" or flow.pv_type != "hybrid":
            raise HTTPException(422, "Speicher-/MPPT-Auswahl gehört zu einem PV-Hybrid-WR.")


@router.get("/schemas/flow")
async def flow_schema():
    return FlowCreate.model_json_schema()


@router.get("/flows", response_model=list[Flow])
@locked
async def list_flows():
    return await load_flows()


@router.post("/flows", response_model=Flow, status_code=201)
async def create_flow(body: FlowCreate):
    flow = Flow(**body.model_dump(exclude={"id", "created_at", "schema_version"}))
    async with topology_lock:
        await validate_parent(flow)
        await db.flows.insert_one(flow.model_dump())
    request_recheck()
    return flow


@router.get("/flows/{id}", response_model=Flow)
@locked
async def get_flow(id: str):
    doc = await db.flows.find_one({"id": id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Fluss nicht gefunden")
    return Flow(**doc)


@router.put("/flows/{id}", response_model=Flow)
async def update_flow(id: str, body: FlowCreate):
    async with topology_lock:
        doc = await db.flows.find_one({"id": id}, {"_id": 0})
        if not doc:
            raise HTTPException(status_code=404, detail="Fluss nicht gefunden")
        if (body.kind != "storage" or body.electrical_side != "dc") and await db.flows.find_one({"storage_ids": id}):
            raise HTTPException(409, "Zuerst die Speicherzuordnung im Hybrid-WR entfernen.")
        if (body.kind != "device" or body.category != "pv" or body.pv_type != "mppt") and await db.flows.find_one({"mppt_ids": id}):
            raise HTTPException(409, "Zuerst die MPPT-Zuordnung im Hybrid-WR entfernen.")
        if doc.get("kind") == "grid" and doc.get("enabled", True) and (not body.enabled or body.kind != "grid"):
            if not await db.flows.find_one({"kind": "grid", "enabled": True, "id": {"$ne": id}}):
                raise HTTPException(409, "Mindestens ein aktiver Netzanschluss muss bestehen bleiben.")
        if body.kind != doc.get("kind", "device") and await db.flows.find_one({"parent_id": id}):
            raise HTTPException(status_code=409, detail="Zuerst die zugeordneten Geräte und Speicher verschieben.")
        flow = Flow(**{**body.model_dump(exclude={"id", "created_at", "schema_version"}), "id": id, "created_at": doc["created_at"]})
        await validate_parent(flow)
        result = await db.flows.replace_one({"id": id}, flow.model_dump())
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Fluss nicht gefunden")
    request_recheck()
    return flow


@router.delete("/flows/{id}", status_code=204)
async def delete_flow(id: str):
    async with topology_lock:
        doc = await db.flows.find_one({"id": id})
        if doc and doc.get("kind") == "grid" and doc.get("enabled", True):
            if not await db.flows.find_one({"kind": "grid", "enabled": True, "id": {"$ne": id}}):
                raise HTTPException(409, "Zuerst einen neuen Netzanschluss anlegen.")
        if await db.flows.find_one({"$or": [{"storage_ids": id}, {"mppt_ids": id}]}):
            raise HTTPException(409, "Zuerst die Hybrid-WR-Zuordnung entfernen.")
        if await db.flows.find_one({"parent_id": id}):
            raise HTTPException(status_code=409, detail="Zuerst die zugeordneten Geräte und Speicher verschieben.")
        res = await db.flows.delete_one({"id": id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Fluss nicht gefunden")
    request_recheck()


