from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Method = Literal["counter_delta", "phase_sum", "power_integral", "run_estimate", "unavailable", "not_applicable"]


class Gap(BaseModel):
    start: datetime
    end: datetime


class EnergyValue(BaseModel):
    kwh: float | None
    method: Method
    coverage: float = 0.0
    complete: bool = False
    gaps: list[Gap] = Field(default_factory=list)
    resets: int = 0
    note: str = ""


class FlowEnergy(BaseModel):
    flow_id: str
    name: str
    category: str
    direction: str
    color: str
    icon: str
    energy_phase_mode: str
    energy_phase: str
    total: EnergyValue
    phases: dict[str, EnergyValue]
    parent_id: str | None = None
    storage_id: str | None = None


class EnergyTotals(BaseModel):
    in_kwh: float | None
    out_kwh: float | None
    incomplete: bool


class EnergyReport(BaseModel):
    start: datetime
    end: datetime
    effective_end: datetime
    start_local: str
    end_local: str
    timezone: str
    mode: Literal["live"] = "live"
    step_s: int
    gap_threshold_s: int
    flows: list[FlowEnergy]
    totals: EnergyTotals
    errors: list[str] = Field(default_factory=list)


class RangePreset(BaseModel):
    key: str
    label: str
    start: str
    end: str


class LiveFlow(BaseModel):
    flow_id: str
    name: str
    category: str
    direction: str
    color: str
    icon: str
    power_phase_mode: str
    power_phase: str
    power_w: float | None
    phases: dict[str, float | None]
    frequency_hz: float | None
    available: bool
    parent_id: str | None = None
    estimated: bool = False
    storage_id: str | None = None


class LiveStorage(BaseModel):
    id: str
    name: str
    parent_id: str | None
    soc_pct: float | None
    charge_w: float | None
    discharge_w: float | None


class LiveNode(BaseModel):
    id: str
    name: str
    phase_mode: Literal["single", "three"]
    phase: str
    phases: dict[str, float | None]
    meter_w: float | None
    children_w: float | None
    difference_w: float | None


class LiveSummary(BaseModel):
    in_w: float | None
    out_w: float | None
    pv_w: float | None
    grid_import_w: float | None
    grid_export_w: float | None
    battery_charge_w: float | None
    battery_discharge_w: float | None
    consumption_w: float | None
    house_rest_w: float | None
    autarky_pct: float | None
    self_consumption_pct: float | None


class LiveReport(BaseModel):
    ts: datetime
    mode: Literal["live"] = "live"
    ok: bool
    errors: list[str] = Field(default_factory=list)
    site_name: str
    poll_s: int
    frequency_hz: float | None
    flows: list[LiveFlow]
    nodes: list[LiveNode] = Field(default_factory=list)
    storages: list[LiveStorage] = Field(default_factory=list)
    summary: LiveSummary
