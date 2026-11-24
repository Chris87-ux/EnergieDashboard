# Release changes

[Documentation](README.md) · [Full historical German changelog](../../CHANGELOG.md)

## 2.6.0 — 24 November 2026

- German/English selector with per-browser persistence and explicit lang URL override, including flow-only embedding.
- English navigation, configuration, device/acquisition/group editors, status messages, chart labels, hints, confirmations and built-in installation guide.
- English number/date/calendar formatting without changing site time zone, configuration IDs or history.
- English built-in API diagnostics and period labels via Accept-Language; user-entered names and custom metadata remain unchanged.
- Complete structured English installation, configuration, maintenance and technical documentation alongside German guides.
- Six additional backend language tests and bilingual browser coverage; database schema remains 6, CSV format 1.

## 2.5.0

Generic configurable HTTP GET acquisition with ioBroker, Home Assistant and evcc presets; Basic/Bearer/custom-header authentication; cross-node consumer groups; quiet startup retries with visible final failures. Existing configuration/history preserved through migration to schema 6.

## 2.4.0

Corrected site production/consumption boundaries, period-based self-sufficiency/self-consumption, combined grid metrics and symmetric three-phase completion.

## 2.3.0

DC MPPT total power/energy, hybrid AC boundary modes, direct/estimated converter DC efficiency and related validation/tests.

## 2.2.0 and earlier

Docker deployment and persistence, combined grid tile, signed-power/zero-filter corrections, CSV configuration, nested nodes, separate storage and local recording. Historical release details and exact older test evidence remain in the [full changelog](../../CHANGELOG.md) and [historical test report](../../PRUEFBERICHT.md).
