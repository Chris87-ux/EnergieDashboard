# Test report — Energieboard 2.6.0

[Documentation](README.md) · [Development](DEVELOPMENT.md) · [Historical German report](../../PRUEFBERICHT.md)

## Scope

The application contains no demo mode. Automated source data comes from isolated test servers and a temporary real MongoDB, not production devices. Language changes preserve configuration and history; schema remains 6 and CSV 1.

## Backend

103 tests passed: 97 existing regressions plus six language tests for language/quality negotiation, placeholder integrity, translated diagnostics, protected user data and metadata, generated labels, and actual HTTP response language/error handling. Existing acquisition, grouping, topology, power/energy, hybrid, storage, counter and CSV tests remain active.

## Browser and integration

TypeScript/Vite production build and integration against real local MongoDB, FastAPI, HTTP API presets, MQTT and Modbus TCP passed. The 50-device fixture checks period energy/indicators, stable IDs, CSV validation/apply, groups, source staleness, recursive node disabling, repeated migration and full backup/restore including BSON values.

Chromium checks German and English navigation, the actual language selector, persistence, explicit URL overrides, unchanged configuration, cancellation with unsaved edits, API forms, English server labels, locale numbers, calendar, embedded flow view and desktop/mobile widths without JavaScript errors. Existing editor/layout/CSV/grid/storage/generator/hybrid checks remain active.

## Deployment and publication

Readiness and updater harnesses cover eventual startup success without transient curl noise, visible final timeout, successful replacement, rollback and checksum rejection. Shell syntax/ShellCheck, Markdown links/anchors, JSON examples, package content and SHA-256 are checked before publication. The Linux Docker workflow is verified before tagging the release; its final run is recorded in the published report.

## Limits

No physical Victron, Home Assistant or evcc production system or actual Proxmox LXC boot was connected during these automated tests. Source credentials, TLS/proxy setup, register maps, hardware compatibility, measurement boundaries and signs require commissioning on the target installation. Synthetic recorded history checks calculations but does not establish metering accuracy. Language does not change machine configuration/API keys; user-entered names can remain German in an English interface by design.
