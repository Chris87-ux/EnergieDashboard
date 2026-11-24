# Battery storage, DC MPPTs and hybrid inverters

[Documentation](README.md) · [Device/node logic](DEVICES-AND-NODES.md) · [Technical reference](DATA-MODEL.md)

## Battery storage

Create type **Battery storage** for each complete storage system, not individual battery modules. Enter its fixed total capacity in kWh, SOC measurement (%), signed power and charge sign. Sign inversion is applied before the selected positive/negative charging convention. Test one charging and one discharging condition.

Choose AC or DC. DC storage has no phase assignment and shows only relevant measurements. AC storage can use total or three-phase power. A storage can be assigned to a node for organisation. DC storage is not directly added to the AC flow balance.

Batteries appear below the main overview with SOC and charge/discharge bars. If more than one is configured, combined SOC is capacity-weighted:

**Combined SOC = Σ(capacity × SOC) / Σ(capacity).**

A 10 kWh system at 40% and 5 kWh at 80% give 53.3%, not 60%. Missing SOC/capacity makes a complete aggregate unavailable; unknown values are not silently zero. Capacities are fixed configured values and do not automatically model degradation or efficiency.

### Reserve, energy and runtime

Optionally assign a SOC reserve data point. Otherwise the fixed reserve setting is used. If an assigned reserve reading is missing/invalid, usable runtime remains unknown rather than silently reverting to the fixed reserve.

Remaining energy is derived from capacity and SOC; usable energy is above reserve. Runtime uses usable energy divided by discharge power smoothed over about five minutes. During charging or very low discharge, no reliable runtime is displayed. This is a simplified estimate without conversion-loss modelling; rapidly changing loads can still alter it. It is not a guaranteed backup duration.

## DC MPPT

Create a PV device with subtype **DC-MPPT**. It has DC output power and optional cumulative total DC energy; no phases, RUN or frequency mapping. Measure the MPPT output to the common DC bus, not panel input before MPPT losses. `power_total` is W/kW; `energy_total` is Wh/kWh. Period energy prefers the counter delta, otherwise recorded power integration.

DC MPPTs are shown separately and count as DC production once. Do not also count hybrid AC conversion output as an independent PV source.

## Hybrid inverter assignment

Create the complete DC storage systems and MPPT devices first. Then create PV → Hybrid inverter and select the associated DC batteries and MPPTs. Each battery/MPPT belongs to at most one hybrid. At least one DC battery is required; AC batteries cannot be assigned as its DC storage. Put the inverter at its actual AC node; DC devices may be linked organisationally without affecting that node's AC residual twice.

### AC boundary: two modes

- **Net inverter power:** total/phase power is already the bidirectional converter net. Positive DC→AC, negative AC→DC.
- **AC-Out minus AC-In:** total/phase power measures AC-Out, and a separate `ac_input` data point measures the same inverter's total AC-In. Net = AC-Out − AC-In. Positive input flows into the inverter; positive output flows out. Use the same AC unit and correct signs; inversion applies to both.

Example: AC-Out 2950 W minus AC-In 2000 W is 950 W conversion output, not 2950 W of PV production. A house grid meter at a different boundary is not a substitute for inverter AC-In. During grid charging, net inverter power must become negative. A single total AC-In cannot provide genuinely measured net power on each phase; calculated symmetry is marked. Historical hybrid input/output channels remain total channels.

### Efficiency

Preferred: assign actual signed **DC power at the inverter**, positive DC→AC and negative AC→DC, with its own unit/inversion. Battery-only power or one MPPT output is not this boundary. A configured direct reading takes priority; if missing, another source is not silently substituted.

Without a direct measurement, explicitly confirm a complete DC bus balance. Estimated converter DC = MPPT outputs + battery discharge − battery charging − other DC loads. Assign other DC loads if present. All DC sources, loads and batteries must be captured at matching boundaries and times. Missing assigned readings leave efficiency unknown.

For DC→AC: efficiency = AC net / DC net × 100. For AC→DC: efficiency = |DC net| / |AC net| × 100. Example: MPPT 2000 W, charging 1000 W, AC output 950 W yields estimated DC input 1000 W and 95%. Grid charging at AC −1000 W and DC −900 W gives 90%.

Minimum power defaults to 100 W on both sides and must be positive. Low power, missing/inconsistent readings, opposite directions or computed efficiency above 100% produce a diagnostic rather than a plausible-looking value. Pure DC PV→battery charging with an idle AC converter has no AC converter efficiency. MPPT and battery efficiency are not included.

## Updates and historic limitations

Existing hybrids remain in net mode. If a previous mapping was actually AC-Out, consciously switch to terminal mode and add AC-In. Existing MPPTs are normalised to DC total-value semantics while IDs/history remain. Fix an incorrectly linked AC battery by removing the hybrid link, changing it to DC, then relinking. Previously recorded incorrect derived energy is not recomputed retrospectively.
