"""Flow configuration schema. `extra="allow"` + `extra` dict + `schema_version` keep it extensible."""

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Phase = Literal["L1", "L2", "L3"]
PhaseMode = Literal["single", "three"]
Direction = Literal["in", "out"]
Category = Literal["pv", "grid", "battery", "heatpump", "ev", "consumer", "custom"]

PHASES: tuple[Phase, ...] = ("L1", "L2", "L3")
SCHEMA_VERSION = 3


class Datapoints(BaseModel):
    """ioBroker state ids. Unknown keys are kept, so new mappings can be added without migration."""

    model_config = ConfigDict(extra="allow")

    power_total: str = ""
    power_l1: str = ""
    power_l2: str = ""
    power_l3: str = ""
    energy_import: str = ""
    energy_export: str = ""
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
    capacity_kwh: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    reserve_soc_pct: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    max_power_w: float = Field(default=5000, gt=0, allow_inf_nan=False)
    electrical_side: Literal["ac", "dc"] = "ac"
    pv_type: Literal["wr", "hybrid", "mppt"] = "wr"
    hybrid_id: str | None = None
    storage_ids: list[str] = Field(default_factory=list)
    mppt_ids: list[str] = Field(default_factory=list)
    grid_mode: Literal["directional", "signed"] = "directional"
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

    @field_validator("extra")
    @classmethod
    def json_metadata(cls, value):
        import json
        try:
            encoded = json.dumps(value, allow_nan=False)
        except (ValueError, TypeError, RecursionError) as exc:
            raise ValueError("Zusatzfelder müssen gültige JSON-Werte mit endlichen Zahlen enthalten.") from exc
        if len(encoded.encode("utf-8")) > 16384:
            raise ValueError("Zusatzfelder dürfen höchstens 16 KiB belegen.")
        return value

    @model_validator(mode="after")
    def validate_kind(self):
        if self.kind == "storage":
            self.electrical_side = "dc"
        if self.kind != "device" and (self.run_power_w is not None or self.datapoints.get("run")):
            raise ValueError("RUN-Schätzungen werden für Geräte konfiguriert.")
        if self.category == "grid" and (self.parent_id or self.kind != "device"):
            raise ValueError("Der Netzanschluss muss ein Gerät auf der Hauptebene sein.")
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
