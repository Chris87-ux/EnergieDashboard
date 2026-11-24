import uuid
from typing import Literal
from datetime import datetime
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field, field_validator, model_validator


class PVArray(BaseModel):
    name: str = Field(default="",max_length=60)
    kwp: float = Field(gt=0,le=10000,allow_inf_nan=False)
    tilt: float = Field(default=30,ge=0,le=90,allow_inf_nan=False)
    azimuth: float = Field(default=0,ge=-180,le=180,allow_inf_nan=False)


class ForecastSite(BaseModel):
    id: str = Field(default_factory=lambda:str(uuid.uuid4()))
    name: str = Field(min_length=1,max_length=80)
    enabled: bool = False
    latitude: float = Field(ge=-90,le=90,allow_inf_nan=False)
    longitude: float = Field(ge=-180,le=180,allow_inf_nan=False)
    timezone: str = ""
    arrays: list[PVArray] = Field(min_length=1,max_length=8)
    actual_flow_ids: list[str] = Field(min_length=1,max_length=100)
    measurement_side: Literal["dc","ac","mixed"] = "dc"
    performance_ratio: float = Field(default=.85,gt=0,le=1.2,allow_inf_nan=False)
    inverter_kw: float | None = Field(default=None,gt=0,allow_inf_nan=False)
    freeze_time: str = "00:05"
    training_days: int = Field(default=45,ge=7,le=365)
    minimum_training_days: int = Field(default=7,ge=3,le=60)
    curtailment_point: str = Field(default="",max_length=512)
    revision: str = ""
    changed_at: float = 0

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls,value):
        if value:
            try:ZoneInfo(value)
            except Exception as exc:raise ValueError("Unbekannte Zeitzone") from exc
        return value
    @field_validator("freeze_time")
    @classmethod
    def valid_freeze(cls,value):
        datetime.strptime(value,"%H:%M")
        if len(value)!=5:raise ValueError("Uhrzeit als HH:MM angeben.")
        return value
    @model_validator(mode="after")
    def constraints(self):
        if len(self.actual_flow_ids)!=len(set(self.actual_flow_ids)):raise ValueError("PV-Istquellen dürfen nicht doppelt zugeordnet werden.")
        if self.minimum_training_days>self.training_days:raise ValueError("Das Lernfenster muss mindestens die Mindestzahl an Tagen enthalten.")
        return self


class ForecastProvider(BaseModel):
    id: str = Field(default_factory=lambda:str(uuid.uuid4()))
    site_id: str
    name: str = Field(min_length=1,max_length=80)
    kind: Literal["vrm","forecast_solar","solcast","open_meteo"]
    enabled: bool = False
    token: str = Field(default="",max_length=8192)
    clear_token: bool = Field(default=False,exclude=True)
    vrm_installation_id: str = Field(default="",pattern=r"^[0-9]*$")
    solcast_resource_ids: list[str] = Field(default_factory=list,max_length=2)
    revision: str = ""
    changed_at: float = 0

    @field_validator("token")
    @classmethod
    def token_header(cls,value):
        if "\r" in value or "\n" in value:raise ValueError("Token darf keine Zeilenumbrüche enthalten.")
        return value
    @field_validator("solcast_resource_ids")
    @classmethod
    def resources(cls,values):
        import re
        if len(values)!=len(set(values)) or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,100}",v) for v in values):raise ValueError("Ungültige oder doppelte Solcast-Ressourcen-ID.")
        return values
