# CSV configuration import and export

[Documentation](README.md) · [Data acquisition](DATA-ACQUISITION.md) · [Full backups](OPERATIONS.md)

CSV format is **1**, independently of application 2.6.0 and database schema 6. Column names, record types and IDs are identical in both languages and are never translated.

## Export options

Open **Download / upload configuration as CSV** under Data acquisition or Configuration.

- Full configuration CSV: connections, measurements, consumer groups, devices, nodes, batteries, system settings and appearance.
- Measurements CSV: compact measurement columns for editing many topics/registers.
- Connections CSV: connection settings without passwords/tokens.
- Measurement template: headers for new measurements.

History is not exported. CSV is a configuration tool, not a full database backup.

Format: UTF-8 with BOM, semicolon separator, decimal point and no thousands separators. In Excel/LibreOffice explicitly select UTF-8, semicolon and text columns for IDs, topics and register labels. Units go in `unit`, not inside numeric cells. Prevent spreadsheet conversion of IDs to dates/numbers.

## Safe editing workflow

1. Download and keep a full configuration export.
2. Edit a fresh relevant export; keep existing IDs unchanged.
3. Give new entries unique stable IDs, for example `workshop-power`. IDs allow letters, digits, `-`, `_`, `.`, `:`, up to 100 characters. They must be unique within each record type.
4. Save UTF-8 semicolon CSV and select it in the board. Maximum size is 2 MB and 5000 records.
5. Use default **Merge / update by ID**, then Preview import.
6. Inspect new, changed, unchanged and removed entries; fix validation errors.
7. Apply validated import. The server first saves the current configuration to MongoDB `config_backups`; the result identifies the backup.

Each imported row is a complete record, not a patch of only filled cells. Blank optional fields clear assignments or use defaults. Entries absent from a merge remain. Export complex devices before editing rather than constructing a narrow hand-written row that accidentally resets fields.

## Examples

The named connections must already exist or be included as connection rows in the same full configuration. These register addresses are structural examples, not universal Victron mappings:

```csv
record_type;csv_version;id;name;connection_id;unit;unit_id;register;function;datatype;byte_order;word_order;scale;offset;enabled;record;stale_s
measurement;1;victron-ac-power;Victron AC power;victron-gx;W;100;820;3;int16;big;big;1;0;true;true;120
measurement;1;victron-soc;Battery SOC;victron-gx;%;225;266;3;uint16;big;big;0.1;0;true;true;120
```

MQTT JSON measurements:

```csv
record_type;csv_version;id;name;connection_id;address;json_path;unit;scale;offset;enabled;record;stale_s
measurement;1;generator-temp;Engine temperature;mqtt-site;site/chp/readings;engine.temperature;°C;1;0;true;true;120
measurement;1;generator-hours;Operating hours;mqtt-site;site/chp/readings;engine.seconds;h;0.000277777777777778;0;true;true;120
```

For a simple MQTT numeric payload leave `json_path` empty. For standard ioBroker API use the full state ID as `address`; the preset extracts `val`. Home Assistant uses an entity ID; evcc uses its relative state path. Units and conversion formula remain the same in both languages.

## Important columns

| Column | Meaning |
|---|---|
| record_type | connection, measurement, consumer_group, flow or settings |
| csv_version | 1 |
| id | Stable record ID; system settings use app |
| connection_id | Existing/imported connection |
| protocol | api, mqtt or modbus; legacy iobroker is normalised |
| api_preset / api_path / api_json_path | API template, GET path, response base |
| api_response_format / api_auth / api_token_header | Extraction and authentication configuration |
| kind | device, node, grid or storage |
| parent_id | Parent electrical node; empty is top level |
| group_id | Optional additional consumer group |
| category | pv, generator, heatpump, ev, consumer or custom for devices |
| datapoints.power_total | Measurement reference, e.g. point:victron-ac-power |
| datapoints.soc_reserve | Reserve SOC measurement (%) |
| storage_ids / mppt_ids | Assigned IDs, separated by `\|` |
| sort_order | Lower values first; no balance effect |
| extra | JSON metadata object inside one correctly quoted CSV cell |
| appearance.*, recorder.*, influx.* | Flattened system settings |

Use `true`/`false` for booleans and keep machine keys in English. Unknown columns, types, references, duplicate IDs and node cycles are rejected. For all supported fields, start from the current export or inspect the [schemas](DATA-MODEL.md).

Groups use `record_type=consumer_group` with name, colour and sort order. Consumer `group_id` must reference one of these IDs independently of `parent_id`. Missing `group_id` in an updated complete device row clears its optional group. An old merge CSV without group rows does not remove existing groups.

## Full replacement and recovery

Replace entire configuration removes records absent from the file and requires extra confirmation. Use a **full** site export, including groups, settings, connections and mandatory grid. A measurement-only export is unsuitable as a full replacement.

Before applying, the server validates the candidate graph and checks that configuration has not changed since preview. A stale preview must be regenerated. Writes and active readers are synchronised. A write failure attempts to restore the previous configuration; if the database also fails during recovery, the backup remains and the error identifies it. Import backups have no automatic retention policy.

CSV never rewrites measurement history. Source/factor changes apply to future samples; previous readings are not recalculated.

## Secrets and spreadsheet formulas

Passwords, API tokens and InfluxDB secrets are not exported or accepted through CSV. Existing secrets are preserved by matching IDs; new connections need credentials entered in the board. Arbitrary secrets placed in free-text metadata are not automatically detected.

Strings that spreadsheet software could interpret as formulas are prefixed with an apostrophe on export; Energieboard reverses its own escaping during import. Do not rename IDs to work around this protection.

## Hybrid and MPPT fields

Current exports include `hybrid_ac_mode` (net/terminals), `dc_power_unit`, `dc_invert`, `dc_balance_complete`, `hybrid_min_power_w`, and data-point fields `ac_input`, `dc_power`, `dc_load_power`. Hybrids require DC batteries. MPPT uses device/pv/mppt, DC `power_total` and optional `energy_total`, without phases or RUN. Use a fresh full row when editing existing hybrids so missing newer fields do not silently revert to defaults. See [Storage and hybrid](STORAGE-AND-HYBRID.md).
