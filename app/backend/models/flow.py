"""Flow configuration schema. `extra="allow"` + `extra` dict + `schema_version` keep it extensible."""

from models.cycles import CycleSettings
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Phase = Literal["L1", "L2", "L3"]
PhaseMode = Literal["single", "three"]
Direction = Literal["in", "out"]
Category = Literal["pv", "generator", "grid", "battery", "heatpump", "ev", "consumer", "custom"]

PHASES: tuple[Phase, ...] = ("L1", "L2", "L3")
SCHEMA_VERSION = 8


class Datapoints(BaseModel):
    """ioBroker state ids. Unknown keys are kept, so new mappings can be added without migration."""

    model_config = ConfigDict(extra="allow")

    ac_input: str = ""
    dc_power: str = ""
    dc_load_power: str = ""
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
    soc_reserve: str = ""
    engine_temperature: str = ""
    efficiency: str = ""
    fuel_consumption: str = ""
    operating_hours: str = ""

    def get(self, key: str) -> str:
        value = self.model_dump().get(key) or ""
        return str(value).strip()


class ResidualSettings(BaseModel):
    name: str = Field(default="", max_length=60)
    group_id: str | None = None
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    icon: str = Field(default="", max_length=80)
    sort_order: int | None = None


class FlowBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str = Field(min_length=1, max_length=60)
    kind: Literal["device", "node", "storage", "grid", "residual"] = "device"
    parent_id: str | None = None
    residual: ResidualSettings = Field(default_factory=ResidualSettings)
    cycle_tracking: CycleSettings = Field(default_factory=CycleSettings)
    group_id: str | None = None
    run_power_w: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    charge_sign: Literal["negative", "positive"] = "negative"
    capacity_kwh: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    fuel_unit: Literal["L/h", "L", "m³/h", "m³", "kg/h", "kg"] = "L/h"
    reserve_soc_pct: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    max_power_w: float = Field(default=5000, gt=0, allow_inf_nan=False)
    electrical_side: Literal["ac", "dc"] = "ac"
    pv_type: Literal["wr", "hybrid", "mppt"] = "wr"
    hybrid_ac_mode: Literal["net", "terminals"] = "net"
    dc_power_unit: Literal["W", "kW"] = "W"
    dc_invert: bool = False
    dc_balance_complete: bool = False
    hybrid_min_power_w: float = Field(default=100, gt=0, allow_inf_nan=False)
    hybrid_id: str | None = None
    storage_ids: list[str] = Field(default_factory=list)
    mppt_ids: list[str] = Field(default_factory=list)
    dc_load_ids: list[str] = Field(default_factory=list)
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

    @model_validator(mode="before")
    @classmethod
    def legacy_types(cls, value):
        if isinstance(value, dict):
            value = dict(value)
            if value.get("kind", "device") == "device" and value.get("category") == "grid":
                value["kind"] = "grid"
            if value.get("kind") == "grid":
                value["category"] = "custom"
            if value.get("kind") == "storage":
                value["category"] = "custom"
        return value

    @model_validator(mode="after")
    def validate_kind(self):
        if self.cycle_tracking.enabled:
            if self.kind != "device" or self.direction != "out" or self.pv_type in ("hybrid", "mppt"):
                raise ValueError("Gerätezyklen sind nur für einzelne Verbrauchsgeräte vorgesehen.")
            if self.cycle_tracking.mode == "bool" and not (self.cycle_tracking.signal_point or self.datapoints.get("run")):
                raise ValueError("Für die Bool-Zykluserkennung ein Betriebssignal zuordnen.")
        for ids in (self.storage_ids, self.mppt_ids, self.dc_load_ids):
            if len(ids) != len(set(ids)):
                raise ValueError("Hybrid-Zuordnungen dürfen keine doppelten Geräte enthalten.")
        if self.dc_load_ids and self.datapoints.get("dc_load_power"):
            raise ValueError("DC-Verbraucher einzeln oder als Sammelmesswert zuordnen, nicht beides gleichzeitig.")
        if self.kind == "device" and self.electrical_side == "dc" and self.direction == "out":
            self.power_phase_mode = self.energy_phase_mode = "single"
        if self.kind == "device" and self.category == "pv" and self.pv_type == "mppt":
            self.electrical_side = "dc"
            self.power_phase_mode = "single"
            self.energy_phase_mode = "single"
            self.direction = "in"
        if self.kind == "storage" and self.electrical_side == "dc":
            self.power_phase_mode = "single"
            self.energy_phase_mode = "single"
        if self.kind != "device" and (self.run_power_w is not None or self.datapoints.get("run")):
            raise ValueError("RUN-Schätzungen werden für Geräte konfiguriert.")
        if self.kind == "grid" and (self.parent_id or self.kind != "grid" or self.electrical_side != "ac"):
            raise ValueError("Der Netzanschluss benötigt Typ Netzanschluss, AC und die Hauptebene.")
        if self.kind == "storage" and not ((self.datapoints.get("power_total") or self.electrical_side == "ac" and self.power_phase_mode == "three" and all(self.datapoints.get("power_" + p.lower()) for p in PHASES)) and self.datapoints.get("soc")):
            raise ValueError("Ein Speicher benötigt einen Leistungs- und einen SOC-Datenpunkt.")
        if self.kind == "device" and bool(self.datapoints.get("run")) != (self.run_power_w is not None):
            raise ValueError("Für RUN sind ein Datenpunkt und eine feste Leistung in Watt erforderlich.")
        if self.group_id and (self.kind not in ("device", "residual") or self.direction!="out" or self.category=="pv" and self.pv_type=="hybrid"):
            raise ValueError("Verbrauchergruppen sind nur für einzelne Verbrauchsgeräte vorgesehen.")
        return self


class FlowCreate(FlowBase):
    pass


class Flow(FlowBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: int = SCHEMA_VERSION
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
