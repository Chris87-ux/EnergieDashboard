"""Source-neutral measurement registry. IDs never depend on source addresses."""
import uuid
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


API_PRESETS = {
    "custom": {"port":80,"api_path":"/{address}","api_json_path":"","api_response_format":"value","api_auth":"none"},
    "iobroker": {"port":8087,"api_path":"/getBulk/{addresses}","api_json_path":"val","api_response_format":"iobroker_bulk","api_auth":"none"},
    "homeassistant": {"port":8123,"api_path":"/api/states/{address}","api_json_path":"state","api_response_format":"value","api_auth":"bearer"},
    "evcc": {"port":7070,"api_path":"/api/state","api_json_path":"result","api_response_format":"value","api_auth":"none"},
}


class Connection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=1, max_length=80)
    protocol: Literal["api", "mqtt", "modbus"]
    host: str = Field(min_length=1, max_length=253)
    port: int = Field(ge=1, le=65535)
    enabled: bool = True
    username: str = ""
    password: str = ""
    tls: bool = False
    timeout_s: float = Field(default=5, ge=0.5, le=30)
    api_preset: Literal["custom","iobroker","homeassistant","evcc"] = "custom"
    api_path: str = Field(default="/{address}",min_length=1,max_length=1024)
    api_json_path: str = Field(default="",max_length=256)
    api_response_format: Literal["value","iobroker_bulk"] = "value"
    api_auth: Literal["none","bearer","basic","header"] = "none"
    api_token_header: str = Field(default="Authorization",pattern=r"^[A-Za-z0-9-]{1,100}$")
    token: str = Field(default="",max_length=8192)
    clear_token: bool = Field(default=False,exclude=True)

    @model_validator(mode="before")
    @classmethod
    def defaults_and_legacy(cls,value):
        if isinstance(value,dict):
            value=dict(value)
            if value.get("protocol")=="iobroker":
                value["protocol"]="api";value["api_preset"]="iobroker"
            if value.get("protocol")=="api":
                preset=API_PRESETS.get(value.get("api_preset","custom"),{})
                for key,default in preset.items():value.setdefault(key,default)
        return value

    @field_validator("api_path")
    @classmethod
    def relative_get_path(cls,value):
        import re
        if not value.startswith("/") or value.startswith("//") or "#" in value or "\\" in value or any(c.isspace() for c in value):
            raise ValueError("API-Aufruf als relativen Pfad ab / ohne Host, Leerzeichen oder Fragment angeben.")
        remaining=value.replace("{address}","").replace("{addresses}","")
        if re.search(r"[{}]",remaining):raise ValueError("API-Variablen sind {address} oder {addresses}.")
        return value

    @field_validator("token")
    @classmethod
    def header_secret(cls,value):
        if "\r" in value or "\n" in value:raise ValueError("Token darf keine Zeilenumbrüche enthalten.")
        return value

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
    unit: Literal["W", "kW", "Wh", "kWh", "%", "Hz", "V", "A", "bool", "°C", "h", "L/h", "L", "m³/h", "m³", "kg/h", "kg", ""] = "W"
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


def validate_measurement(connection, point):
    if connection.protocol=="mqtt":
        if not point.address or "+" in point.address or "#" in point.address:
            raise ValueError("Ein konkretes MQTT-Topic ohne Wildcards ist erforderlich.")
    elif connection.protocol=="api":
        if ("{address}" in connection.api_path or "{addresses}" in connection.api_path or connection.api_preset=="evcc") and not point.address:
            raise ValueError("API-Adresse/Entity bzw. evcc-Wertpfad ist erforderlich.")
