# English documentation

[Project overview](../../README.en.md) · [Deutsch](../README.md)

Application **2.7.1** · database schema **8** · CSV format **1** · 26 November 2026.

## Install

1. [Proxmox LXC: prerequisites and first installation](INSTALLATION.md)
2. [Docker Compose: first installation and external database](DOCKER.md)
3. [Getting started and commissioning](GETTING-STARTED.md)

## Configure

4. [Data acquisition: generic API, ioBroker, Home Assistant, evcc, MQTT and Modbus TCP](DATA-ACQUISITION.md)
5. [Devices, grid connection, nested nodes and residual consumption](DEVICES-AND-NODES.md)
6. [Battery storage, DC MPPTs and hybrid inverters](STORAGE-AND-HYBRID.md)
7. [Consumer groups](CONSUMER-GROUPS.md)
8. [CSV configuration import/export](CSV.md)
9. [Appearance, zero-power filtering and embedding](APPEARANCE.md)

## Operate and extend

10. [Backups, restore, updates and moving installations](OPERATIONS.md)
11. [Troubleshooting](TROUBLESHOOTING.md)
12. [Data model, API and additional JSON](DATA-MODEL.md)
13. [Development and tests](DEVELOPMENT.md)
14. [Glossary and units](GLOSSARY.md)
15. [Release changes](CHANGELOG.md)
16. [Test report and limitations](TEST-REPORT.md)

Start with one known measurement per protocol, verify its unit and sign, then configure the grid connection and add the remaining equipment. For 30–50 devices, use stable IDs and CSV after validating the first entries.

## Language

Choose **Deutsch / English** in the application header. The choice is stored in this browser; changing it reloads the page after confirmation. Save edits first. Other browsers retain their own choice. The default remains German for existing installations. English numbers use a decimal point and English date/calendar labels; site time zone and recorded timestamps do not change.

`?lang=en` and `?lang=de` override the browser preference for a page, including `/flow?lang=en`. Opening an override link does not overwrite the saved preference. The application sends `Accept-Language` for API requests; direct API clients can send `Accept-Language: en`. Configuration keys, CSV columns, API paths, user-entered names, IDs and recorded values are language-independent.

The repository contains both documentation languages. English pages are part of the LXC archive and available with every corresponding release tag. Historical tags retain their original content.

## Forecasts and appliance analysis

- [PV forecasts, sources, evaluation and calibration](PV-FORECASTS.md)
- [Appliance cycles and status](APPLIANCE-CYCLES.md)
- [Custom charts from recorded and calculated values](CHARTS.md)
