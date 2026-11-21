# Energieboard mit Docker Compose

Energieboard kann weiterhin direkt im Debian-LXC betrieben werden. Docker ist eine zusätzliche Bereitstellungsart. Es werden dieselbe Anwendung und dieselben Konfigurations-/Historienformate verwendet. Der systemd-/APT-Installer wird innerhalb des Docker-Containers nicht ausgeführt.

## Voraussetzungen

- Linux-Host oder Linux-VM mit Docker Engine und Docker Compose Plugin v2.20 oder neuer. Für Proxmox ist eine eigene Linux-VM mit Docker eine mögliche Alternative zum bisherigen LXC.
- Zunächst etwa 2 CPU-Kerne, 4 GB RAM und 32 GB SSD plus Platz für Historie und Sicherungen.
- Für die mitgelieferte lokale MongoDB 8.0: geeigneter amd64-Prozessor mit AVX und kompatibler Hostkernel. Docker beseitigt die MongoDB-CPU-/Kernelanforderungen nicht. Die geprüfte Zielarchitektur ist linux/amd64; andere Architekturen sind nicht Bestandteil der Freigabe.
- Git und ausgehender HTTPS-Zugang zu GitHub, Docker Hub, npm und PyPI für den Image-Build.
- Zugriff des Docker-Hosts auf ioBroker, MQTT-Broker bzw. Modbus-TCP-Geräte. In der Quellkonfiguration deren LAN-Adressen verwenden. `localhost` bezeichnet innerhalb des App-Containers den App-Container selbst. Dienste auf dem Docker-Host sind unter Linux ggf. über `host.docker.internal` erreichbar; dieser Name wird in Compose auf das Hostgateway abgebildet.

Docker anhand der [offiziellen Anleitung](https://docs.docker.com/engine/install/) für das Hostsystem installieren. Versionsprüfung:

```bash
docker version
docker compose version
```

## Erstinstallation

Auf dem Docker-Host:

```bash
git clone --branch v2.2.0 https://github.com/Chris87-ux/EnergieDashboard.git
cd EnergieDashboard
cp docker.env.example .env
docker compose up -d --build --wait --wait-timeout 180
```

Der erste Build lädt die Abhängigkeiten und baut die Oberfläche. Er kann mehrere Minuten dauern. Öffnen:

```text
http://<DOCKER-HOST-IP>:8000/datenerfassung
```

Die eingebettete Übersicht liegt unter `http://<DOCKER-HOST-IP>:8000/flow`.

In `.env` können `ENERGIEBOARD_PORT`, `ENERGIEBOARD_BIND` und `ENERGIEBOARD_VERSION` angepasst werden. Der Standard veröffentlicht Port 8000 auf den Hostschnittstellen. Für einen ausschließlich lokalen Reverse-Proxy beispielsweise `ENERGIEBOARD_BIND=127.0.0.1` verwenden. Der Dienst hat keine eigene Anmeldung; Zugriff auf vertrauenswürdige Geräte begrenzen oder einen Zugriffsschutz vorsehen.

Compose startet zwei Dienste:

| Dienst | Aufgabe |
|---|---|
| `energieboard` | Oberfläche, API und Recorder; läuft ohne Root-Rechte mit UID/GID 10001 |
| `mongo` | MongoDB 8.0, nur im Docker-Netz erreichbar; kein veröffentlichter Datenbankport |

Das App-Dateisystem ist schreibgeschützt. Temporäre Dateien liegen im flüchtigen `/tmp`; Konfiguration, Historie und Filterzustände werden vollständig in MongoDB gespeichert. Compose verwendet den festen Projektnamen `energieboard`. Die Daten liegen im benannten Volume `energieboard_mongo_data` und überstehen Neustart, App-Neubau und Austausch des App-Containers.

Die Datenbank besitzt in dieser einfachen lokalen Compose-Konfiguration keine eigene Anmeldung und ist nicht auf einen Hostport veröffentlicht. Keine zusätzliche Portfreigabe für MongoDB einrichten. Für eine bestehende geschützte Datenbank die externe Variante verwenden.

Der Appstart wartet auf die gesunde Datenbank; anschließend prüft ein eigener Healthcheck die API. Grundlage ist die [Compose-Startreihenfolge mit Healthchecks](https://docs.docker.com/compose/how-tos/startup-order/). Das Image nutzt einen [mehrstufigen Build](https://docs.docker.com/build/building/multi-stage/): Node.js baut die Oberfläche, im Laufzeitimage wird nur Python benötigt.

## Status und Fehlersuche

```bash
docker compose ps
docker compose logs --tail=100 energieboard
docker compose logs --tail=100 mongo
curl -fsS http://127.0.0.1:8000/api/
```

Bei geändertem Hostport den curl-Befehl anpassen. Ein Datenbankfehler hält den Healthcheck auf fehlerhaft; in den Logs stehen Start-/Migrationsfehler. Bei Quellenproblemen außerdem im Board die Messpunktdiagnose prüfen.

## Backup

Für eine konsistente Sicherung die App kurz stoppen; MongoDB bleibt verfügbar. Auf dem Linux-Docker-Host im Projektverzeichnis:

```bash
docker compose stop energieboard
mkdir -p backups
backup_name="$(date -u +%Y%m%dT%H%M%S)"
docker compose run --rm --no-deps --user "$(id -u):$(id -g)" \
  -v "$PWD/backups:/backups" energieboard \
  python /opt/energieboard/deploy/backup.py backup "/backups/$backup_name"
docker compose start energieboard
```

Das Sicherungswerkzeug exportiert die Datenbank einschließlich BSON-Datentypen, Konfiguration, Messhistorie und Indizes. Die neue Sicherungs-Unterstruktur erhält private Verzeichnisrechte. Sie enthält Zugangsdaten; an einem geschützten Ort aufbewahren. Falls die Sicherung fehlschlägt, Fehler beheben und die App bei Bedarf mit `docker compose start energieboard` wieder starten.

## Update ohne Neueinrichtung

Vorher die oben beschriebene Datenbanksicherung erstellen und die bisherige Git-Version notieren:

```bash
git describe --tags --always
git fetch --tags
git checkout v2.2.0
```

Bei einem späteren Release statt `v2.2.0` dessen Tag auswählen. In `.env` `ENERGIEBOARD_VERSION` auf denselben neuen Versionsnamen setzen, damit das gebaute Image eindeutig benannt ist. Danach:

```bash
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
```

Das benannte MongoDB-Volume bleibt erhalten. Die Anwendung führt ihre kompatiblen Migrationen beim Start aus. Für Docker **nicht** `deploy/install.sh` oder `deploy/update.sh` benutzen; diese Skripte sind für die direkte LXC-/systemd-Installation vorgesehen.

`docker compose down` entfernt Container und Netzwerk, erhält aber das Datenvolume. **`docker compose down --volumes` löscht auch die Datenbank** und gehört nicht zum normalen Updateablauf. Den Projektnamen und das Datenvolume beim Update beibehalten. Ein anderer Projektname erzeugt eine separate Datenbank und wirkt dadurch wie eine leere Neueinrichtung.

Docker aktualisiert MongoDB nicht automatisch auf eine neue Hauptversion; die Compose-Datei bleibt zunächst bei MongoDB 8.0. Für ein späteres Hauptversionsupdate die MongoDB-Migrationsvorgaben gesondert beachten.

## Wiederherstellen / Umzug aus dem LXC

Für eine vollständige Übernahme aus dem LXC einschließlich Historie:

1. Dort `energieboard.service` stoppen und mit `deploy/backup.py backup <NEUER-SICHERUNGSPFAD>` eine Sicherung erstellen. Das Werkzeug liest die bisherige Umgebungsdatei.
2. Den gesamten entstandenen Sicherungsordner auf den Docker-Host unter `backups/` übertragen. Die vorhandene LXC-Installation zunächst erhalten.
3. Docker-Anwendung und Datenbank zunächst starten, damit das neue Datenbankziel erreichbar ist; danach nur die App stoppen.
4. Die Sicherung in die eigene neue Energieboard-Datenbank zurückspielen:

```bash
docker compose stop energieboard
docker compose run --rm --no-deps --user 0:0 \
  -v "$PWD/backups/DEINE-SICHERUNG:/backup:ro" energieboard \
  python /opt/energieboard/deploy/backup.py restore /backup
docker compose start energieboard
```

`DEINE-SICHERUNG` durch den tatsächlichen Ordner ersetzen. Der einmalige Restore-Prozess verwendet Root im Container, damit auch eine rootgeschützte LXC-Sicherung lesbar ist; der reguläre App-Dienst läuft weiterhin als UID 10001. Restore ersetzt den Inhalt der konfigurierten Zieldatenbank. Ausschließlich die eigene Energieboard-Datenbank verwenden und Host/DB-Namen vorher prüfen.

Bei einem Rückgang auf eine ältere Anwendung muss ggf. auch die zugehörige ältere Datenbanksicherung wiederhergestellt werden. Alte Anwendung und neuere inkompatible Datenbank nicht kombinieren.

Alternativ kann ausschließlich die Konfiguration über CSV übertragen werden; dabei fehlen Historie und Zugangsdaten neuer Verbindungen. Details in [CSV-IMPORT.md](CSV-IMPORT.md).

## Externe MongoDB

Die Datei `compose.external.yaml` startet ausschließlich die App. Sie ersetzt die normale Compose-Datei und wird separat ausgewählt:

```bash
cp docker.env.example .env
editor .env
docker compose -f compose.external.yaml up -d --build --wait --wait-timeout 180
```

In `.env` `MONGO_URL` und `DB_NAME` auf die vorhandene, vom Container erreichbare Datenbank setzen. Beispiele stehen in `docker.env.example`. Bei Bedarf eine URI mit Authentifizierung und TLS verwenden. Zugangsdaten-Datei schützen. Für Status, Logs und Updates dann ebenfalls immer `-f compose.external.yaml` verwenden. Die MongoDB muss mindestens Version 5.0 unterstützen; keine zusätzliche lokale MongoDB wird gestartet.

## Automatisierter Docker-Test

Der GitHub-Actions-Workflow **Docker build and persistence** baut das Image auf einem Linux-Runner, startet App und MongoDB mit Compose, führt die Backendtests im Laufzeitimage aus und prüft Konfigurationspersistenz nach einem App-Container-Austausch. Außerdem werden der Betrieb ohne Root-Rechte, die gebaute Oberfläche, API und der isolierte Updater-Test unter Linux geprüft. Ergebnis: [GitHub Actions](https://github.com/Chris87-ux/EnergieDashboard/actions/workflows/docker.yml).

Die lokale Entwicklung auf diesem Windows-Rechner benötigt dafür weder Docker Desktop noch WSL. Der Docker-Laufzeittest erfolgt im Linux-CI-System; reale Datenquellen und die Hardware des späteren Hosts müssen zusätzlich vor Ort geprüft werden.
