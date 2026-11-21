# Energieboard 2.2

Selbst gehostetes Energiedashboard für Proxmox-LXC. FastAPI und React, MongoDB für Konfiguration und Aufzeichnung. Messwerterfassung über ioBroker simple-api, MQTT oder Modbus TCP. Kein Demo-Modus und keine vorgefüllten Geräte.

- Verschachtelte AC-Knoten mit anklickbarer Diagrammnavigation und automatischer Restverrechnung.
- Netzanschluss und Speicher als eigene Typen; Generator/BHKW mit optionalen Betriebswerten.
- Persistenter Nullleistungsfilter: unter 1 W nach 60 Sekunden ausblenden, jederzeit wieder einblenden.
- CSV-Import/-Export mit Vorschau und Sicherung; Bearbeitungsformulare direkt unter dem Eintrag.
- Sensorgeräte und RUN-Signale mit fester Leistung und aufgezeichneter kWh-Schätzung.
- WR, Hybrid-WR und separate DC-MPPTs.
- Mehrere Speicher mit Kapazität, gewichtetem Gesamt-SOC, Leistungsbalken, Restenergie und geglätteter Restlaufzeit.
- Drei Darstellungen, globale Farben, über 50 suchbare Symbole und eingebettete Ansicht unter `/flow`.
- Update mit Sicherung, Konfigurationsmigration und Rückfall auf die vorherige Version.

## Dokumentation

- [Docker Compose: Installation, Datenvolume, Backup und Update](DOCKER.md)
- [Installation, Ersteinrichtung und Updates](INSTALLATION.md)
- [CSV-Import, Export und Vorlagen](CSV-IMPORT.md)
- [Messpunkte, Bilanzregeln und JSON-Beispiele](DATENMODELL.md)
- [Prüfbericht und Grenzen der Prüfung](PRUEFBERICHT.md)
- [Änderungen](CHANGELOG.md)

## Docker als zusätzliche Installation

```bash
git clone --branch v2.3.0 https://github.com/Chris87-ux/EnergieDashboard.git
cd EnergieDashboard
docker compose up -d --build --wait --wait-timeout 180
```

Die Konfiguration und Historie liegen im persistenten MongoDB-Volume. Voraussetzungen und Umzug vom LXC stehen in [DOCKER.md](DOCKER.md).

## Voraussetzungen für die direkte LXC-Installation

Unprivilegierter Debian-12-LXC, amd64, systemd, empfohlen 2 vCPU, 4 GB RAM und 32 GB SSD. Lokale MongoDB benötigt AVX und einen kompatiblen Hostkernel. Externe MongoDB ist möglich. Netzwerkzugriff auf die tatsächlichen Datenquellen und während Installation/Updates auf Paketquellen, PyPI und GitHub.

## Erstinstallation von GitHub

Als root im LXC ausführen. Für bestehende Installationen den Updateweg verwenden.

```bash
(
  set -e
  apt-get update
  apt-get install -y ca-certificates curl
  cd /tmp
  basis="https://raw.githubusercontent.com/Chris87-ux/EnergieDashboard/main/outputs"
  curl -fL --retry 3 "$basis/Energieboard-LXC.tar.gz" -o Energieboard-LXC.tar.gz
  curl -fL --retry 3 "$basis/SHA256SUMS" -o SHA256SUMS
  sha256sum -c SHA256SUMS
  mkdir -p /opt
  tar -xzf Energieboard-LXC.tar.gz -C /opt
  bash /opt/energieboard/deploy/install.sh
)
```

Öffnen: `http://<LXC-IP>:8000/datenerfassung`. Zuerst Verbindungen und Messpunkte, anschließend unter Konfiguration den Netzanschluss einrichten.

## Bestehende Installation aktualisieren

Die erste alte Version enthält noch kein Updateskript. Den neuen Updater einmal herunterladen und starten:

```bash
curl -fL --retry 3 https://raw.githubusercontent.com/Chris87-ux/EnergieDashboard/main/deploy/update.sh -o /tmp/energieboard-update.sh
bash /tmp/energieboard-update.sh
```

Danach genügt:

```bash
bash /opt/energieboard/deploy/update.sh
```

Anwendung und Datenbank werden vor der Umstellung gesichert. Zugangsdaten in `/etc/energieboard/energieboard.env`, bestehende Messpunktzuordnungen und Historie bleiben erhalten. Für Sicherungsplatz, Ablauf und Rückkehr zur alten Version siehe Installationsanleitung. Kein gleichzeitiges zweites Update starten.

Das Board hat keine eigene Anmeldung. Im vertrauenswürdigen LAN betreiben oder über einen Reverse-Proxy schützen.
