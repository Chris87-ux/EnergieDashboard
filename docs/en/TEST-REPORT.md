# Test report · Energieboard 2.7.0

[Deutsch](../../PRUEFBERICHT.md) · 24 November 2026.

## Backend

**141 backend tests passed**, including all previous regressions. Added coverage includes virtual residual configuration/groups without duplicate accounting, hybrid DC loads, CSV, charts, appliance cycles and four forecast adapters.

Charts cover negative/small values, symmetrical phase estimates, raw units, digital last values, gaps and bounded output. Cycles cover washing pauses, spikes, initially running appliances, boolean edges, restart/gap handling and runtime warnings. Forecast tests cover 23/25-hour DST days, native power/energy units, combined AC clipping, absent data, token headers without secrets in URLs, rate errors and backoff. Learning tests reject future data, require out-of-sample correction evidence, restore raw forecasts when correction loses, and verify correlated-source weighting and cutoff-aware exclusions.

## Real MongoDB and Chromium integration

Passed against an isolated real MongoDB and HTTP/MQTT/Modbus TCP fixtures with 50 devices. Existing energy/phase/grid indicators, nested nodes, storage/hybrids, groups, source staleness, CSV preview/apply/concurrency protection, migration and BSON-compatible full backup/restore remain covered.

Additional MongoDB tests prove idempotent completed counts when retrying after a simulated event/state write interruption. Twelve concurrent forecast reservations permit only eight per token/UTC day, with next-day reset and no plaintext token in usage records. Frozen morning predictions survive later updates; actual counter deltas produce correct daily forecast errors. Provider failures preserve forecasts and apply backoff.

Chromium covers copying points with fresh IDs, residual group assignment, appliance profiles/status, saved measurement/computed charts, forecast configuration, token redaction, CSV and dependency guards in German and English. Existing forms, layouts, language persistence/URL override, user-name preservation, calendars, embeds and desktop/mobile checks remain active without JavaScript errors.

## Deployment and publication

Production TypeScript/Vite build passed. Readiness tests suppress expected connection refusals and reveal genuine final timeouts. Updater tests passed successful replacement, rollback and pre-stop checksum rejection. ShellCheck and Bash syntax passed.

Documentation validation passed: 44 Markdown files, 329 local links/anchors, 18 JSON examples and 70 Bash blocks. Package content, executable modes and SHA-256 passed. The [Linux Docker workflow for 2.7.0](https://github.com/Chris87-ux/EnergieDashboard/actions/runs/45396672363) passed every step: Compose build/start, all 141 tests inside the runtime image, additional real MongoDB tests, health/non-root checks, configuration/chart/forecast-token persistence after container recreation and both Linux deployment harnesses.

## Limits

No live Victron/PV accounts or physical appliances were connected. Adapters are tested against official formats and isolated HTTP responses; account permissions, free-plan limits and service availability require actual commissioning. Improved forecast accuracy over multiple weeks has not been demonstrated with real history and is not guaranteed.

No actual Proxmox LXC boot was performed here. Verify networking, TLS/proxy access, source addresses, register maps, measurement boundaries and signs on your system. Tune appliance thresholds through complete real cycles. Test history checks arithmetic, not meter certification. The wiki Git endpoint remains unavailable; all guides are versioned in the repository and installation archive.
