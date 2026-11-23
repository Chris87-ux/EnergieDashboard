import uuid
from pydantic import BaseModel, Field


class ConsumerGroup(BaseModel):
    id: str = Field(default_factory=lambda:str(uuid.uuid4()))
    name: str = Field(min_length=1,max_length=80)
    color: str = Field(default="#38BDF8",pattern=r"^#[0-9A-Fa-f]{6}$")
    sort_order: int = 100
