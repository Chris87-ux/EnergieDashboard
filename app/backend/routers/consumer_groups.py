from fastapi import APIRouter,HTTPException
from lib.db import db
from lib.config_lock import locked
from models.consumer_group import ConsumerGroup

router=APIRouter(tags=["Verbrauchergruppen"])


@router.get("/consumer-groups",response_model=list[ConsumerGroup])
@locked
async def groups():
    return await db.consumer_groups.find({}, {"_id":0}).sort([("sort_order",1),("name",1)]).to_list()


@router.put("/consumer-groups/{id}",response_model=ConsumerGroup)
@locked
async def save_group(id:str,body:ConsumerGroup):
    body.id=id
    await db.consumer_groups.replace_one({"id":id},body.model_dump(),upsert=True)
    return body


@router.delete("/consumer-groups/{id}",status_code=204)
@locked
async def delete_group(id:str):
    if await db.flows.find_one({"$or":[{"group_id":id},{"kind":"node","residual.group_id":id}]}):
        raise HTTPException(409,"Zuerst die zugeordneten Verbraucher aus der Gruppe entfernen.")
    result=await db.consumer_groups.delete_one({"id":id})
    if not result.deleted_count:raise HTTPException(404,"Gruppe nicht gefunden.")
