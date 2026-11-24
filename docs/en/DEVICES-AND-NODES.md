# Devices, grid connection and nodes

[Documentation](README.md) · [Data acquisition](DATA-ACQUISITION.md) · [Storage/hybrid](STORAGE-AND-HYBRID.md)

## Types and categories

Configuration type identifies **Device / producer**, **Grid connection**, **Node / section meter**, or **Battery storage**. Grid and storage are types, not selectable device categories. Categories describe ordinary devices, for example PV, generator/CHP, heat pump, electric mobility, consumer or custom. Choose an icon and colour independently.

Display order sorts smaller numbers first and does not change the calculation. An enabled flow participates in the active view and balance. Disabling a node disables its entire subtree for evaluation without deleting configuration or history.

## Mandatory grid connection

Create the grid at top level on AC. Use one signed power value (normally positive import, negative export) or supported separate import/export entries. Apply sign inversion if the source uses the opposite convention. Do not create contradictory combinations of signed and separate grid measurements. At least one active grid connection must remain; the last one cannot be removed/disabled.

The permanent top-centre grid tile combines import and export, frequency, and today's or selected-period import/export energy. Assign frequency only at the actual transfer point. Separate cumulative directional energy counters are preferred; otherwise recorded directional power is integrated. Import and export are transfers, not local production/household consumption by themselves.

## Ordinary measured devices

Assign total power or phase power, optional cumulative energy, and the matching units. A consumer uses the magnitude as consumption; a producer uses the magnitude as production. The displayed signed source value is retained, including negative generator values. Inverting the sign changes the displayed reading, not the ordinary device's configured role. Use grid or hybrid types for real bidirectional behaviour.

For three-phase configuration, a total value covers the **entire device**. Total 900 W with no phase sensors means 300 W per phase. One measured phase at 300 W without a total is symmetrically extrapolated to 900 W. Actual phase readings take priority; missing phases share the remaining total and are marked calculated. Energy follows the same principle. Do not enter whole-device power as if it were each individual phase.

## RUN-only devices

Assign RUN plus fixed running watts. true/non-zero means running; false/0 means off. Live power is the fixed wattage while active. Recorded state intervals become estimated energy, with limited validity so missing observations do not imply indefinite operation. A fixed wattage is an estimate, not a calibrated energy meter. Past runtime before recording started cannot be recovered.

## Generator / CHP

Choose category Generator / CHP for the generator icon and optional engine temperature (°C), efficiency (%), fuel consumption (L/h, L, m³/h, m³, kg/h or kg) and operating hours (h). These readings are displayed without an automatic fuel/efficiency calculation. Convert seconds to hours at the measurement using scale 1/3600 when necessary. Additional telemetry does not alter the power balance.

## Nodes and automatic residuals

A node represents an electrical section and may contain consumers, producers, storage or further nodes. Select the parent through Connection; the top level is upstream of section meters. Cycles and missing parents are rejected.

With a node meter, positive net power means section consumption and negative means production. Automatic residual consumption/production channels reconcile the meter with known children. For a net section reading of +1000 W, a known consumer at 300 W and producer at 100 W leave 800 W residual consumption: 1000 − (300 − 100). With a 200 W RUN load as another child, the residual becomes 600 W. Children are not added again on top of the section meter in the site balance.

Nested nodes account for their whole subtree at the correct boundary. A node without a meter cannot independently establish an unknown residual. The overview uses visually distinct rectangular nodes; clicking opens their children and shows a breadcrumb path. Select one/three phases to inspect meter, child net sum and residual per phase.

AC batteries affect the AC section residual according to charge/discharge direction. DC batteries and MPPTs may be organisationally assigned to a node but remain outside its AC subtraction; their AC contribution passes through the hybrid inverter.

## Site balance and indicators

Production includes configured local AC producers, residual production and measured DC production. Grid import and battery discharge are excluded. For a hybrid with assigned MPPTs, MPPT production is counted once; inverter AC output is not added as another PV source. Without MPPTs, a marked estimate uses AC/battery balance and excludes unmeasured conversion losses.

AC consumption uses grid import − export + ordinary AC production + hybrid AC output − hybrid AC input + AC battery discharge − AC battery charging. Unassigned consumption is the difference from individually captured consumer loads. DC production and AC useful consumption have different measurement boundaries and are not interchangeable loss-adjusted totals.

Self-sufficiency and self-consumption in the overview use **recorded Today**, not instantaneous power. The energy balance uses its selected period. Self-sufficiency = (1 − grid import / consumption) × 100; balance-based self-consumption = (1 − grid export / production) × 100, limited to 0–100%. Measured zero yields 0%; missing required data remains unknown. Grid charging/battery export means these are balance indicators, not energy-origin tracking.

## Grouping, removal and checks

An optional [consumer group](CONSUMER-GROUPS.md) adds a cross-node summary without moving the electrical connection. Before deleting a node, move its devices, batteries and child nodes. Removing a configuration entry does not reconstruct or erase previously recorded energy automatically. Confirm signs and boundaries with known loads and check residuals before expanding the installation.

## Configure automatic residual consumers (2.7)

A metered node exposes a virtual residual consumer in Configuration. Its editor contains name, group, icon, colour and display order only; no independent data points. Values remain the node meter minus children. Negative residuals retain the separate residual-production channel; consumer groups include only the consumption share.

The stable virtual ID is `<node-id>:rest_consumption`; metadata is stored on the node in `residual`. Do not create or import a separate `kind=residual` record. Remove dependent chart references before removing the node meter.
