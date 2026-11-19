# Energieboard auf Proxmox installieren

Stand 19. November 2026. Die Anwendung läuft als systemd-Dienst in einem Debian-LXC. MongoDB speichert Konfiguration und Messwerte. ioBroker liefert die aktuellen Zustände. InfluxDB kann zusätzlich vorhandene Historie normaler Messgeräte liefern.

## 1. Voraussetzungen

| Bereich | Voraussetzung |
| --- | --- |
| Proxmox | Laufender Proxmox-VE-Host und Zugang zur Weboberfläche beziehungsweise Host-Shell |
| Container | Unprivilegierter LXC mit **Debian 12 Bookworm, amd64** |
| CPU | Zwei zugewiesene CPU-Kerne als Startgröße |
| Arbeitsspeicher | Mindestens 2 GB, für die geplanten 30–50 Geräte zunächst 4 GB einplanen |
| Datenträger | Mindestens 16 GB, als Startgröße 32 GB auf SSD einplanen und Datenwachstum beobachten |
| CPU für lokale MongoDB | x86-64-Prozessor mit AVX-Unterstützung |
| Netzwerk | LAN-Adresse, Standard-Gateway und funktionierende DNS-Auflösung |
| Installation | HTTP/HTTPS zu den Debian-Paketquellen sowie HTTPS zu PyPI und den offiziellen MongoDB-Paketquellen |
| ioBroker | Erreichbarer simple-api-Adapter mit lesbaren Datenpunkten, üblicherweise TCP-Port 8087 |
| Browser | Zugriff vom eigenen Gerät auf TCP-Port 8000 des LXC |
| Dateiübertragung | SCP-Client auf dem PC oder ein geeignetes SCP-Programm |
| Optional | InfluxDB 1.x oder InfluxDB 2.x mit Flux und passendem Lesezugriff |

Die Ressourcenwerte sind Startgrößen für dieses Projekt. Die benötigte Festplatte hängt vor allem von Zahl der Datenpunkte, Recorder-Intervall und Aufzeichnungsdauer ab.

MongoDB 8.0 unterstützt Debian 12 amd64. Die Herstelleranforderungen umfassen AVX sowie passende CPU-Generationen, darunter Intel Core ab Haswell, Celeron/Pentium ab Tiger Lake oder AMD ab Bulldozer. Ein LXC nutzt den Kernel und die CPU-Funktionen des Proxmox-Hosts. Der Installer begrenzt bei einer neu installierten MongoDB den WiredTiger-Cache auf 0,5 GB. [MongoDB auf Debian](https://www.mongodb.com/docs/v8.0/tutorial/install-mongodb-on-debian/), [MongoDB-Betriebshinweise](https://www.mongodb.com/docs/v8.0/administration/production-notes/)

Die MongoDB-Betriebshinweise nennen derzeit eine Inkompatibilität mit Linux-Kernel 6.19 bis 7.0.13. Bei einem Host in diesem Versionsbereich vor der lokalen Datenbankinstallation den dort beschriebenen behobenen Kernel einsetzen oder eine externe MongoDB verwenden. Mit `uname -r` lässt sich der im LXC sichtbare Host-Kernel prüfen. [MongoDB-Kernelhinweis](https://www.mongodb.com/docs/v8.0/administration/production-notes/)

Die Oberfläche ist im Paket fertig gebaut. Der Installer richtet die Python-Abhängigkeiten und den Dienst im Container ein.

## 2. Paket und Anleitung

Im Projektordner liegen nach der Erstellung unter `outputs` folgende Dateien.

- `Energieboard-LXC.tar.gz` enthält Anwendung, gebaute Oberfläche, Installer und diese Anleitung.
- `SHA256SUMS` enthält die Prüfsumme des Installationsarchivs.
- `Installationsanleitung.md` enthält diese Anleitung separat.

Die Verzeichnisstruktur nach dem Entpacken ist `/opt/energieboard`. Der Installer und die Dienstdatei verwenden diesen Pfad.

## 3. LXC in Proxmox anlegen

Diese Schritte erfolgen in der **Proxmox-Weboberfläche**.

1. Den gewünschten Proxmox-Knoten auswählen.
2. Einen Storage mit Container-Templates öffnen, üblicherweise **local → CT Templates → Templates**.
3. Ein **Debian-12-amd64-Template** herunterladen. Den tatsächlich angebotenen Dateinamen verwenden.
4. **CT erstellen** wählen.
5. Eine freie Container-ID vergeben und notieren, zum Beispiel `123`.
6. Als Hostnamen beispielsweise `energieboard` verwenden.
7. Ein Root-Passwort festlegen und **unprivilegierter Container** aktivieren.
8. Das heruntergeladene Debian-12-Template auswählen.
9. Festplatte und Ressourcen entsprechend der Tabelle festlegen.
10. Die LAN-Bridge des eigenen Proxmox-Hosts auswählen, häufig `vmbr0`.
11. DHCP mit einer festen Router-Zuordnung oder eine passende statische IP samt Gateway eintragen.
12. Den DNS-Server setzen beziehungsweise die funktionierende Host-Konfiguration übernehmen.
13. Den Container erstellen und starten.

Unter **LXC → Optionen → Beim Booten starten** lässt sich der Start zusammen mit dem Proxmox-Host aktivieren.

## 4. Archiv auf den Proxmox-Host übertragen

Diese Befehle erfolgen in einer **PowerShell auf deinem PC**, geöffnet im Projektordner. `PROXMOX-IP` durch die tatsächliche Adresse des Proxmox-Hosts ersetzen.

```powershell
scp .\outputs\Energieboard-LXC.tar.gz .\outputs\SHA256SUMS root@PROXMOX-IP:/root/
```

Beim ersten SSH-Zugriff den angezeigten Hostschlüssel mit dem Proxmox-Host abgleichen. Alternativ können beide Dateien mit einem SCP-Programm nach `/root/` auf dem Proxmox-Host übertragen werden.

## 5. Prüfen und in den Container kopieren

Die folgenden Befehle in der **Proxmox-Host-Shell** ausführen.

```sh
cd /root
sha256sum -c SHA256SUMS
```

Erwartet wird `Energieboard-LXC.tar.gz: OK`.

Nun die Container-ID anpassen und das Archiv übertragen. Der Container muss bereits laufen.

```sh
CTID=123
pct status "$CTID"
pct push "$CTID" /root/Energieboard-LXC.tar.gz /tmp/Energieboard-LXC.tar.gz
pct enter "$CTID"
```

Nach `pct enter` befindet sich die Shell im **LXC-Container**. Die weiteren Installationsbefehle werden dort als root ausgeführt. Die Proxmox-Container-Verwaltung dokumentiert die Befehle `pct push` und `pct enter`. [Proxmox-Container-Verwaltung](https://pve.proxmox.com/pve-docs/pct.1.html)

## 6. Container vorab prüfen

In der **LXC-Konsole**.

```sh
cat /etc/os-release
dpkg --print-architecture
uname -r
hostname -I
getent hosts pypi.org
getent hosts repo.mongodb.org
grep -w avx /proc/cpuinfo
```

Erwartet werden Debian 12 mit Codename `bookworm`, Architektur `amd64`, eine passende LAN-Adresse, aufgelöste Hostnamen und mindestens eine CPU-Zeile mit `avx`.

Wenn AVX fehlt, kann eine externe MongoDB verwendet werden. Die Variante ist in Abschnitt 10 beschrieben.

## 7. Installieren

Weiterhin in der **LXC-Konsole als root**.

```sh
mkdir -p /opt
tar -xzf /tmp/Energieboard-LXC.tar.gz -C /opt
bash /opt/energieboard/deploy/install.sh
```

Der Installer führt die folgenden Schritte aus.

1. Debian-Version, Architektur, systemd und die enthaltene Oberfläche prüfen.
2. Python, curl und die benötigten Pakete installieren.
3. Bei Bedarf MongoDB 8.0 aus der offiziellen Paketquelle installieren.
4. Für eine neu installierte MongoDB den Cache auf 0,5 GB begrenzen und den Dienst starten.
5. Den Dienstbenutzer `energieboard` anlegen.
6. Die Konfiguration unter `/etc/energieboard/energieboard.env` anlegen.
7. Die Python-Umgebung unter `/opt/energieboard/.venv` einrichten.
8. Oberfläche, Datenbankversion, Datenbankverbindung und Indizes prüfen.
9. `energieboard.service` aktivieren und starten.
10. API und Oberfläche per HTTP prüfen.

Eine vorhandene Konfigurationsdatei wird weiterverwendet. Bei bereits installierter MongoDB bleibt deren Cache-Konfiguration in der Verantwortung der bestehenden Datenbankinstallation. Der vom Installer angelegte Cache-Zusatz liegt unter `/etc/systemd/system/mongod.service.d/energieboard-cache.conf`.

Am Ende erscheint die Meldung, dass Energieboard läuft.

## 8. Ersten Start prüfen

In der **LXC-Konsole**.

```sh
systemctl is-active mongod
systemctl is-active energieboard
curl -fsS http://127.0.0.1:8000/api/
/opt/energieboard/.venv/bin/python /opt/energieboard/deploy/check.py
```

Bei lokaler MongoDB sollen beide Dienste `active` melden. Die API liefert ein JSON-Objekt mit `"status":"ok"`. Die Vorprüfung bestätigt die Python- und MongoDB-Version sowie die enthaltene Oberfläche.

Mit `hostname -I` die Container-IP ermitteln. Im Browser beispielsweise `http://192.168.1.50:8000/system` öffnen und die Beispiel-IP durch die eigene LXC-Adresse ersetzen.

Die Oberfläche hat keine eigene Anmeldung. Der Zugriff auf TCP-Port 8000 gehört in das vertrauenswürdige LAN. Wenn eine Proxmox-Firewall aktiv ist, eine passende Regel für die zugelassenen Geräte beziehungsweise das LAN setzen. Für einen weitergehenden Zugriff einen Reverse-Proxy mit Zugriffsschutz und HTTPS vorsehen. MongoDB bleibt bei der lokalen Standardinstallation auf dem Loopback-Zugang.

## 9. ioBroker und Geräte einrichten

### Verbindung

1. In ioBroker den Adapter **simple-api** installieren und starten.
2. Dessen Hostadresse und Port notieren. Der häufig verwendete Standardport ist `8087`.
3. In Energieboard unter **System → ioBroker** Host, Port und Protokoll eintragen.
4. Im Host-Feld ausschließlich Hostname oder IP eintragen. Protokoll und Port haben eigene Felder.
5. **Verbindung testen** auswählen.
6. **Einstellungen speichern** auswählen.

Der derzeitige Connector erwartet einen im vertrauenswürdigen LAN erreichbaren simple-api-Lesezugang. Die Verbindungsmaske unterstützt Host, Port und Protokoll. Falls der Adapter eine zusätzliche Anmeldung verlangt, muss der Zugriff für diesen Connector passend im eigenen LAN bereitgestellt werden.

Vor der Geräte-Konfiguration kann die Verbindung mit dem folgenden Befehl in der LXC-Konsole geprüft werden. IP und Port anpassen.

```sh
curl -fsS http://192.168.1.20:8087/help
```

### Knoten anlegen

Unter **Konfiguration → Knoten hinzufügen** einen Abschnitt wie `Werkstatt` anlegen.

- Im Reiter **Phasen** ein- oder dreiphasige Anzeige einstellen.
- Bei einphasiger Anzeige die zugehörige Phase auswählen.
- Unter **Datenpunkte** Gesamtleistung oder die drei Phasenwerte des Abschnittszählers eintragen.
- Die Einheit des Zählers korrekt auf W beziehungsweise kW einstellen.
- Positive Knotenleistung bedeutet Verbrauch, negative Knotenleistung bedeutet Erzeugung. Falls der Zähler die umgekehrte Konvention nutzt, das Vorzeichen im Editor umkehren.

Ein Knoten kann Verbraucher, Erzeuger und Speicher enthalten. Die Übersicht bilanziert seine Kinder. Unter **Zähler und Verrechnung** stehen Zählerwert, Summe der Geräte und die Differenz.

Beispiel mit positivem Verbrauch.

| Wert | Leistung |
| --- | --- |
| Motor | +300 W |
| RUN-Pumpe | +200 W |
| PV-Erzeuger | −100 W |
| Speicher lädt | +200 W |
| Summe der Geräte | +600 W |
| Abschnittszähler | +1.000 W |
| Unzugeordnete Differenz | +400 W |

Die Differenz wird als Kontrolle angezeigt. Fehlende Gerätewerte führen zu einer unbekannten Differenz. Die aktuelle Struktur umfasst eine Knotenebene unter der Hauptebene.

### Geräte mit Sensor anlegen

Unter **Neuer Fluss** den Typ **Gerät / Erzeuger** wählen. Richtung, Kategorie, Name, Einheit, Phasen und Datenpunkte einstellen. Als Anschluss den zugehörigen Knoten oder die Hauptebene auswählen.

- **Zufluss** wird beispielsweise für PV-Erzeugung oder Netzbezug verwendet.
- **Abfluss** wird beispielsweise für Verbraucher oder Netzeinspeisung verwendet.
- Ein konfigurierter Energiezähler sollte ein fortlaufender Zählerstand in Wh oder kWh sein.
- Wenn kein Energiezähler vorhanden ist, wird vorhandene historische Wirkleistung integriert.
- Für die Kennzahlen zu Autarkie und Eigenverbrauch Netzbezug beziehungsweise Netzeinspeisung als Flüsse der Kategorie **Netz** mit passender Richtung konfigurieren. Fehlende Netzwerte werden als unbekannt angezeigt.

Die Gesamtkennzahlen beziehen sich auf die konfigurierten Geräte. Ein Abschnittszähler als Knoten dient der Kontrolle seiner Kinder.

### RUN-Geräte anlegen

Im Geräteeditor unter **Datenpunkte** die RUN-Schätzung aktivieren. Einen RUN-Datenpunkt und die feste Betriebsleistung in Watt eintragen, beispielsweise `200`.

`true`, `1` oder ein anderer numerischer Wert ungleich `0` bedeutet Betrieb. `false` beziehungsweise `0` bedeutet aus. Ein fehlender Wert gilt als unbekannt.

Bei Betrieb zeigt das Gerät die hinterlegte Leistung an. Die aufgezeichnete Laufzeit wird als **RUN-Schätzung** in kWh bilanziert. Änderungen der Wattzahl gelten für neue Aufzeichnungen. Der Recorder muss dafür eingeschaltet sein.

### Speicher anlegen

Unter **Speicher hinzufügen** einen Speicher mit folgenden Angaben anlegen.

- Vorzeichenbehafteter Leistungsdatenpunkt in W oder kW.
- SOC-Datenpunkt in Prozent von 0 bis 100.
- Einstellung, ob eine positive oder negative Leistung Laden bedeutet.
- Zugehöriger Knoten oder **Hauptebene / vor Abschnittszählern**.

Laden und Entladen werden getrennt bilanziert. Die neuen Speicherkanäle sammeln Historie ab ihrer Einrichtung bei aktiver Aufzeichnung.

### Recorder und Historie

Unter **System → Recorder** das Intervall prüfen. Der Standard beträgt 15 Sekunden. Zustandswechsel zwischen zwei Abfragen können mit dieser Genauigkeit erfasst werden. Bei längeren Ausfällen werden Werte zeitlich begrenzt weitergeführt und anschließend Datenlücken ausgewiesen.

Die Messwerte werden fortlaufend in MongoDB gespeichert. Bei 100 aufgezeichneten Kanälen und 15 Sekunden Intervall entstehen rechnerisch 576.000 Messwertdokumente pro Tag. RUN- und Speicherkanäle kommen zu ihren ursprünglichen Datenpunkten hinzu. Die tatsächliche Dateigröße hängt auch von Kompression und Indizes ab.

Der aktuelle Stand hat keine automatische Aufbewahrungsfrist. Den belegten Speicher regelmäßig prüfen.

```sh
df -h /
du -sh /var/lib/mongodb
```

### Optional InfluxDB verbinden

Unter **System → InfluxDB** die vorhandene Datenbank aktivieren.

- Für Version 1.x URL, Datenbank und gegebenenfalls Benutzer und Passwort eintragen.
- Für Version 2.x URL, Organisation, Bucket und Token mit Leserechten eintragen.
- Measurement muss der konfigurierten Datenpunkt-ID entsprechen. Der Standard-Feldname ist `value`.
- Verbindung testen und speichern.

Diese Anbindung unterstützt InfluxDB 1.x und die Flux-Schnittstelle von InfluxDB 2.x. Neue RUN- und Speicherkanäle werden aus der lokalen Aufzeichnung berechnet. Die Historie dieser Kanäle beginnt mit ihrer lokalen Aufzeichnung.

## 10. Externe MongoDB verwenden

Diese Variante passt beispielsweise zu einem Proxmox-Host ohne AVX oder zu einer bereits vorhandenen Datenbank. Die externe Datenbank muss vom LXC erreichbar sein. Die Historienberechnung benötigt MongoDB ab Version 5.0. Die aktuelle Prüfumgebung verwendet MongoDB 8.0.

Zuerst das Archiv wie in Abschnitt 7 entpacken. Dann in der **LXC-Konsole**.

```sh
install -d -m 0700 /etc/energieboard
install -m 0600 /opt/energieboard/deploy/energieboard.env.example /etc/energieboard/energieboard.env
editor /etc/energieboard/energieboard.env
```

Beispiel für den Dateiinhalt mit einer externen Datenbank. Adresse, Benutzer, Passwort und Authentifizierungsdatenbank anpassen. Sonderzeichen in den URI-Zugangsdaten müssen URL-kodiert werden.

```dotenv
MONGO_URL=mongodb://BENUTZER:PASSWORT@MONGODB-IP:27017/energieboard?authSource=energieboard
DB_NAME=energieboard
```

Der Datenbankbenutzer benötigt Lese- und Schreibrechte samt Index-Erstellung für die Datenbank `energieboard`. Zugangsdaten nicht in Browser-URLs eintragen.

Danach installieren.

```sh
bash /opt/energieboard/deploy/install.sh --external-mongo
```

Bei dieser Variante ist die externe Datenbank für Verfügbarkeit, Speicherbedarf und Sicherung zuständig. Bei Updates dieselbe Installer-Option verwenden.

## 11. Neustart, Update und Sicherung

### Neustart

```sh
systemctl restart energieboard
systemctl status energieboard --no-pager
```

Nach einem Container-Neustart startet der aktivierte Dienst automatisch. Bei lokaler MongoDB startet auch `mongod`.

### Update

Vor dem Update eine Sicherung des LXC anlegen. Das neue Archiv und seine Prüfsumme wie zuvor auf den Proxmox-Host übertragen, dort prüfen und mit `pct push` in den laufenden Container kopieren.

Danach in der **LXC-Konsole**.

```sh
systemctl stop energieboard
tar -xzf /tmp/Energieboard-LXC.tar.gz -C /opt
bash /opt/energieboard/deploy/install.sh
```

Bei externer MongoDB die letzte Zeile mit `--external-mongo` ausführen. Die Konfiguration liegt unter `/etc/energieboard/energieboard.env`, die lokale Datenbank standardmäßig unter `/var/lib/mongodb`. Die Aktualisierung des Anwendungspakets ersetzt diese Daten nicht.

Für eine vollständige Sicherung des lokalen Datenbankstands kann ein Proxmox-Backup im Modus **Stop** verwendet werden. Dabei wird der Container während der Sicherung angehalten. Bei externer MongoDB muss zusätzlich die externe Datenbank gesichert werden.

## 12. Fehlersuche

### Installer bricht ab

Die zuletzt angezeigte Fehlermeldung prüfen. Bei DNS-Problemen Gateway und DNS des LXC kontrollieren. Bei Paketfehlern die Erreichbarkeit der in Abschnitt 1 genannten Quellen prüfen. Das Skript kann nach Beheben des Fehlers erneut gestartet werden.

### Anwendung startet nicht

```sh
systemctl status energieboard --no-pager -l
journalctl -u energieboard -b -n 80 --no-pager
/opt/energieboard/.venv/bin/python /opt/energieboard/deploy/check.py
```

Die Vorprüfung testet die Paketdateien und MongoDB. Bei Verbindungsausfällen `MONGO_URL`, Datenbankname, Zugangsdaten und Erreichbarkeit prüfen.

### Lokale MongoDB startet nicht

```sh
systemctl status mongod --no-pager -l
journalctl -u mongod -b -n 80 --no-pager
grep -w avx /proc/cpuinfo
df -h /
```

Zusätzlich die MongoDB-Logdatei `/var/log/mongodb/mongod.log` prüfen. Fehler wie `Illegal instruction` deuten auf nicht erfüllte CPU-Anforderungen hin. Bei vorhandenem MongoDB-Bestand auch dessen Version und Konfiguration prüfen.

### API lokal erreichbar, Browser im LAN erreicht das Board nicht

```sh
hostname -I
ss -ltnp | grep ':8000'
curl -fsS http://127.0.0.1:8000/api/
```

Die Anwendung soll auf `0.0.0.0:8000` lauschen. Im Browser die LXC-IP samt Port verwenden. Proxmox-Firewall, VLAN, Netzwerk-Bridge und LAN-Routing prüfen.

### Oberfläche zeigt fehlende Messwerte

Unter **System** die Verbindung testen und unter **Konfiguration** die Datenpunkt-IDs, Einheiten und Aktivierung prüfen. Auch der zugehörige Knoten muss aktiv sein. Für Energiewerte nach der Einrichtung zunächst Messwerte sammeln lassen und unter **System** den Recorder-Status prüfen.

### Port 8000 ist belegt

Mit `ss -ltnp | grep ':8000'` den belegenden Dienst ermitteln. Der mitgelieferte Installer und die Dienstdatei verwenden Port 8000. Einen vorhandenen Dienst gezielt umkonfigurieren oder für Energieboard einen eigenen Container verwenden.

## 13. Prüfumfang dieses Pakets

Der Prüfumfang und die tatsächlichen Ergebnisse stehen im mitgelieferten Prüfbericht. Die bisherigen lokalen Funktionsprüfungen umfassen echte MongoDB, API-Aufrufe und einen Chromium-Browser. ioBroker- und InfluxDB-Antworten werden für automatisierte Tests kontrolliert nachgebildet. Der erste vollständige Installationslauf auf deinem Proxmox-LXC sowie die Verbindung zu deinen echten Anlagen gehören zur Inbetriebnahme.

Die mitgelieferten Rechen- und Regressionstests lassen sich bei Bedarf auch im LXC starten.

```sh
cd /opt/energieboard/app/backend
/opt/energieboard/.venv/bin/python -m unittest discover -s tests -v
```
