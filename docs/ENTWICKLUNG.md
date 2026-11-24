# Entwicklung und Prüfungen

[English](en/DEVELOPMENT.md)

[Dokumentationsübersicht](README.md) · [Datenmodell](../DATENMODELL.md) · [Prüfbericht](../PRUEFBERICHT.md)

## Aufbau

| Pfad | Inhalt |
|---|---|
| `app/backend` | FastAPI, Modelle, Datenerfassung, Live-/Historienbilanz |
| `app/frontend` | React/TypeScript mit Vite |
| `app/backend/tests` | Unit-, Integrations- und Browserprüfungen |
| `deploy` | LXC-Installer/Updater, Backup, Paketbau und Docker-Smoke-Test |
| `.github/workflows/docker.yml` | Linux-Dockerprüfung |
| `docs` | Benutzeranleitungen |
| `outputs` | Geprüftes LXC-Paket, Prüfsumme und kopierte Hauptanleitungen |

Anwendungsversion: `VERSION`, Backend/API und Frontend-Paketversion. Datenbankschema 6 und CSV-Version 1 sind getrennte Versionsangaben. Eine reine Dokumentationsänderung erfordert keine Datenbankmigration.

## Lokal vorbereiten

Python **3.11** und Node.js **ab 22.12** verwenden. Isolierte Entwicklungsdatenbank benutzen, nicht die produktive Energieboard-Datenbank. Aus dem Projektverzeichnis unter Linux/Bash:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r app/backend/requirements.txt
npm ci --prefix app/frontend
npm run build --prefix app/frontend
```

Der Build führt TypeScript-Prüfung und Produktionsbuild aus. Die Dockerdatei baut Oberfläche und Python-Laufzeit in getrennten Stufen. Die normale LXC-Installation verwendet bereits gebaute Assets aus dem Archiv.

## Backendtests

```bash
PYTHONPATH=app/backend .venv/bin/python -m unittest discover -s app/backend/tests -v
```

Stand 2.6.0: 103 Tests. Einige Tests öffnen lokale Test-Sockets. Testdaten und Protokollfixtures sind ausschließlich Testcode; die ausgelieferte Anwendung hat keinen Demo-Modus.

## Integration mit echter MongoDB

Passende lokale `mongod`-Datei bereitstellen und aus dem Projektverzeichnis starten:

```bash
MONGOD_BIN=/usr/bin/mongod .venv/bin/python app/backend/tests/integration_modular.py
```

Die Prüfung startet eine eigene temporäre MongoDB und HTTP-/MQTT-/Modbus-Fixtures, prüft API, 50 Geräte, CSV, Migration und Backup/Restore und beendet die Testdienste anschließend. Zusätzlich zum Backend muss die gebaute Oberfläche vorhanden sein, wenn Browserprüfungen laufen sollen.

## Browserprüfung

`app/backend/tests/browser_modular.cjs` verwendet Playwright-Core und einen separat bereitgestellten Chromium. `BROWSER_TEST` aktiviert die Prüfung im Integrationslauf, `BROWSER_HOME` zeigt auf dessen Bibliotheken und Browserdateien. Der aktuelle Browserpfad im Skript ist auf die verwendete Windows-Testumgebung ausgelegt; unter Linux den Chromium-Pfad passend anpassen. Keine pauschale plattformübergreifende Browser-Startanweisung annehmen.

Geprüft werden u. a. Inline-Formulare, CSV, Netz/Speichertypen, DC-MPPT ohne Phasen, Hybridfelder/-anzeige, drei Layouts, mobile Überläufe und JavaScript-Fehler.

## LXC-Skripte und Paket

```bash
bash -n deploy/install.sh
bash -n deploy/update.sh
bash -n deploy/wait_ready.sh
shellcheck deploy/install.sh deploy/update.sh deploy/wait_ready.sh
python3 deploy/test_update.py
python3 deploy/test_ready.py
python3 deploy/package.py
```

`test_update.py` benötigt Bash und simuliert Hostbefehle in einer isolierten Umgebung. Es prüft Austausch, Rückfall und falsche Prüfsumme. `test_ready.py` simuliert anfängliche Nichterreichbarkeit mit späterem Erfolg sowie dauerhafte Startfehler. Auf Windows muss `BASH_BIN` auf eine passende Git-Bash zeigen. **Nicht im schreibgeschützten/noexec App-Container ausführen**; Linux-CI führt es auf dem Runner aus.

`package.py` benötigt die gebaute Oberfläche. Es erzeugt `outputs/Energieboard-LXC.tar.gz`, prüft Inhalt, relative Pfade und Rechte und schreibt `outputs/SHA256SUMS`. Nach Dokumentationsänderungen mit Paketbezug auch die ausgelieferten Anleitungen konsistent halten.

## Dockerprüfung

Auf einem isolierten Linux-Testhost:

```bash
docker compose config --quiet
docker compose build
docker compose up -d --wait --wait-timeout 180
docker compose run --rm --no-deps -v "$PWD/app/backend/tests:/tests:ro" energieboard python -m unittest discover -s /tests -v
```

Der GitHub-Workflow prüft zusätzlich externe Compose-Konfiguration, Healthcheck/Non-Root, Persistenz nach App-Neuerstellung und den Linux-Updater-Harness. `docker_smoke.py` erzeugt absichtlich Testkonfiguration; nur auf einer frischen isolierten Testdatenbank anwenden. Ein Docker-CI-Erfolg bestätigt keinen Test an realen Victron-Geräten oder einen vollständigen Proxmox-LXC-Boot.

## Dokumentation pflegen

Benutzeranleitungen im Repository bearbeiten, Links/Beispiele prüfen und entsprechende Wiki-Seiten aus denselben Inhalten aktualisieren. Bei neuen Einstellungen Modell, Editor, CSV, Migration, Tests und Anleitung gemeinsam betrachten. Kennwörter oder echte Konfigurationsbackups nicht öffentlich committen. Historische Release-Tags unverändert lassen; neuere Dokumentation liegt auf `main`.

## Übersetzungen

Der gemeinsame Katalog liegt in `app/frontend/src/lib/en.json`. Oberfläche: explizite `t(Quelle, ...Werte)`-Aufrufe; API: `lib/i18n.py` lokalisiert ausschließlich Ausgabemeldungen anhand von Accept-Language. Docker kopiert denselben Katalog ins Backend-Image, im LXC wird die mitgelieferte Frontend-Quelldatei gelesen. Keine zweite unabhängig gepflegte Übersetzung anlegen. Platzhalter müssen in beiden Sprachen übereinstimmen; Namen, IDs, Konfigurationsschlüssel, extra-Metadaten und Eingabewerte dürfen nicht übersetzt werden. Browserpräferenz und URL-Override verändern weder Datenbank noch Zeitzone. Englische Dokumentation unter docs/en gemeinsam aktualisieren.
