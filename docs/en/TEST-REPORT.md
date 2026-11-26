# Test report · Energieboard 2.7.1

[Deutsch](../../PRUEFBERICHT.md) · 26 November 2026.

**152 backend tests passed**, production build passed, complete real-MongoDB/API/HTTP/MQTT/Modbus TCP integration passed with 50 devices. Chromium covers German/English, desktop/mobile, configuration, charts, cycles and forecasts without JavaScript errors. Fixtures exist only in test processes; the application has no demo mode.

## Added regression coverage

- Hourly VRM Wh converted to kWh: 38,894.84 Wh becomes 38.89484 kWh, excluding unrelated consumption/battery series.
- Default 25/25/50 dependency weights, equal sources, independent sources, custom groups, manual relative weights including zero, renormalisation for missing sources and configurable automatic caps.
- Weight preferences retain physical revisions; the corrected VRM parser starts fresh training.
- Old snapshots, daily blends and error values repaired exactly once with original calculation audit. Actual measurements, frozen weights and manual exclusions persist. Unknown providers are not guessed.
- Real MongoDB confirms repeated migration, parser revision/schema 8 and byte-equivalent physical recorder observations before/after repair.
- Browser forms save all weighting modes, cap, grouping toggle, relative weights and custom groups. A dedicated AC PV system saves without storage or manual side correction. CSV preview, dependency guards and token redaction remain valid.

## Existing coverage retained

Signed/tiny power, grid and energy balance, symmetrical phases, nested nodes, residual consumers/groups without duplicate accounting, batteries/hybrids/DC loads, independent point recording, bounded charts with units/gaps, durable appliance counts and status, forecast quotas, no-lookahead learning, correction validation and audited exclusions remain covered.

The full integration retains stable IDs, source expiry, recursive disable, CSV conflict protection, repeated migration and BSON-compatible full backup/restore. Simulated cycle write interruptions do not double-count. Late weather updates cannot replace morning predictions; the audited technical unit repair is an explicit exception.

## Deployment

Readiness and updater rollback passed. Documentation validation passed for 44 Markdown files, 329 local links/anchors, 18 JSON examples and 70 Bash blocks. Package contents, executable modes and SHA-256 passed. The [Linux Docker workflow for 2.7.1](https://github.com/Chris87-ux/EnergieDashboard/actions/runs/45820902586) passed completely: Compose build/start, all 152 tests inside the runtime image, real MongoDB regression tests including VRM repair, health/non-root checks, persistence after container recreation and both Linux deployment harnesses.

## Limits

No access to your production database or live VRM/Solcast accounts. Repair runs on your server after upgrading. Cloud adapters use official formats and isolated HTTP responses; validate account rights and real source values during commissioning. No actual Proxmox LXC boot or physical metering was performed here. Actual PV measurement boundaries and units must match the forecast installation. Configurable weighting does not guarantee better weather predictions every day.
