"""Source-neutral measurement registry. IDs never depend on source addresses."""
import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Connection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=1, max_length=80)
    protocol: Literal["iobroker", "mqtt", "modbus"]
    host: str = Field(min_length=1, max_length=253)
    port: int = Field(ge=1, le=65535)
    enabled: bool = True
    username: str = ""
    password: str = ""
    tls: bool = False
    timeout_s: float = Field(default=5, ge=0.5, le=30)

    @model_validator(mode="after")
    def host_only(self):
        from models.settings import IoBrokerSettings
        self.host = IoBrokerSettings(host=self.host).host
        return self


class Measurement(BaseModel):
    model_config = ConfigDict(serialize_by_alias=True)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=1, max_length=100)
    connection_id: str
    enabled: bool = True
    record: bool = True
    unit: Literal["W", "kW", "Wh", "kWh", "%", "Hz", "V", "A", "bool", "°C", ""] = "W"
    address: str = Field(default="", max_length=512)
    json_path: str = Field(default="", max_length=256)
    scale: float = Field(default=1, allow_inf_nan=False)
    offset: float = Field(default=0, allow_inf_nan=False)
    stale_s: int = Field(default=120, ge=5, le=86400)
    unit_id: int = Field(default=1, ge=0, le=247)
    register_address: int = Field(default=0, ge=0, le=65535, alias="register")
    function: Literal[3, 4] = 3
    datatype: Literal["uint16", "int16", "uint32", "int32", "float32", "float64"] = "uint16"
    byte_order: Literal["big", "little"] = "big"
    word_order: Literal["big", "little"] = "big"
    # Kept through migrations so historical measurements remain accessible.
    history_key: str = ""
    legacy_until: float | None = None
