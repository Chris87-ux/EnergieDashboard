# Glossary and units

[Documentation](README.md)

| Term | Meaning |
|---|---|
| Power (W / kW) | Current rate of energy transfer; 1000 W = 1 kW |
| Energy (Wh / kWh) | Accumulated energy; 1 kW for one hour = 1 kWh |
| Cumulative counter | Lifetime/running total; period use comes from deltas, not the current total |
| Production | Local generation; excludes grid import and battery discharge |
| Consumption | Useful site/device use; excludes grid export and battery charging in the site balance |
| Grid import / export | Transfer across the site's grid connection |
| Node / section meter | Electrical measurement boundary containing child devices or nodes |
| Residual | Metered section net minus known child net; may be consumption or production |
| Consumer group | Additional cross-node sum of selected normal consumers, without adding another site load |
| RUN | On/off operating signal combined with configured fixed watts to estimate power/energy |
| AC / DC | Alternating-current / direct-current measurement side |
| MPPT | PV controller; this app expects its DC output to the common bus |
| Hybrid inverter | Bidirectional AC/DC converter associated with complete DC batteries and optional MPPTs |
| AC-In / AC-Out | Input/output terminals; pass-through can be present and must not be counted as conversion production |
| SOC | State of charge in percent |
| SOC reserve | Lower charge level reserved from usable runtime calculation |
| Capacity | Fixed configured full battery energy in kWh |
| Weighted SOC | Capacity-weighted mean across complete storage systems |
| Smoothed runtime | Estimate using usable energy and about five minutes of discharge power |
| Self-sufficiency | 1 − grid import / consumption, for the recorded selected period |
| Self-consumption | 1 − grid export / production, as a balance indicator for the period |
| Gap / coverage | Missing observations / fraction of selected time with valid data |
| Counter reset | Counter returning to a lower value; handled separately from normal positive deltas |
| Calculated phase | Symmetric estimate when individual phase measurements are missing |
| Stale | MQTT validity period since reception has expired |
| Retained | Broker-stored MQTT message; reception does not establish its original measurement age |
| Stable ID | Language-independent identifier linking measurements, devices and history |
| Unavailable / N/A | Unknown or unsuitable data; not a measured zero |

Generator units: °C temperature, % measured efficiency, h operating hours, and configured fuel amount/rate (L, L/h, m³, m³/h, kg, kg/h). API timestamps remain ISO-compatible; displayed dates/numbers follow the interface locale, while day boundaries follow the configured IANA site time zone.
