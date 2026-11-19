from asyncio import Lock

from fastapi import APIRouter, HTTPException

from lib.db import db
from lib.recorder import request_recheck
from lib.store import load_flows
from models.flow import Flow, FlowCreate

router = APIRouter(tags=["flows"])
topology_lock = Lock()


async def validate_parent(flow: Flow) -> None:
    if flow.parent_id == flow.id:
        raise HTTPException(status_code=422, detail="Ein Eintrag kann nicht seinem eigenen Knoten zugeordnet werden.")
    if flow.parent_id and not await db.flows.find_one({"id": flow.parent_id, "kind": "node"}):
        raise HTTPException(status_code=422, detail="Der ausgewählte Knoten existiert nicht.")


@router.get("/flows", response_model=list[Flow])
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
        if await db.flows.find_one({"parent_id": id}):
            raise HTTPException(status_code=409, detail="Zuerst die zugeordneten Geräte und Speicher verschieben.")
        res = await db.flows.delete_one({"id": id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Fluss nicht gefunden")
    request_recheck()


