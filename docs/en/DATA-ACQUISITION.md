# Data acquisition

[Documentation](README.md) · [CSV](CSV.md) · [Data model](DATA-MODEL.md)

## Connection → measurement → device

A connection identifies a server or TCP device. Each measurement describes one value and has a stable ID. A device, node, grid connection or battery assigns these values using `point:<measurement-id>` references. Measurements for one device can come from different connections. Editing a source address with the same ID preserves assignments and history identity; deleting and recreating it creates a new identity.

Create the connection, create one measurement, check diagnostics, then assign it under Configuration. Editing opens the form directly below the selected entry. Search/filter avoids scrolling through long lists.

**Converted value = raw value × scale + offset.** Set the device power/energy unit to the converted measurement unit. A 1500 W source can remain W with factor 1, or become 1.5 kW with factor 0.001. Do not scale once in acquisition and again unintentionally in device units. Supported units include W, kW, Wh, kWh, %, Hz, V, A, bool, °C, h and generator fuel units.

## API / HTTP

Choose **API / HTTP**, then a preset. Enter host/IP without scheme or port; set the port separately. TLS means HTTPS and requires a trusted certificate. A preset is an editable configuration template, not an automatically created connection.

| Preset | Port | GET path | Response base | Format / authentication |
|---|---:|---|---|---|
| Generic API | 80 | `/{address}` | empty | value / none |
| ioBroker | 8087 | `/getBulk/{addresses}` | `val` | iobroker_bulk / none |
| Home Assistant | 8123 | `/api/states/{address}` | `state` | value / bearer |
| evcc | 7070 | `/api/state` | `result` | value / none |

Ports are suggestions; use the actual server or reverse-proxy port.

### Editable request and variables

The request is a relative **HTTP GET path**, never a shell command. `{address}` is replaced by the URL-encoded measurement address. `{addresses}` combines up to 40 addresses for a bulk request. Other variables, arbitrary scripts, host replacement and fragments are unsupported. Use only read-only endpoints; no POST, PUT or device-control requests are sent. Redirects are not followed automatically: configure the final endpoint.

A fixed path such as `/api/state` or `/meter/latest` is valid. Identical URLs are requested only once per acquisition cycle. The response base path is applied first, followed by the measurement JSON path. Dot notation supports objects and zero-based arrays (`channels.0.power`). API paths also support JSON Pointer (`/data/power`), including escaped `/` and `~` keys. Empty paths use the current value itself. JSONPath filters and JavaScript expressions are not supported.

The final value must be numeric, a numeric string or a boolean. `on`/`off` become 1/0. `unknown`, `unavailable`, missing fields and non-finite values remain unavailable. A plain-text numeric response works when both JSON paths are empty.

### ioBroker simple-api

Install/enable the simple-api adapter in your existing ioBroker system and allow the Energieboard server to reach it. Its common port is 8087; do not confuse this with Admin 8081 or Web 8082. Choose the ioBroker preset. Each measurement address is the full data-point ID, for example `alias.0.Energie.Netz.Leistung`; leave measurement JSON path empty for the standard preset.

| Editable GET path | Response format | Base path |
|---|---|---|
| `/getBulk/{addresses}` | ioBroker bulk | `val` |
| `/get/{address}` | value | `val` |
| `/getPlainValue/{address}` | value | empty |

Existing ioBroker connections are automatically converted to protocol `api` with the ioBroker preset, preserving IDs and history. The global ioBroker setting under System exists for legacy direct IDs; create new sources in Data acquisition.

### Home Assistant

1. Make the REST API reachable from the Energieboard server/container.
2. Create a long-lived access token in your Home Assistant profile.
3. Choose the Home Assistant preset, enter host/port, then enter the token under Bearer authentication **without** adding `Bearer ` yourself.
4. Set the measurement address to the entity ID, for example `sensor.grid_power`. The default response base `state` extracts the entity state.
5. Match unit and factor to the actual entity. For a numeric attribute instead of state, clear the response base and set a measurement JSON path such as `attributes.power`, only if that attribute actually exists.

### evcc

Choose the evcc preset and actual host/port. With GET `/api/state` and response base `result`, enter a relative value path in each measurement address: `grid.power`, `pvPower` or `loadpoints.0.chargePower`. Without an explicit measurement JSON path, the address is used as the value path. An explicit JSON path takes priority. Arrays are zero-based, independent of MQTT numbering.

Inspect your instance's state response to confirm available fields, units and sign. Configure Bearer/custom-header authentication when your instance requires it. The no-auth preset is not a promise that your instance is publicly readable. evcc's state structure may change with versions, so request and field paths remain editable.

### Custom API and credentials

For GET `/meter/latest` returning `{"metrics":{"power":850.5}}`, use Generic API, request `/meter/latest`, response base `metrics`, measurement JSON path `power`, unit W. A fixed generic path may have an empty address; a path containing a variable requires an address.

Authentication choices: none, HTTP Basic (username/password), Bearer token, or token in a custom header such as `X-API-Key`. Custom headers receive the token unchanged. Normal API responses and CSV exports omit passwords/tokens. Blank secret fields on edit preserve stored secrets; **Delete saved token** explicitly clears the token. The database and full backups contain credentials, so protect access to them. Do not place secrets in free-text metadata or query strings intended for public exports.

Official references: [ioBroker simple-api](https://github.com/ioBroker/ioBroker.simple-api/blob/master/README.md), [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest/), [evcc REST API](https://docs.evcc.io/integrations/rest-api/), [evcc state reference](https://docs.evcc.io/en/reference/state/).

## MQTT

Provide an existing broker, for example Mosquitto or your ioBroker MQTT adapter. Energieboard does not install a broker. Set host/port (often 1883, TLS 8883), optional username/password, and trusted TLS as appropriate. Each measurement uses an exact topic; wildcards `+` and `#` are not supported.

A numeric payload `850.5` needs an empty JSON path. For payload:

```json
{"data":{"power":850.5,"soc":72,"channels":[100,200]}}
```

Use `data.power`, `data.soc` or `data.channels.1` for the second array element. Multiple measurements may share a topic. MQTT paths support dot notation and numeric array indices, without JSONPath filters or keys containing dots. RUN supports true/false, on/off and 1/0.

Validity (`stale_s`, 5–86400 seconds) starts at reception by Energieboard. Choose a value longer than the normal publishing interval; for publishing every 10 seconds, 30–60 seconds can be a starting point. Expired or disconnected values are unavailable. A publisher sending only on changes needs a heartbeat/regular publication to avoid becoming stale while unchanged.

Subscriptions use QoS 1. Retained messages are marked in diagnostics. Their original measurement age is unknown unless supplied/examined externally; receipt of a retained value does not prove the device is currently online. Device-specific LWT and external payload timestamps are not separately evaluated by this version.

## Modbus TCP

Only network TCP reads are supported, not serial RTU or writes. Enable Modbus TCP on the target device/gateway and obtain its manufacturer's register map.

1. Create connection `modbus`, actual IP/port (often 502) and timeout.
2. Set measurement Unit ID, which may differ from 1, particularly behind gateways.
3. Enter the **zero-based** register address. A manual's `40001` may mean address 0 with FC03, but check the manufacturer's convention rather than always subtracting 40000.
4. Choose FC03 Holding Register or FC04 Input Register, data type, byte order, word order, scale and unit.
5. Verify one known value before importing many registers.

| Type | 16-bit registers |
|---|---:|
| uint16 / int16 | 1 |
| uint32 / int32 / float32 | 2 |
| float64 | 4 |

Use signed types for bidirectional grid or battery power. Huge/unreasonable readings usually indicate address, type, factor or byte/word order errors. Victron addresses depend on device and Unit ID; examples are not universal mappings. Registers are read sequentially per connection, so slow or unresponsive registers can extend a whole acquisition cycle.

## Existing InfluxDB history

Under System, enable reading existing InfluxDB history only when needed. Choose v1 (InfluxQL) or v2 (Flux) and enter the actual URL, commonly port 8086. For v1 set database and any required username/password; for v2 set organisation, bucket and token. The default numeric field is `value`, as commonly used by the ioBroker influxdb adapter, with a measurement name matching the state ID. Use Test connection to check reachability and matching recent history.

The source history must match the configured measurement/history keys. Newly created IDs do not automatically identify arbitrary old Influx measurements. Migrated ioBroker keys are preserved. Suitable Influx history is read first and local MongoDB samples fill available missing intervals; missing data is still marked. Energieboard does not write samples to InfluxDB. Keep the local recorder active for new API/MQTT/Modbus measurements and derived RUN, node and battery channels.

## Recording and scale

Record raw value stores the **normalised** measurement value when the local recorder is enabled. Derived RUN, node residual, grid, hybrid and storage channels are also recorded for energy evaluation. For 30–50 devices, validate one measurement per protocol, plan stable names/IDs, then use [CSV](CSV.md). Changing scale/source affects future samples; existing history is not recalculated.
