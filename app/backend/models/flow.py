"""Flow configuration schema. `extra="allow"` + `extra` dict + `schema_version` keep it extensible."""

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Phase = Literal["L1", "L2", "L3"]
PhaseMode = Literal["single", "three"]
Direction = Literal["in", "out"]
Category = Literal["pv", "grid", "battery", "heatpump", "ev", "consumer", "custom"]

PHASES: tuple[Phase, ...] = ("L1", "L2", "L3")
SCHEMA_VERSION = 2


class Datapoints(BaseModel):
    """ioBroker state ids. Unknown keys are kept, so new mappings can be added without migration."""

    model_config = ConfigDict(extra="allow")

    power_total: str = ""
    power_l1: str = ""
    power_l2: str = ""
    power_l3: str = ""
    energy_total: str = ""
    energy_l1: str = ""
    energy_l2: str = ""
    energy_l3: str = ""
    frequency: str = ""
    run: str = ""
    soc: str = ""

    def get(self, key: str) -> str:
        value = self.model_dump().get(key) or ""
        return str(value).strip()


class FlowBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(min_length=1, max_length=60)
    kind: Literal["device", "node", "storage"] = "device"
    parent_id: str | None = None
    run_power_w: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    charge_sign: Literal["negative", "positive"] = "negative"
    category: Category = "consumer"
    direction: Direction = "out"
    icon: str = "plug"
    color: str = Field(default="#38BDF8", pattern=r"^#[0-9A-Fa-f]{6}$")
    enabled: bool = True
    sort_order: int = 0
    power_phase_mode: PhaseMode = "single"
    power_phase: Phase = "L1"
    energy_phase_mode: PhaseMode = "single"
    energy_phase: Phase = "L1"
    power_unit: Literal["W", "kW"] = "W"
    energy_unit: Literal["Wh", "kWh"] = "kWh"
    invert: bool = False
    datapoints: Datapoints = Field(default_factory=Datapoints)
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_kind(self):
        if self.kind != "device" and (self.run_power_w is not None or self.datapoints.get("run")):
            raise ValueError("RUN-Schätzungen werden für Geräte konfiguriert.")
        if self.kind == "node" and self.parent_id:
            raise ValueError("Knoten werden auf der obersten Ebene angelegt.")
        if self.kind == "storage" and not (self.datapoints.get("power_total") and self.datapoints.get("soc")):
            raise ValueError("Ein Speicher benötigt einen Leistungs- und einen SOC-Datenpunkt.")
        if self.kind == "device" and bool(self.datapoints.get("run")) != (self.run_power_w is not None):
            raise ValueError("Für RUN sind ein Datenpunkt und eine feste Leistung in Watt erforderlich.")
        return self


class FlowCreate(FlowBase):
    pass


class Flow(FlowBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: int = SCHEMA_VERSION
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
