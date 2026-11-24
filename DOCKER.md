# Erstinstallation mit Docker Compose

[English](docs/en/DOCKER.md)

[Dokumentationsübersicht](docs/README.md) · [Alternative: Proxmox-LXC direkt](INSTALLATION.md) · [Ersteinrichtung](docs/ERSTE-SCHRITTE.md)

Diese Anleitung läuft auf dem **Linux-Docker-Host**, z. B. einer Debian-VM unter Proxmox. Im App-Container werden weder der LXC-Installer noch der LXC-Updater ausgeführt.

## Inhalt

1. [Host und Voraussetzungen](#1-host-und-voraussetzungen)
2. [Docker auf einer neuen Debian-VM installieren](#2-docker-auf-einer-neuen-debian-vm-installieren)
3. [Energieboard herunterladen und starten](#3-energieboard-herunterladen-und-starten)
4. [Zugriff und Datenhaltung](#4-zugriff-und-datenhaltung)
5. [Externe MongoDB](#5-externe-mongodb)
6. [Nächste Schritte](#6-nächste-schritte)

## 1. Host und Voraussetzungen

| Bereich | Voraussetzung |
|---|---|
| Host | Linux amd64 mit Docker Engine und Compose-Plugin; für die mitgelieferten Befehle Debian 12 oder 13 |
| Compose | Aktuelles Plugin mit `docker compose ...`, mindestens 2.20; kein altes `docker-compose` v1 |
| Startgröße | 2 vCPU, 4 GB RAM, 32 GB SSD plus Historie und Sicherungen |
| Datenbank lokal | MongoDB 8.0 mit geeigneter CPU/AVX und kompatiblem Kernel |
| Netzwerk | GitHub, Docker Hub, npm, PyPI und eigene Messquellen erreichbar |
| Rechte | Root oder berechtigter Docker-Administrator auf dem Host |

Für Proxmox eine eigene Linux-VM erstellen, dort das Betriebssystem und Docker installieren. Bei lokaler MongoDB in den VM-CPU-Einstellungen sicherstellen, dass AVX im Gast tatsächlich sichtbar ist; für einen einzelnen kompatiblen Host ist CPU-Typ `host` eine Möglichkeit. Bei Cluster-/Migrationsbetrieb einen geeigneten gemeinsamen CPU-Typ wählen. Prüfung **im Gast**:

```bash
uname -m
grep -w avx /proc/cpuinfo
uname -r
```

Zielarchitektur der bisherigen Prüfungen ist `linux/amd64`. Docker hebt CPU-/Kernelanforderungen der Datenbank nicht auf. Vor Installation die [MongoDB-Plattformhinweise](https://www.mongodb.com/docs/manual/administration/production-notes/) für den konkreten Patchstand prüfen.

Docker in einem Proxmox-LXC benötigt zusätzliche Container-/Nesting-Konfiguration und ist nicht der hier beschriebene Installationsweg. Für diesen Fall stehen die [Proxmox-Dokumentation](https://pve.proxmox.com/pve-docs/chapter-pct.html) und die direkte [LXC-Installation](INSTALLATION.md) als Alternative bereit.

## 2. Docker auf einer neuen Debian-VM installieren

Wenn Docker bereits korrekt läuft, mit Abschnitt 3 fortfahren. Die folgenden Befehle als **root auf einer neuen Debian-VM** ausführen. Bei vorhandenen Docker-/Containerd-Installationen keine Pakete blind ersetzen, sondern die Konflikthinweise der [offiziellen Docker-Anleitung für Debian](https://docs.docker.com/engine/install/debian/) beachten.

```bash
apt-get update
apt-get install -y ca-certificates curl git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
. /etc/os-release
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: $VERSION_CODENAME
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker version
docker compose version
```

Erwartet: Docker-Client und erreichbarer Server sowie eine Compose-Plugin-Version. Die Installation auf einem anderen Hostsystem nach dessen offizieller Docker-Anleitung vornehmen. Zugriff auf den Docker-Daemon verleiht weitreichende Hostrechte; nicht beliebigen Benutzern geben.

## 3. Energieboard herunterladen und starten

**Auf dem Docker-Host**, als root oder Docker-Administrator. Für die Erstinstallation ein noch nicht belegtes Projektverzeichnis verwenden:

```bash
mkdir -p /opt
cd /opt
git clone --branch v2.6.0 https://github.com/Chris87-ux/EnergieDashboard.git energieboard-docker
cd /opt/energieboard-docker
cp docker.env.example .env
```

`.env` vor dem Start bei Bedarf bearbeiten:

```dotenv
ENERGIEBOARD_VERSION=2.6.0
ENERGIEBOARD_PORT=8000
ENERGIEBOARD_BIND=0.0.0.0
```

| Variable | Wirkung |
|---|---|
| `ENERGIEBOARD_VERSION` | Name des **lokal gebauten** Images; lädt allein kein neues Release herunter |
| `ENERGIEBOARD_PORT` | Dashboard-Port auf dem Host, z. B. 8000 oder 8080 |
| `ENERGIEBOARD_BIND` | `0.0.0.0` für Hostschnittstellen, `127.0.0.1` nur für lokalen Zugriff/Proxy |

Dann:

```bash
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
docker compose logs --tail=60 energieboard
curl -fsS http://127.0.0.1:8000/api/
```

Bei geändertem Hostport den `curl`-Befehl anpassen. Der erste Build lädt Pakete und baut die Oberfläche; dies kann mehrere Minuten dauern. `--wait-timeout` betrifft die anschließende Start-/Healthphase. Es gibt derzeit kein bereitgestelltes Projektimage in einer Registry; Compose baut es aus dem geklonten Code.

Erwartet: App und MongoDB laufen, Healthchecks sind erfolgreich, die API zeigt Version `2.6.0`. Im Browser:

```text
http://<DOCKER-HOST-IP>:8000/datenerfassung
```

## 4. Zugriff und Datenhaltung

| Dienst | Aufgabe |
|---|---|
| `energieboard` | Oberfläche, API, Recorder, UID/GID 10001, schreibgeschütztes App-Dateisystem |
| `mongo` | MongoDB 8.0 mit Datenvolume; kein veröffentlichter Datenbankport |

Der feste Compose-Projektname ist `energieboard`, das Standardvolume heißt **`energieboard_mongo_data`**. Konfiguration, Historie und Filterzustände liegen in MongoDB. Neustart und App-Neubau erhalten diese Daten. Eine zweite unabhängige Installation benötigt bewusst getrennte Projektnamen, Volumes und Hostports.

**`docker compose down --volumes` löscht die Datenbank.** Für normale Updates wird dieser Befehl nicht verwendet. Die lokale Compose-Datenbank hat keine eigene Anmeldung und bleibt im privaten Docker-Netz. Keine ungeschützte MongoDB-Portfreigabe ergänzen.

Die Anwendung besitzt keine eigene Anmeldung. Zugriff auf den veröffentlichten Port über Netz-/Hostregeln begrenzen oder einen geschützten Reverse-Proxy verwenden. Docker-Portfreigaben in der tatsächlichen Firewallkonfiguration berücksichtigen; siehe [Docker-Portveröffentlichung](https://docs.docker.com/engine/network/port-publishing/).

### Datenquellen erreichen

- Für ioBroker, MQTT und Modbus die **LAN-IP oder den erreichbaren DNS-Namen** des jeweiligen Servers verwenden.
- `localhost` und `127.0.0.1` bezeichnen im App-Container den App-Container, nicht den Docker-Host.
- `host.docker.internal` wird in der mitgelieferten Compose-Konfiguration auf das Hostgateway abgebildet. Der betreffende Hostdienst muss dort erreichbar sein und darf nicht ausschließlich auf dessen Loopback-Adresse lauschen.
- Der Browser muss nur das Dashboard erreichen; die App selbst muss die Quellen erreichen.

## 5. Externe MongoDB

Statt des lokalen MongoDB-Dienstes lässt sich `compose.external.yaml` verwenden. Das ist eine **alternative Bereitstellung**, kein zusätzlicher Aufruf parallel zur Standarddatei.

Vor dem ersten Start `.env` ergänzen:

```dotenv
MONGO_URL=mongodb://192.168.10.20:27017
DB_NAME=energieboard
```

URI, Anmeldung/`authSource`, Rechte und Datenbanknamen anpassen; bei Sonderzeichen in Kennwörtern die URI-Kodierung beachten. `.env` mit Zugangsdaten nur für Administratoren lesbar halten, z. B. `chmod 600 .env`.

```bash
docker compose -f compose.external.yaml config --quiet
docker compose -f compose.external.yaml up -d --build --wait --wait-timeout 180
docker compose -f compose.external.yaml ps
```

Danach bei **jedem** Betriebs-, Backup- und Updatebefehl dieselbe `-f compose.external.yaml`-Auswahl verwenden. `MONGO_URL`/`DB_NAME` in der normalen `.env` schalten die Standard-Compose-Datei nicht automatisch auf extern um. Vorhandene lokale Daten werden nicht automatisch in die externe Datenbank kopiert; dafür [Backup und Umzug](docs/BETRIEB-UND-UPDATES.md) nutzen.

## 6. Nächste Schritte

1. [Ersteinrichtung](docs/ERSTE-SCHRITTE.md) durchführen.
2. Mindestens einen bekannten Messwert und die Netzrichtung prüfen.
3. [Sicherung einrichten](docs/BETRIEB-UND-UPDATES.md#docker-sicherung).
4. Für ein späteres Update den Abschnitt [Docker-Update](docs/BETRIEB-UND-UPDATES.md#docker-update) verwenden.

[Fehlersuche](docs/FEHLERSUCHE.md) · [Messquellen konfigurieren](docs/DATENERFASSUNG.md) · [Prüfbericht](PRUEFBERICHT.md).
