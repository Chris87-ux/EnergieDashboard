from typing import Literal
from pydantic import BaseModel, Field, model_validator


class CycleSettings(BaseModel):
    enabled: bool = False
    mode: Literal["power", "bool"] = "power"
    profile: Literal["washing_machine", "dryer", "dishwasher", "custom"] = "washing_machine"
    signal_point: str = Field(default="", max_length=512)
    start_w: float = Field(default=10, gt=0, allow_inf_nan=False)
    end_w: float = Field(default=5, ge=0, allow_inf_nan=False)
    standby_w: float = Field(default=0.5, ge=0, allow_inf_nan=False)
    start_delay_s: int = Field(default=60, ge=0, le=3600)
    end_delay_s: int = Field(default=600, ge=0, le=7200)
    window_s: int = Field(default=120, ge=0, le=3600)
    minimum_run_s: int = Field(default=300, ge=0, le=86400)
    maximum_run_s: int = Field(default=14400, ge=60, le=172800)

    @model_validator(mode="after")
    def thresholds(self):
        if self.mode == "power" and not self.standby_w <= self.end_w < self.start_w:
            raise ValueError("Standby ≤ Ende < Start muss für die Leistungsschwellen gelten.")
        if self.minimum_run_s >= self.maximum_run_s:
            raise ValueError("Die Mindestlaufzeit muss kleiner als die maximale Laufzeit sein.")
        return self


CYCLE_PRESETS = {
    "washing_machine": CycleSettings().model_dump(),
    "dryer": CycleSettings(profile="dryer", start_w=50, end_w=10, standby_w=1, start_delay_s=30, end_delay_s=300).model_dump(),
    "dishwasher": CycleSettings(profile="dishwasher", start_w=10, end_w=5, start_delay_s=60, end_delay_s=900, minimum_run_s=600, maximum_run_s=21600).model_dump(),
    "bool": CycleSettings(mode="bool", profile="custom", start_delay_s=0, end_delay_s=0, minimum_run_s=0, window_s=0).model_dump(),
}
