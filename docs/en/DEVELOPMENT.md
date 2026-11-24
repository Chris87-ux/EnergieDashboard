# Development and verification

[Documentation](README.md) · [Data model](DATA-MODEL.md) · [Test report](TEST-REPORT.md)

## Source layout

- app/backend: Python/FastAPI, MongoDB, acquisition, recorder, topology, balance and API.
- app/frontend: React/TypeScript/Vite interface and translation catalogue.
- deploy: LXC installer/updater, readiness helper, backup and packaging/tests.
- docs and docs/en: German/English operating guides.
- outputs: built LXC archive, checksum and copied installation/test guides.

There is no application demo mode. Test measurements exist only in isolated fixtures. Use a dedicated test database and source servers; integration/backup/restore tests must never target production.

## Build and backend tests

Use a supported Node version from package.json (20.19+ on the 20 line, or 22.12+), Python 3.11+, installed backend requirements and MongoDB for integration. From the repository root:

```bash
npm ci --prefix app/frontend
npm run build --prefix app/frontend
python3 -m venv .venv
.venv/bin/pip install -r app/backend/requirements.txt
PYTHONPATH=app/backend .venv/bin/python -m unittest discover -s app/backend/tests -v
```

The current suite has 103 tests, including six language tests. Some open local sockets. Production build also typechecks TypeScript. App version appears in VERSION, API/backend, frontend package files and deployment examples. Database schema remains 6, CSV 1.

## Integration and browser

`app/backend/tests/integration_modular.py` starts an isolated real MongoDB, API and local HTTP/MQTT/Modbus fixtures. Set MONGOD_BIN to an appropriate mongod binary. BROWSER_TEST activates `browser_modular.cjs`; BROWSER_HOME identifies Playwright-Core/browser files. The current browser executable path is specific to the Windows test environment; adapt it explicitly for another platform.

Checks include 50 devices, configuration import/preview, grouping, recording, migration, full BSON backup/restore, hybrid boundaries, desktop/mobile and both languages. The language tests use the real selector, persistence/URL overrides, forms, calendar, locale numbers, English API labels, unchanged configuration and flow-only embedding.

## Translations

The canonical catalogue is `app/frontend/src/lib/en.json`: German source keys map to English text. Use explicit `t(source, ...values)` calls for interface strings. Numeric placeholders such as {0} must match in both languages; never translate machine IDs or enum values. Avoid concatenating phrases that require different grammar. Interpolated user names stay verbatim.

`lib/i18n.ts` reads a valid lang query first, then the browser preference, defaulting to de. Language switching persists the selection and reloads after confirmation so module-level labels/date formatters use the correct language. Catch blocked localStorage and retain URL-based operation. Date/number locale is separate from the site's time zone.

Backend `lib/i18n.py` uses the same catalogue, localising presentation fields only at the HTTP response boundary. User configuration, names, extra metadata and input values must remain untouched. The Dockerfile copies the canonical catalogue into the backend runtime; the direct LXC uses the packaged frontend source catalogue. Do not introduce a second independently maintained translation file. Language middleware does not rewrite samples or database configuration.

When adding text, update interface, catalogue, English/German documentation and meaningful tests together. Validate placeholder parity, API negotiation, user-data preservation and relevant browser behaviour. JSON/schema/CSV field names remain stable across languages.

## Installer and updater checks

On a suitable development host:

```bash
bash -n deploy/install.sh
bash -n deploy/update.sh
bash -n deploy/wait_ready.sh
shellcheck deploy/install.sh deploy/update.sh deploy/wait_ready.sh
python3 deploy/test_ready.py
python3 deploy/test_update.py
python3 deploy/package.py
```

The harnesses mock service/network commands in isolated directories. On Windows set BASH_BIN to a suitable Git Bash. Run these on the host/CI runner, not inside the read-only/noexec app container. Packaging requires an already built frontend, validates archive contents/permissions and writes SHA256SUMS. Include updated documentation and catalogue.

## Docker verification

On an isolated Linux test host:

```bash
docker compose config --quiet
docker compose build
docker compose up -d --wait --wait-timeout 180
docker compose run --rm --no-deps -v "$PWD/app/backend/tests:/tests:ro" energieboard python -m unittest discover -s /tests -v
```

GitHub CI also checks external Compose syntax, non-root/health, persistence after app recreation and both Linux script harnesses. docker_smoke.py deliberately creates test configuration: never run it against production. A passing CI run does not replace a real target-device/Proxmox commissioning test.

Before tagging a release, check local Markdown links/anchors, JSON examples and Bash syntax, rebuild/package, run source tests and Docker CI, then verify the published archive against its SHA-256. Preserve historical tags.
