# Erstinstallation auf Proxmox als LXC

[Dokumentationsübersicht](../docs/README.md) · [Alternative: Docker](../DOCKER.md) · [Nach der Installation](../docs/ERSTE-SCHRITTE.md)

Diese Anleitung installiert Energieboard **direkt als systemd-Dienst** in einem neuen Debian-LXC. Befehle zur Anwendungsinstallation laufen **im LXC**, nicht auf dem Proxmox-Host. Bestehende Installationen über [Betrieb und Updates](../docs/BETRIEB-UND-UPDATES.md) aktualisieren; kein neues Archiv über die laufende Installation entpacken.

## Inhalt

1. [Voraussetzungen](#1-voraussetzungen)
2. [Container erstellen](#2-container-erstellen)
3. [Netzwerk prüfen](#3-netzwerk-prüfen)
4. [Archiv laden und prüfen](#4-archiv-laden-und-prüfen)
5. [Anwendung installieren](#5-anwendung-installieren)
6. [Start und Zugriff prüfen](#6-start-und-zugriff-prüfen)
7. [Ersteinrichtung und Betrieb](#7-ersteinrichtung-und-betrieb)

## 1. Voraussetzungen

| Bereich | Voraussetzung |
|---|---|
| Gast | Debian **12 Bookworm**, **amd64**, gestartetes systemd |
| Proxmox | Gepflegter Host; LXC nutzt dessen Kernel |
| Container | Unprivilegierter LXC mit Root-Zugriff in der Konsole |
| Startgröße | 2 vCPU, 4 GB RAM, 32 GB SSD plus Historie/Backups |
| Netzwerk | Freie IP, korrekter Router und DNS, Internet und Zugriff auf Datenquellen |
| MongoDB lokal | Geeignete CPU mit AVX, kompatibler Hostkernel; Installer installiert MongoDB 8.0 |
| MongoDB extern | Eigene erreichbare Energieboard-Datenbank, technisch ab MongoDB 5.0; im Betrieb eine gepflegte unterstützte Version einsetzen |

**Debian 13 ist nicht Ziel des direkten Installers.** Auch auf einem neueren Proxmox-Host für diese Installationsart das Debian-12-Template verwenden. Für Docker ist das Gastbetriebssystem des App-Images getrennt vom Docker-Host.

CPU und Kernel im LXC prüfen:

```bash
dpkg --print-architecture
cat /etc/os-release
grep -w avx /proc/cpuinfo
uname -r
```

Ohne AVX keine lokale MongoDB installieren; eine geeignete externe Datenbank nutzen. Docker umgeht diese CPU-Anforderung ebenfalls nicht. MongoDB veröffentlicht versionsabhängige Kernel-Einschränkungen; vor der Installation die [aktuellen Plattformhinweise](https://www.mongodb.com/docs/manual/administration/production-notes/) mit dem Hostkernel und dem konkreten MongoDB-Patchstand vergleichen. Bei Inkompatibilität passenden Host/Kernel oder externe Datenbank wählen.

## 2. Container erstellen

In der **Proxmox-Weboberfläche**:

1. Auf einem Template-fähigen Storage → **CT Templates** → **Templates** das Debian-12-Standardtemplate für amd64 herunterladen.
2. **Create CT**: freie CT-ID, Hostname z. B. `energieboard`, Root-Passwort oder SSH-Schlüssel setzen. **Unprivileged container** aktivieren.
3. Debian-12-Template wählen, Datenträger zunächst mindestens 32 GiB, 2 Kerne und 4096 MiB RAM zuweisen.
4. Netzwerkkarte an die tatsächlich verwendete Bridge, häufig `vmbr0`, anschließen. VLAN nur bei passender Netzwerkkonfiguration setzen.
5. DHCP mit fester Router-Zuweisung oder statische Adresse eintragen. Beispiel für ein tatsächliches /24-LAN: `192.168.10.17/24`, Gateway `192.168.10.1`. **Gateway ist die Router-IP, niemals `255.255.255.0`.** Präfix und Router aus deinem LAN übernehmen.
6. DNS-Server setzen. Container starten → **Console**, als root anmelden.
7. Optional Start beim Booten aktivieren und einen Proxmox-Backupauftrag einrichten.

Docker ist für diesen Weg nicht erforderlich. „Nesting“ hängt auch von der systemd-/Containerkonfiguration ab; bei Namespace-/systemd-Problemen die [Proxmox-Containerdokumentation](https://pve.proxmox.com/pve-docs/chapter-pct.html) und [Fehlersuche](../docs/FEHLERSUCHE.md) prüfen. Nicht zur Umgehung eines Fehlers pauschal auf privilegierten Betrieb wechseln.

## 3. Netzwerk prüfen

**Im LXC:**

```bash
ip -4 addr show
ip -4 route show
getent ahostsv4 deb.debian.org
apt-get update
```

Erwartet: die eigene LAN-Adresse, eine Default-Route über den Router, DNS-Auflösung und abrufbare Paketlisten. Zuerst Netzwerkfehler beheben, dann installieren. Bei IPv6 ohne funktionierende Route einmal IPv4 testen:

```bash
apt-get -o Acquire::ForceIPv4=true update
```

Dies repariert keine fehlende IPv4-Route. Details zu „No route to host“ stehen in der [Fehlersuche](../docs/FEHLERSUCHE.md#netzwerk-und-apt).

Eingehend braucht die Anwendung TCP **8000** aus dem erlaubten LAN. Ausgehend braucht sie DNS und während Installation/Update HTTP/HTTPS zu Paketquellen, GitHub und PyPI. Quellports typischerweise: ioBroker 8087, MQTT 1883/TLS 8883, Modbus TCP 502, InfluxDB 8086; tatsächliche Werte prüfen.

## 4. Archiv laden und prüfen

Für eine **neue** Installation als root im LXC. Verwendet wird der feste Release-Tag `v2.3.0`; Archiv und Prüfsumme stammen so aus demselben Stand.

```bash
(
  set -e
  test ! -e /opt/energieboard || { echo 'Installation besteht bereits: Update-Anleitung verwenden.' >&2; exit 1; }
  apt-get update
  apt-get install -y ca-certificates curl
  download_dir="$(mktemp -d /tmp/energieboard-install.XXXXXXXX)"
  cd "$download_dir"
  release=v2.3.0
  basis="https://raw.githubusercontent.com/Chris87-ux/EnergieDashboard/$release/outputs"
  curl -fL --retry 3 "$basis/Energieboard-LXC.tar.gz" -o Energieboard-LXC.tar.gz
  curl -fL --retry 3 "$basis/SHA256SUMS" -o SHA256SUMS
  sha256sum -c SHA256SUMS
  mkdir -p /opt
  tar -xzf Energieboard-LXC.tar.gz -C /opt
)
```

Erwartet: `Energieboard-LXC.tar.gz: OK` und `/opt/energieboard/deploy/install.sh` vorhanden. Bei Prüfsummenfehler nicht weiterarbeiten, beide Dateien erneut vom selben Tag laden. Erst die folgende Auswahl installiert Dienste.

Alternativ beide Dateien aus `outputs/` desselben Tags auf den Proxmox-Host übertragen. **Auf dem Proxmox-Host**, CT-ID und Dateipfade ersetzen:

```bash
CTID=123
pct push "$CTID" /root/Energieboard-LXC.tar.gz /tmp/Energieboard-LXC.tar.gz
pct push "$CTID" /root/SHA256SUMS /tmp/SHA256SUMS
pct enter "$CTID"
```

Danach **im neuen LXC** Prüfsumme kontrollieren und wie oben nach `/opt` entpacken. Auch bei Dateiübertragung benötigt der Installer Internet für Python-Pakete und ggf. MongoDB.

## 5. Anwendung installieren

### A. Lokale MongoDB

**Im LXC:**

```bash
bash /opt/energieboard/deploy/install.sh
```

Der Installer richtet Python-Umgebung und Abhängigkeiten, MongoDB 8.0 (falls noch nicht vorhanden), Benutzer `energieboard`, Konfiguration und systemd-Dienst ein. Eine neu installierte MongoDB erhält einen Cache von 0,5 GB. Die Oberfläche ist bereits gebaut; Node.js wird im LXC nicht benötigt.

### B. Vorhandene externe MongoDB

Statt A zunächst die geschützte Konfigurationsdatei anlegen:

```bash
install -d -m 0700 /etc/energieboard
install -m 0600 /opt/energieboard/deploy/energieboard.env.example /etc/energieboard/energieboard.env
nano /etc/energieboard/energieboard.env
```

Falls `nano` fehlt, zuerst `apt-get install -y nano`. In der Datei die **eigenen** Verbindungsdaten eintragen, beispielsweise:

```dotenv
MONGO_URL=mongodb://192.168.10.20:27017
DB_NAME=energieboard
```

Bei Anmeldung die passende MongoDB-URI einschließlich `authSource` verwenden; Sonderzeichen in URI-Zugangsdaten korrekt URL-kodieren. Den Benutzer auf diese eigene Datenbank berechtigen: Lesen/Schreiben, Indexverwaltung und für Restore auch Collection-Verwaltung. Niemals eine fremdgenutzte Datenbank als Restore-Ziel verwenden.

Anschließend:

```bash
bash /opt/energieboard/deploy/install.sh --external-mongo
```

Damit wird keine lokale MongoDB installiert. Zugriff, Sicherung und Pflege der externen Datenbank bleiben Teil des eigenen Betriebs.

## 6. Start und Zugriff prüfen

```bash
systemctl status energieboard --no-pager
journalctl -u energieboard -n 60 --no-pager
curl -fsS http://127.0.0.1:8000/api/
hostname -I
```

Erwartet: Dienst `active (running)`, API mit `status: ok` und Version `2.3.0`. Dann im Browser:

```text
http://<LXC-IP>:8000/datenerfassung
```

Die API-Erreichbarkeit bestätigt den Dienststart; sie prüft noch keine realen Geräte. Ein leeres Dashboard bzw. ein Hinweis auf den fehlenden Netzanschluss ist nach Erstinstallation normal.

## 7. Ersteinrichtung und Betrieb

Jetzt [Erste Schritte](../docs/ERSTE-SCHRITTE.md) ausführen. Die Anwendung hat keine eigene Anmeldung; Port 8000 nur aus vertrauenswürdigen Netzen zulassen oder Reverse-Proxy mit Anmeldung verwenden.

| Pfad | Inhalt |
|---|---|
| `/opt/energieboard` | Anwendung und Python-Umgebung |
| `/etc/energieboard/energieboard.env` | MongoDB-Verbindung und Datenbankname, nur root |
| `/etc/systemd/system/energieboard.service` | systemd-Dienst |
| `/var/lib/mongodb` | Standarddatenpfad lokaler MongoDB; eigene Konfiguration kann abweichen |
| `/var/backups/energieboard` | Sicherungen des LXC-Updaters |

Weiter: [Backup und Updates](../docs/BETRIEB-UND-UPDATES.md) · [Fehlersuche](../docs/FEHLERSUCHE.md) · [Prüfgrenzen](../PRUEFBERICHT.md).
