# Energieboard 2.6.0

**English** · [Deutsch](README.md) · [Full English documentation](docs/en/README.md)

Self-hosted energy dashboard for production, consumption, grid connection and battery storage. Run it directly in a Proxmox LXC or with Docker Compose. Read real data from configurable HTTP APIs (ioBroker, Home Assistant, evcc or custom), MQTT and Modbus TCP. Configuration and recording use MongoDB. There is no demo mode and the app does not control devices.

## Start here

| Task | Guide |
|---|---|
| New Proxmox installation | [LXC requirements and first install](docs/en/INSTALLATION.md) |
| New Docker installation | [Compose requirements and first install](docs/en/DOCKER.md) |
| Configure the first real readings | [Getting started](docs/en/GETTING-STARTED.md) |
| API, MQTT or Modbus sources | [Data acquisition](docs/en/DATA-ACQUISITION.md) |
| Grid, devices and nested section meters | [Devices and nodes](docs/en/DEVICES-AND-NODES.md) |
| Battery, MPPT and hybrid inverter | [Storage and hybrid](docs/en/STORAGE-AND-HYBRID.md) |
| Sum selected consumers across nodes | [Consumer groups](docs/en/CONSUMER-GROUPS.md) |
| Bulk configuration | [CSV](docs/en/CSV.md) |
| Backup, update or move | [Operations](docs/en/OPERATIONS.md) |
| Errors or implausible balances | [Troubleshooting](docs/en/TROUBLESHOOTING.md) |

## Features

- Permanent combined grid import/export tile with frequency and daily/period energy.
- Nested AC nodes, automatic residual consumption/production and clickable topology navigation.
- Measured devices or RUN signal with fixed estimated power and recorded kWh.
- Generator/CHP telemetry, DC MPPT energy and hybrid converter boundaries/efficiency.
- Separate storage bars, capacity-weighted combined SOC, usable energy and smoothed runtime.
- Optional consumer groups without double counting the site balance.
- CSV preview/apply, stable IDs, credential preservation and configuration backups.
- Three layouts, global colours, extended icons and flow-only embedding.
- Zero-power filtering after continuous readings strictly between −1 and +1 W; grid remains visible.
- Updates that preserve configuration/history and LXC rollback on failure.
- German and English interface, date/number/calendar formatting and English built-in API diagnostics.

## Language and access

Open `http://<SERVER-IP>:8000/?lang=en` or choose English in the header. Language is saved per browser; switching reloads after confirmation. Use `/flow?lang=en` for an English embedded view. IDs, CSV keys, user names, time zone and recorded data do not change.

The app has no built-in login. Use a trusted LAN or an authenticated HTTPS reverse proxy. A suggested starting allocation for 30–50 devices is 2 vCPU, 4 GB RAM and 32 GB SSD plus history/backups. Direct LXC targets Debian 12 amd64; Docker targets Linux amd64. Local MongoDB requires AVX and a compatible kernel. See the installation guides for checks and external-database options.

Application **2.6.0**, database schema **6**, CSV **1**. Use fixed release tags such as v2.6.0. See the [test report](docs/en/TEST-REPORT.md) for validation and limits and [release changes](docs/en/CHANGELOG.md) for history.
