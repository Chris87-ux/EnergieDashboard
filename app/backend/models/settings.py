from typing import Literal
from ipaddress import ip_address
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field, field_validator


class IoBrokerSettings(BaseModel):
    host: str = ""
    port: int = Field(default=8087, ge=1, le=65535)
    protocol: Literal["http", "https"] = "http"
    timeout_s: float = Field(default=5.0, ge=0.5, le=60)

    @field_validator("host")
    @classmethod
    def valid_host(cls, value: str) -> str:
        value = value.strip()
        if any(character.isspace() for character in value) or any(character in value for character in "/?#@"):
            raise ValueError("Nur Hostname oder IP angeben. Protokoll und Port werden separat eingestellt.")
        if ":" in value:
            try:
                ip_address(value.strip("[]"))
            except ValueError as exc:
                raise ValueError("Den Port im separaten Port-Feld angeben.") from exc
        return value.strip("[]")


class InfluxSettings(BaseModel):
    enabled: bool = False
    version: Literal["v1", "v2"] = "v1"
    url: str = "http://localhost:8086"
    database: str = "iobroker"
    username: str = ""
    password: str = ""
    org: str = ""
    bucket: str = "iobroker"
    token: str = ""
    field: str = "value"
    timeout_s: float = Field(default=15.0, ge=1, le=120)

    @field_validator("url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.query or parsed.fragment or parsed.username:
            raise ValueError("Eine http-/https-URL ohne Zugangsdaten und Abfrageparameter angeben.")
        try:
            parsed.port
        except ValueError as exc:
            raise ValueError("Ungültiger Port in der InfluxDB-URL.") from exc
        return value


class RecorderSettings(BaseModel):
    enabled: bool = True
    interval_s: int = Field(default=15, ge=5, le=3600)


class Appearance(BaseModel):
    zero_threshold_w: float = Field(default=1, ge=0, le=100, allow_inf_nan=False)
    zero_delay_s: int = Field(default=60, ge=1, le=3600)
    layout: Literal["square", "rounded", "flow"] = "rounded"
    background: str = Field(default="#0B132B", pattern=r"^#[0-9A-Fa-f]{6}$")
    surface: str = Field(default="#111D42", pattern=r"^#[0-9A-Fa-f]{6}$")
    accent: str = Field(default="#38BDF8", pattern=r"^#[0-9A-Fa-f]{6}$")


class AppSettings(BaseModel):
    appearance: Appearance = Field(default_factory=Appearance)
    site_name: str = Field(default="Mein Zuhause", min_length=1, max_length=80)
    timezone: str = "Europe/Berlin"
    live_poll_s: int = Field(default=5, ge=1, le=300)
    gap_threshold_min: int = Field(default=15, ge=1, le=1440)
    iobroker: IoBrokerSettings = Field(default_factory=IoBrokerSettings)
    influx: InfluxSettings = Field(default_factory=InfluxSettings)
    recorder: RecorderSettings = Field(default_factory=RecorderSettings)

    @field_validator("timezone")
    @classmethod
    def _valid_tz(cls, v: str) -> str:
        try:
            ZoneInfo(v)
        except Exception as exc:
            raise ValueError("Unbekannte Zeitzone") from exc
        return v


class SettingsOut(AppSettings):
    """Secrets are never returned; the *_set flags tell the UI whether one is stored."""

    influx_password_set: bool = False
    influx_token_set: bool = False


class TestResult(BaseModel):
    ok: bool
    message: str
    details: list[str] = Field(default_factory=list)


class RecorderStatus(BaseModel):
    state: Literal["idle", "disabled", "waiting", "recording", "error"] = "idle"
    message: str = ""
    last_run: str | None = None
    last_error: str | None = None
    recorded_dps: list[str] = Field(default_factory=list)
    influx_dps: list[str] = Field(default_factory=list)
    samples_written: int = 0
    samples_total: int = 0
