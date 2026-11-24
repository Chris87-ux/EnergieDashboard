import uuid
from typing import Literal
from pydantic import BaseModel, Field, model_validator


class ChartSeries(BaseModel):
    kind: Literal["measurement", "power", "soc", "charge", "discharge", "status", "cycles"] = "measurement"
    reference_id: str = Field(min_length=1, max_length=160)
    label: str = Field(default="", max_length=100)
    color: str = Field(default="#38BDF8", pattern=r"^#[0-9A-Fa-f]{6}$")
    unit: str = ""


class ChartConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=1, max_length=80)
    series: list[ChartSeries] = Field(min_length=1, max_length=8)
    sort_order: int = 100

    @model_validator(mode="after")
    def unique_sources(self):
        keys = [(s.kind, s.reference_id) for s in self.series]
        if len(keys) != len(set(keys)):
            raise ValueError("Eine Quelle darf nur einmal im Chart vorkommen.")
        return self
