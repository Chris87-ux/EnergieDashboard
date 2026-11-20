# Energieboard · Installation und Betrieb im Proxmox-LXC

## 1. Voraussetzungen

| Bereich | Voraussetzung |
|---|---|
| Container | Debian 12 Bookworm, amd64, systemd, unprivilegiert |
| Ressourcen | Empfohlen 2 vCPU, 4 GB RAM, 32 GB SSD für zunächst 30–50 Geräte |
| MongoDB lokal | AVX-Unterstützung des Hostprozessors, kompatibler Linux-Kernel |
| MongoDB extern | MongoDB ab 5.0, erreichbar vom LXC; eigene Datenbank für Energieboard |
| Installation | Root-Zugriff in der LXC-Konsole, funktionierende Uhrzeit, DNS und Internet |
| Browser | Aktueller Browser auf einem Gerät im LAN |

Der Container teilt sich den Kernel mit Proxmox. CPU-/Kernelvoraussetzungen betreffen deshalb auch den Host. Vor der Installation `grep -w avx /proc/cpuinfo` und `uname -r` prüfen. Der Installer richtet bei lokaler Installation MongoDB 8.0 ein. Die CPU muss dessen Plattformanforderungen erfüllen. MongoDB weist in seinen Plattformhinweisen auf Einschränkungen bestimmter neuer Kernel hin; die zum Hostkernel passenden Hinweise prüfen. Bei ungeeigneter CPU oder ungeeignetem Kernel eine externe MongoDB verwenden.

Referenzen: [MongoDB-Plattformanforderungen](https://www.mongodb.com/docs/manual/administration/production-notes/), [MongoDB auf Debian](https://www.mongodb.com/docs/v8.0/tutorial/install-mongodb-on-debian/), [Proxmox-Container](https://pve.proxmox.com/pve-docs/pct.1.html).

Die Anwendung enthält keine Demodaten. Für sinnvolle Anzeigen müssen reale Messpunkte und ein Netzanschluss eingerichtet sein. Ein funktionsfähiger MQTT-Broker oder ein Modbus-TCP-Gerät wird bei Bedarf vorausgesetzt; beides wird nicht vom Installer eingerichtet. Modbus arbeitet ausschließlich lesend über das Netzwerk.

## 2. LXC in Proxmox anlegen

1. Debian-12-Standardtemplate für amd64 herunterladen.
2. Container erstellen, unprivilegiert aktivieren und einen Hostnamen vergeben, z. B. `Energieboard`.
3. 2 CPU-Kerne, 4096 MiB RAM und zunächst 32 GiB SSD zuweisen. Backups und Messhistorie brauchen zusätzlichen Platz.
4. Netzwerkschnittstelle an die passende Bridge hängen, üblicherweise `vmbr0`. VLAN nur eintragen, wenn das LAN dies benötigt.
5. Eine freie IPv4-Adresse mit korrektem Präfix und als Gateway die LAN-IP des Routers eintragen. Beispiel für ein /24-LAN: `192.168.10.17/24`, Gateway etwa `192.168.10.1`, sofern dies tatsächlich der Router ist. Eine Subnetzmaske gehört nicht ins Gateway-Feld.
6. Passenden DNS-Server eintragen, Container starten, Konsole öffnen und als root anmelden.
7. Optional in den Proxmox-Containeroptionen den Start beim Booten des Hosts aktivieren.

Keine Docker-/Nesting-Freigabe erforderlich. Energieboard wird als eigener systemd-Dienst installiert.

## 3. Netzwerk prüfen

In der LXC-Konsole:

```bash
ip -4 addr show
ip -4 route show
getent ahostsv4 deb.debian.org
apt-get update
```

Die Standardroute muss auf den tatsächlichen Router zeigen. Bei fehlendem IPv6-Routing kann APT über IPv4 getestet werden:

```bash
apt-get -o Acquire::ForceIPv4=true update
```

Nur wenn IPv4 funktioniert und APT dauerhaft IPv4 nutzen soll:

```bash
printf 'Acquire::ForceIPv4 "true";\n' > /etc/apt/apt.conf.d/99force-ipv4
```

Ausgehend erforderlich: DNS, HTTP/HTTPS für Debian, MongoDB, PyPI und GitHub; Zugriff auf die eigenen Quellen. Übliche Quellports sind ioBroker 8087, MQTT 1883 bzw. TLS 8883, Modbus TCP 502 und optional InfluxDB 8086. Eingehend benötigt das Dashboard TCP 8000 aus dem eigenen LAN. Tatsächliche Ports können abweichen.

## 4. Erstinstallation direkt von GitHub

Diesen Block als root **im LXC** ausführen, wenn dort noch keine Energieboard-Installation besteht:

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

Bei einer Prüfsummenabweichung nicht entpacken; Archiv und Prüfsumme erneut herunterladen. Ein zeitgleich veröffentlichtes Update kann bei diesem Erstinstallationsdownload unterschiedliche Stände liefern. Der Updater bindet beide Dateien an denselben Commit.

Der Installer installiert Python mit virtueller Umgebung und die festgelegten Abhängigkeiten. Bei lokaler Installation richtet er MongoDB ein, erstellt den Dienstbenutzer `energieboard`, prüft die gebaute Oberfläche und Datenbank und startet den Dienst. Bei neu installierter MongoDB begrenzt er den WiredTiger-Cache auf 0,5 GB. Eine vorhandene MongoDB-Konfiguration wird nicht durch eine neue Cacheeinstellung ersetzt.

Die Oberfläche ist im Archiv bereits gebaut. Node.js ist im LXC für Installation und Updates nicht erforderlich.

### Alternative Dateiübertragung

Archiv und SHA256SUMS von GitHub auf den eigenen PC herunterladen und per SCP in den LXC kopieren. Falls der LXC keinen SSH-Zugang bietet, zuerst auf den Proxmox-Host kopieren und in dessen Shell:

```bash
CTID=123
pct push "$CTID" /root/Energieboard-LXC.tar.gz /tmp/Energieboard-LXC.tar.gz
pct push "$CTID" /root/SHA256SUMS /tmp/SHA256SUMS
pct enter "$CTID"
cd /tmp
sha256sum -c SHA256SUMS
mkdir -p /opt
tar -xzf Energieboard-LXC.tar.gz -C /opt
bash /opt/energieboard/deploy/install.sh
```

`123` durch die tatsächliche Container-ID ersetzen.

### Externe MongoDB

Archiv wie oben prüfen und entpacken. Vor dem Installer:

```bash
install -d -m 0700 /etc/energieboard
install -m 0600 /opt/energieboard/deploy/energieboard.env.example /etc/energieboard/energieboard.env
editor /etc/energieboard/energieboard.env
bash /opt/energieboard/deploy/install.sh --external-mongo
```

In der Datei `MONGO_URL` auf die erreichbare MongoDB setzen und `DB_NAME=energieboard` oder einen eigenen, ausschließlich für Energieboard verwendeten Datenbanknamen festlegen. Bei bestehender Installation dieselbe Datenbank weiterverwenden. Der Datenbankbenutzer benötigt Lesen, Schreiben, Indexverwaltung sowie für Sicherung/Wiederherstellung die entsprechenden Rechte in dieser Datenbank.

## 5. Dienst und Browserzugriff

```bash
systemctl status energieboard --no-pager
journalctl -u energieboard -n 60 --no-pager
curl -fsS http://127.0.0.1:8000/api/
hostname -I
```

Im Browser `http://<LXC-IP>:8000/datenerfassung` öffnen, beispielsweise `http://192.168.10.17:8000/datenerfassung`. Der Dienst startet beim Containerstart. Ein Neustart des gesamten Proxmox-Hosts ist nach der Installation nicht erforderlich.

Die API und die Oberfläche haben keine eigene Anmeldung. Zugriff auf vertrauenswürdige LAN-Geräte beschränken oder einen Reverse-Proxy mit Anmeldung verwenden. Passwörter und Tokens werden in der Datenbank bzw. Umgebungsdatei gespeichert. Sicherungen nur für Administratoren zugänglich aufbewahren.

## 6. Ersteinrichtung

### Verbindungen und Messpunkte

1. Reiter **Datenerfassung**, Verbindung hinzufügen, Protokoll und tatsächlichen Host/Port auswählen.
2. Bei MQTT optional Benutzer/Passwort und TLS konfigurieren. Broker muss extern bereitstehen. Bei Modbus ausschließlich TCP-Verbindung angeben.
3. Messpunkt hinzufügen und Verbindung auswählen. Anzeigename, Einheit und Adresse/Topic bzw. Unit-ID/Register/Datentyp setzen.
4. Rohwert und umgerechneten Wert in der Diagnose prüfen. Faktor und Offset bei Bedarf anpassen. Für Modbus zuerst einen bekannten Messwert mit Herstellerdokumentation vergleichen.
5. Für jeden benötigten Wert einen Messpunkt anlegen, etwa Leistung, SOC, RUN und kumulativen kWh-Zähler. Ein Gerät kann Messpunkte verschiedener Verbindungen verwenden.

Protokolldetails, vollständige Beispiele und JSON-Pfade stehen in [DATENMODELL.md](DATENMODELL.md).

### Netzanschluss zuerst einrichten

Unter **Konfiguration**, Neuer Fluss, Typ Gerät, Kategorie Netzanschluss wählen. Hauptebene verwenden. Entweder einen vorzeichenbehafteten Wert auswählen oder getrennte Geräte für Bezug und Einspeisung anlegen. Vorzeichen anhand eines bekannten Betriebszustands prüfen. Optional getrennte kWh-Zähler zuordnen. Ohne Netzanschluss bleibt ein Einrichtungshinweis bestehen.

### Knoten und Geräte

Knoten mit Anzeigename und optionalem Abschnittszähler anlegen. Ein Knoten kann einen anderen Knoten als Anschluss haben. Danach Verbraucher und Erzeuger zuordnen. Der automatische Rest entspricht Zähler minus vorzeichenrichtiger Kindersumme. Gemessene Unterknoten werden einmal mit ihrem Zählerwert berücksichtigt. Die Restanzeige ist automatisch verwaltet; dafür kein zusätzliches eigenes Gerät anlegen.

Geräte mit Leistungssensor erhalten die entsprechenden Messpunkte. Bei dreiphasigen Geräten optional L1–L3 konfigurieren. Geräte mit RUN-Signal erhalten den RUN-Messpunkt und eine feste Leistung in W. Fehlende Werte werden nicht als null behandelt.

### Speicher, Hybrid-WR und MPPT

1. Pro vollständigem Speicher einen Eintrag vom Typ Speicher anlegen.
2. Gesamtkapazität in kWh, optional SOC-Reserve und maximale Balkenleistung angeben.
3. SOC- und Leistungsdatenpunkt auswählen. Das Lade-Vorzeichen anhand eines tatsächlichen Ladevorgangs prüfen.
4. Optional einen Knoten zuordnen. Speicher bleiben aus der AC-Verrechnung herausgenommen und werden unten separat gezeigt.
5. DC-MPPTs als PV-Geräte mit Typ DC-MPPT anlegen.
6. Hybrid-Wechselrichter als PV-Gerät mit Typ Hybrid-WR anlegen. Den bidirektionalen **AC**-Leistungswert zuordnen, vorhandene Speicher und MPPTs auswählen. Positiv bedeutet AC-Abgabe, negativ AC-Aufnahme; bei Bedarf Vorzeichen invertieren.

Ab zwei Speichern erscheint die kapazitätsgewichtete Gesamtanzeige. Restlaufzeit ist eine geglättete Schätzung bis zur eingestellten Reserve. Wechselrichter-AC-Abgabe, Batterie-DC-Leistung und MPPT-Leistung werden nicht mehrfach als PV-Erzeugung summiert. Bei Hybridbetrieb bleiben nicht eindeutig ableitbare PV-/Eigenverbrauchskennzahlen unverfügbar.

### Aufzeichnung und InfluxDB

Unter **System** Recorder einschalten und Intervall wählen, z. B. 15 s. Die lokale MongoDB speichert die empfangenen normalisierten Messwerte und die abgeleiteten RUN-, Rest-, Netz- und Speicherkanäle. Die Liveanzeige ist auch ohne Recorder nutzbar; neue historische kWh benötigen Aufzeichnung oder vorhandene Historie.

Vorhandene InfluxDB-1.x-/2.x-Historie übernommener ioBroker-Datenpunkte bleibt nutzbar. Zugangsdaten unter System konfigurieren. Neue Messpunkte zeichnen zunächst lokal auf; freie neue Influx-Measurement-Zuordnungen sind noch nicht als Editorfeld verfügbar. Direkte alte ioBroker-Zuordnungen verwenden weiterhin den globalen ioBroker-Host. Übernommene Messpunkte verwenden die Verbindung unter Datenerfassung.

Energieberichte kennzeichnen Methode, Datenabdeckung, Lücken und Zählerresets. Ausfallzeiten werden zeitlich begrenzt überbrückt. Bei geänderter Leistung oder Zuordnung werden alte Aufzeichnungen nicht rückwirkend umgeschrieben.

### Darstellung und Einbettung

Unter **Darstellung** eckige Karten, moderne Karten oder Flussdiagramm wählen. Hintergrund, Flächen und Akzentfarbe lassen sich global speichern. Bei großen Anlagen fasst das Diagramm nach Abschnitten zusammen, die Abschnittslisten enthalten weiterhin alle Einzelgeräte. Knoten sind einklappbar und Geräte suchbar.

Direkte Ansicht ohne Navigation:

```text
http://<LXC-IP>:8000/flow
```

Beispiel für ioBroker VIS oder eine andere HTML-Übersicht:

```html
<iframe src="http://192.168.10.17:8000/flow"
        title="Energiefluss" width="100%" height="900"
        style="border:0"></iframe>
```

Die tatsächliche LXC-IP verwenden. Bei HTTPS auf der Zielseite auch das Dashboard per HTTPS bereitstellen, damit der Browser keine gemischten Inhalte blockiert. Die eingebettete Seite enthält keine Konfigurationsformulare; die übrigen API-Endpunkte bleiben über das LAN erreichbar.

## 7. Updates ohne Neueinrichtung

Ein Update übernimmt dieselbe MongoDB und dieselbe Umgebungsdatei. Nicht zuerst die Anwendung oder Datenbank löschen. Vor allem `DB_NAME` und `MONGO_URL` nicht versehentlich auf eine neue leere Datenbank ändern.

Vorbereitung:

- Keine parallelen Updates starten; Sicherungen bei großen Datenbeständen zeitlich einplanen.
- Ausreichend freien Platz prüfen: zusätzlich mindestens Platz für Anwendung inklusive Python-Umgebung, komprimierte vollständige Datenbank und die vorherige Anwendung. Bei großer Historie entsprechend mehr.
- Für einen zusätzlichen Rückweg ist ein Proxmox-Backup des gestoppten Containers sinnvoll. Bei externer MongoDB deren Sicherung separat berücksichtigen.
- Paketquellen, PyPI und GitHub müssen erreichbar sein.

### Erstes Update von der alten Version

Die erste Version enthält noch kein Updateskript. Deshalb einmal herunterladen:

```bash
curl -fL --retry 3 https://raw.githubusercontent.com/Chris87-ux/EnergieDashboard/main/deploy/update.sh -o /tmp/energieboard-update.sh
bash /tmp/energieboard-update.sh
```

### Weitere Updates

```bash
bash /opt/energieboard/deploy/update.sh
```

Optional kann als Argument ein vorhandener Git-Tag oder eine vollständige Commit-ID übergeben werden. Das Skript löst den Stand auf einen festen Commit auf und lädt Archiv und Prüfsumme von genau diesem Stand. Nicht auf eine ältere Anwendung mit neuerer Datenbank downgraden; dafür die passende Sicherung verwenden.

Ablauf:

1. Download und Prüfsumme prüfen, Archivpfade kontrollieren.
2. Dienst anhalten, damit während Sicherung und Migration keine neuen Messwerte geschrieben werden.
3. Datenbank einschließlich Historie und Indizes, Anwendung inklusive Python-Umgebung, Dienstdatei und Umgebungsdatei unter `/var/backups/energieboard/<Zeitpunkt>-<PID>/` sichern.
4. Anwendung austauschen, Abhängigkeiten installieren und mit bestehender MongoDB starten.
5. Additive Migration beim Start, API-Funktionstest, installierten Commit in `/opt/energieboard/INSTALLED_COMMIT` speichern.
6. Bei einem Fehler nach Austausch die vorherige Anwendung und gesicherte Datenbank wiederherstellen. Scheitert die Datenwiederherstellung, bleibt der Dienst angehalten und meldet den Sicherungspfad.

Der Updater verändert die Umgebungsdatei nicht und installiert beim Update keine neue MongoDB. Bei lokaler MongoDB bleibt der bereits bestehende Dienst erhalten. Sicherungen enthalten Zugangsdaten und sind nur für root zugänglich. Sie werden nicht automatisch gelöscht. Nach geprüfter erfolgreicher Aktualisierung können ältere Sicherungen nach eigener Sicherungsstrategie entfernt werden.

Die Schemaübernahme ersetzt bestehende ioBroker-Verweise durch stabile Messpunkt-IDs, erhält aber die bisherigen historischen Schlüssel. Dieser Vorgang ist mehrfach ausführbar. Neu hinzugekommene Einstellungen wie die Speicherkapazität müssen einmal ergänzt werden; vorhandene Datenquellen und Geräte werden übernommen.

### Manuelle Wiederherstellung

Nur im Fehlerfall und mit der tatsächlich passenden Sicherung arbeiten. Zuerst Dienst stoppen. Das aktuelle Anwendungsverzeichnis zur Diagnose an einen anderen freien Pfad verschieben, die gesicherte `application.tar.gz` wieder nach `/opt` entpacken. Die virtuelle Umgebung ist im Archiv enthalten. Gesicherte Umgebungs- und Dienstdatei wieder an ihre ursprünglichen Orte kopieren, jeweils mit passenden root-Rechten.

Die Datenbank mit der `deploy/backup.py` der neuen Version wiederherstellen:

```bash
systemctl stop energieboard
/opt/energieboard/.venv/bin/python /pfad/zur/neuen/deploy/backup.py restore /var/backups/energieboard/TATSAECHLICHE-SICHERUNG/database
systemctl daemon-reload
systemctl start energieboard
```

Der Restore ersetzt den Inhalt der in der Umgebungsdatei angegebenen Datenbank durch die Sicherung. Deshalb ausschließlich eine eigene Energieboard-Datenbank verwenden und vorher die Verbindungsdaten prüfen. Die Sicherung enthält BSON-Datentypen, historische Samples und Indizes. Zum Wiederherstellen einer älteren Anwendung ggf. zuerst die neue `backup.py` aus dem heruntergeladenen Archiv an einen separaten Ort kopieren.

## 8. Betrieb und Fehlersuche

```bash
systemctl status energieboard mongod --no-pager
journalctl -u energieboard -n 100 --no-pager
curl -fsS http://127.0.0.1:8000/api/
df -h /opt /var/lib/mongodb /var/backups
free -h
```

Bei externer MongoDB den lokalen `mongod`-Status überspringen. Fehler der Datenquelle unter Datenerfassung anhand Rohwert, Empfangszeit und Verbindungsstatus prüfen. Bei Modbus besonders Unit-ID, Registerbasis, Datentyp und Reihenfolge beachten. Bei MQTT müssen Topic und JSON-Pfad exakt passen.

Der Recorder besitzt aktuell keine automatische Löschfrist. Datenbestand und Sicherungsplatz überwachen. Beispiel: 100 Kanäle alle 15 s ergeben etwa 576.000 Rohsamples pro Tag, zuzüglich abgeleiteter Kanäle. Die tatsächliche Größe hängt von MongoDB-Kompression, Indizes und Daten ab. Bei wachsender Historie größere Datenträger oder ein gröberes Intervall einplanen.

## 9. Selbst bauen und testen

Für die Entwicklung Python 3.11 und Node.js ab 22.12 verwenden. Im Backend eine virtuelle Umgebung anlegen und `requirements.txt` installieren. Im Frontend:

```bash
cd app/frontend
npm ci
npm run build
```

Backendtests vom Projektverzeichnis:

```bash
PYTHONPATH=app/backend python -m unittest discover -s app/backend/tests -v
```

Die Integrationstests verwenden eine eigene temporäre MongoDB und ausschließlich lokale Testprotokollserver. `MONGOD_BIN` muss auf eine passende mongod-Datei zeigen:

```bash
MONGOD_BIN=/usr/bin/mongod python app/backend/tests/integration_modular.py
```

Für die optionale Chromium-Prüfung `BROWSER_TEST` auf `app/backend/tests/browser_modular.cjs` und `BROWSER_HOME` auf eine Umgebung mit Playwright-Core und dem im Skript konfigurierten Chromium setzen. Die bereitgestellte Browserprüfung ist auf den verwendeten Windows-Testpfad innerhalb von BROWSER_HOME ausgelegt; bei Linux den Chromium-Pfad im Skript anpassen.

Die hier durchgeführten Tests ersetzen keinen Test mit den tatsächlichen Geräten und dem Proxmox-Kernel. Details und genaue Prüfgrenzen stehen im [Prüfbericht](PRUEFBERICHT.md).
