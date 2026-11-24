# Data model, API and additional JSON

[Documentation](README.md) · [Configuration walkthrough](GETTING-STARTED.md)

Application 2.6.0, schema **6**, CSV **1**. For exact required types/defaults/limits use the live schemas and OpenAPI. This reference complements [device balance](DEVICES-AND-NODES.md), [hybrid boundaries](STORAGE-AND-HYBRID.md) and [data acquisition](DATA-ACQUISITION.md).

## API and language

Interactive API documentation: `http://<SERVER-IP>:8000/docs`; OpenAPI: `/openapi.json`. The API has the same network/proxy protection as the application, with no built-in login. Health: `GET /api/` reports version, status and schema, or 503 when MongoDB is unavailable.

Send `Accept-Language: en` for English built-in diagnostics, validation messages, notes and period labels; use de for German. Supported regional tags and quality priorities are respected, with German as fallback. JSON responses set Content-Language and vary by Accept-Language. Numeric readings, machine keys, enums, IDs, names and custom metadata stay unchanged. CSV remains language-neutral. Stored messages/samples are not rewritten by language selection.

## Endpoints

| Resource | Routes |
|---|---|
| Flows | GET/POST `/api/flows`; PUT/DELETE `/api/flows/<id>` |
| Connections | GET `/api/connections`; PUT/DELETE `/api/connections/<id>` |
| Measurements | GET `/api/measurements`; PUT/DELETE `/api/measurements/<id>` |
| Measurement diagnosis | GET `/api/measurements/live` |
| API preset defaults | GET `/api/api-presets` |
| Consumer groups | GET `/api/consumer-groups`; PUT/DELETE `/api/consumer-groups/<id>` |
| Live report | GET `/api/live` |
| Energy | GET `/api/energy?preset=today`, or start/end query parameters |
| Period presets | GET `/api/energy/presets` |
| Settings | GET/PUT `/api/settings` |
| Connection tests | POST `/api/settings/test/iobroker`, `/api/settings/test/influx` |
| Recorder | GET `/api/recorder/status` |
| Schemas | GET `/api/schemas/flow`, `/api/schemas/connection`, `/api/schemas/measurement` |
| CSV | GET `/api/config/csv`; POST `/api/config/csv/preview`, `/api/config/csv/apply` |

PUT submits the complete intended configuration, not a partial PATCH. Let the server create flow id/schema_version/created_at for new POST entries. Measurement/connection/group PUT uses the URL ID. Keep existing IDs when editing. The energy API accepts IANA time zones through system settings and limits a single selected range to 400 days.

## Connections

Fields: `id`, `name` (1–80 characters), `protocol` (api/mqtt/modbus), `host` (hostname/IP only), `port` (1–65535), `enabled`, `tls`, `timeout_s` (0.5–30), `username`, `password`.

API-only fields: `api_preset` (custom/iobroker/homeassistant/evcc), `api_path` (relative GET path, up to 1024 characters), `api_json_path` (up to 256), `api_response_format` (value/iobroker_bulk), `api_auth` (none/basic/bearer/header), `api_token_header` (default Authorization), `token`, and transient `clear_token`.

Presets fill omitted settings, including ports. Explicit settings remain authoritative. Legacy `protocol=iobroker` is accepted and normalised to API/ioBroker. Token/header validation rejects invalid newlines/header names. Request variables are `{address}` and `{addresses}`; JSON extraction rules and authenticating examples are in [Data acquisition](DATA-ACQUISITION.md).

Normal responses return empty password/token plus password_set/token_set flags. Empty secrets on save retain stored values. `clear_token=true` explicitly removes a token. Credentials remain in the database/full backup and are excluded from CSV.

Example API connection:

```json
{
  "name": "Home Assistant",
  "protocol": "api",
  "api_preset": "homeassistant",
  "host": "192.168.10.20",
  "port": 8123,
  "api_path": "/api/states/{address}",
  "api_json_path": "state",
  "api_response_format": "value",
  "api_auth": "bearer",
  "token": "REPLACE_WITH_YOUR_TOKEN"
}
```

## Measurements

Fields: `id`, `name` (1–100), `connection_id`, `enabled`, `record`, `unit`, `address` (up to 512), `json_path` (up to 256), `scale`, `offset`, `stale_s` (5–86400). `history_key` and `legacy_until` preserve old history and are server-managed.

For MQTT address is an exact topic. For API it is a state/entity/request variable, or evcc relative value path. For Modbus use `unit_id` (0–247), `register` (zero-based 0–65535), `function` (3/4), `datatype` (uint16/int16/uint32/int32/float32/float64), `byte_order` and `word_order` (big/little).

Scale and offset must be finite. Converted unit must match device unit; supported units are W, kW, Wh, kWh, %, Hz, V, A, bool, °C, h, L/h, L, m³/h, m³, kg/h, kg and empty. `record` stores normalised raw values; derived channels can still be recorded for configured devices. Existing history is not rescaled after a mapping change.

```json
{
  "name": "Grid power",
  "connection_id": "EXISTING-CONNECTION-ID",
  "address": "sensor.grid_power",
  "unit": "W",
  "scale": 1,
  "offset": 0,
  "enabled": true,
  "record": true
}
```

## Flow fields

| Field | Meaning / allowed values |
|---|---|
| name | User display name, 1–60 characters |
| kind | device, node, grid, storage |
| parent_id | Existing parent node ID or null |
| group_id | Additional consumer group ID or null; normal consumers only |
| category | pv, generator, heatpump, ev, consumer, custom; grid/battery retained internally for compatibility |
| direction | in = production, out = consumption |
| electrical_side | ac or dc |
| enabled / sort_order | Active evaluation / display ordering |
| icon / color | Icon ID / #RRGGBB |
| power_phase_mode / energy_phase_mode | single or three |
| power_phase / energy_phase | L1, L2, L3 |
| power_unit / energy_unit | W/kW and Wh/kWh |
| invert | Invert source power sign |
| run_power_w | Positive fixed watts with assigned RUN signal, or null |
| grid_mode | signed or directional |
| pv_type | wr, hybrid, mppt |
| hybrid_ac_mode | net or terminals |
| storage_ids / mppt_ids | Assigned complete DC batteries / MPPTs |
| hybrid_id | Optional reverse association metadata; ownership is validated |
| dc_power_unit / dc_invert | Direct inverter DC power unit and sign |
| dc_balance_complete | Explicit complete-DC-bus confirmation for estimated efficiency |
| hybrid_min_power_w | Positive minimum AC/DC power, default 100 W |
| capacity_kwh | Positive fixed total battery capacity |
| charge_sign | negative or positive means charging |
| reserve_soc_pct | Fixed reserve 0–100%, default 0 |
| max_power_w | Positive battery bar scale, default 5000 W |
| fuel_unit | L/h, L, m³/h, m³, kg/h, kg |
| datapoints | Mapping of supported channels to stable measurement references |
| extra | Finite JSON metadata object up to 16 KiB |

Grid/storage types are normalised to neutral configured category custom; generated channels retain internal accounting labels. Grid must be AC/top-level, and at least one active grid remains. RUN requires both signal and positive fixed watts and applies only to ordinary devices. MPPT normalises to DC, direction in and no meaningful phases. A hybrid requires measured AC, linked DC storage and valid non-duplicated assignments. Nodes cannot form cycles.

## Data-point keys

| Key | Reading |
|---|---|
| power_total | Whole-device active power; DC output for MPPT |
| power_l1 / power_l2 / power_l3 | Actual AC phase power |
| energy_total | Cumulative whole-device energy; DC output energy for MPPT |
| energy_l1 / energy_l2 / energy_l3 | Phase cumulative counters |
| energy_import / energy_export | Directional grid cumulative counters |
| frequency | Grid frequency in Hz |
| run | Boolean/nonzero operating signal |
| soc / soc_reserve | SOC / reserve in percent |
| engine_temperature | °C |
| efficiency | Measured generator efficiency in percent |
| fuel_consumption | In configured fuel_unit |
| operating_hours | Hours |
| ac_input | Same inverter's total AC-In in power_unit |
| dc_power | Direct signed converter DC power in dc_power_unit |
| dc_load_power | Other DC bus loads in dc_power_unit |

Empty mappings are ignored. Additional keys can be preserved for extensions but do not automatically gain a calculation. A `point:<id>` reference resolves to acquisition; direct legacy ioBroker IDs remain supported for migration compatibility.

### Grid example

POST `/api/flows` after creating the referenced measurements:

```json
{
  "name": "Grid connection",
  "kind": "grid",
  "grid_mode": "signed",
  "electrical_side": "ac",
  "power_unit": "W",
  "energy_unit": "kWh",
  "datapoints": {
    "power_total": "point:grid-power",
    "energy_import": "point:grid-import-counter",
    "energy_export": "point:grid-export-counter"
  }
}
```

The energy counters are optional; omit unavailable assignments. Signed power follows import positive/export negative unless inverted.

### DC storage example

```json
{
  "name": "Utility room battery",
  "kind": "storage",
  "electrical_side": "dc",
  "capacity_kwh": 10,
  "charge_sign": "negative",
  "reserve_soc_pct": 20,
  "max_power_w": 5000,
  "power_unit": "W",
  "datapoints": {
    "power_total": "point:battery-power",
    "soc": "point:battery-soc",
    "soc_reserve": "point:battery-reserve"
  },
  "extra": {"location": "Utility room", "tags": ["storage"]}
}
```

If no reserve measurement exists, omit soc_reserve and use the fixed setting.

## Additional fields (JSON)

The editor expects **only the contents of extra**, not the entire flow object:

```json
{
  "manufacturer": "Victron",
  "location": "Garage",
  "tags": ["backup", "dc"],
  "maintenance": {"interval_days": 180, "enabled": true},
  "notes": "Complete storage system"
}
```

Use an object with quoted keys and JSON values: strings, finite numbers, booleans, null, arrays and nested objects. Comments, trailing commas, NaN/Infinity and JavaScript functions are invalid. Limit is 16 KiB in JSON representation. These fields are stored/returned as metadata only; they execute no code and do not change calculations. Capacity, signs, mappings and hybrid relationships belong in their regular fields. Old extra.capacity_kwh values must be moved manually to the actual capacity field.

## Consumer groups and reports

Groups have stable id, name (1–80), color (#RRGGBB) and sort_order. group_id applies to individual consumers independently of parent_id. Missing group reference gives 422; deleting a referenced group gives 409.

Live/energy reports include consumer_groups with id, name, color, member_ids, complete and power_w or energy_kwh. Group sums do not affect totals. Site reports include production_w/production_kwh, consumption, grid directional energy, indicators and completeness notes. Historic compatibility fields in_w/out_w and in_kwh/out_kwh now mean production/consumption; machine direction keys and historical channel IDs are unchanged.

## System parameters and versioning

| Parameter | Default / range |
|---|---|
| timezone | Europe/Berlin; valid IANA time zone |
| live_poll_s | 5; 1–300 seconds |
| recorder.enabled | true |
| recorder.interval_s | 15; 5–3600 seconds |
| gap_threshold_min | 15; 1–1440 minutes |
| appearance.zero_threshold_w | 1; 0–100 W, strictly lower magnitude |
| appearance.zero_delay_s | 60; 1–3600 seconds |
| appearance.layout | rounded; square / rounded / flow |
| appearance.background/surface/accent | #RRGGBB colours |

Gap threshold does not give indefinite validity to RUN/residual/storage samples. Derived channels have interval-based validity. Influx settings read suitable existing history; the recorder is not an Influx writing adapter. Schema migrations are additive and repeatable. Newer schemas are rejected by older software; downgrade together with its matching database backup. Application, database schema and CSV versions are independent.
