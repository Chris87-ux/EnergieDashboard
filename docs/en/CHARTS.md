# Custom charts

[Documentation](README.md) · [Deutsch](../CHARTS.md)

Use **Charts** (`/charts`) to save views with up to eight series each. Configuration persists in MongoDB through updates and Docker container recreation when the database volume is retained.

## Create a chart

1. Configure and record the required measurements under **Data acquisition**, then enable the recorder under System. From 2.7, recorded measurements are saved even when not yet assigned to a device.
2. Choose **Add chart**, enter a name and select a source. Source names are used automatically; custom labels are optional.
3. Add series and colours, at most eight different sources per chart.
4. Save and choose the time range. Today refreshes about once a minute; Refresh reloads visible data. A query covers at most 400 days.
5. Toggle legend items to hide/show series. Inspect values using the mouse or timestamp slider.

## Sources

- **Measurement:** the captured value after acquisition scaling/transformation, in the measurement's unit. A kW measurement remains kW.
- **Power:** calculated whole-device or node power in W, including symmetrical missing-phase estimates. Negative and small values are preserved.
- **Node residual:** the existing recorded residual consumption channel, without duplicate energy accounting.
- **SOC / charging / discharging:** mapped SOC and separate derived power channels. Net storage power is charging minus discharging.
- **Device status / cycles:** recorded detection state and cumulative completed cycle count; see [Appliance cycles](APPLIANCE-CYCLES.md).

RUN estimates, node residuals and storage channels exist only after recording begins. Available source options do not imply existing history. Missing data stays missing. Remove a source from charts before deleting its device or measurement; disabling it preserves past history.

## Display and accuracy

Different units use separate axes, at most two per panel. Further units create additional panels. Equal units share a scale. Boolean, status and cycle-count series use steps; other series use lines with gaps. See the cycle guide for numeric status codes.

Queries return up to approximately 480 windows per series, never shorter than one recorder interval. Continuous values use window means; digital values use the last observation. This is a visualisation, **not an alternative kWh calculation**. Use the energy balance for counter deltas and time integration.

Missing windows are never filled with zero or connected across gaps. Zoom to a shorter range to inspect individual events. Status and RUN estimates are not reconstructed before their recording start.

## Backups and CSV

The full CSV export includes `record_type=chart`, `name`, `sort_order` and a JSON list in the `series` column. Example cell content (the exporter handles CSV quoting):

```json
[{"kind":"measurement","reference_id":"meter-power","label":"","color":"#38BDF8","unit":"W"},{"kind":"power","reference_id":"workshop:rest_consumption","label":"Workshop residual","color":"#F59E0B","unit":"W"}]
```

IDs must exist in the destination configuration. Import validates sources and derives units from them. CSV transfers configuration, not measurement history; use the full database backup for a migration.

API: `GET /api/chart-sources`, `GET /api/charts`, `PUT /api/charts/{id}`, `DELETE /api/charts/{id}`, `GET /api/charts/{id}/data?start=2026-11-24T00:00:00%2B01:00&end=2026-11-25T00:00:00%2B01:00`. Prefer timestamps containing a timezone.
