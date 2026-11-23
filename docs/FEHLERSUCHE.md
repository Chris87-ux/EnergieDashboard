# Fehlersuche

[Dokumentationsübersicht](README.md) · [Ersteinrichtung](ERSTE-SCHRITTE.md) · [Betrieb und Backups](BETRIEB-UND-UPDATES.md)

## Zuerst eingrenzen

1. **Dienst erreichbar?** Lokal auf dem Server API testen.
2. **Datenquelle erreichbar?** Netzwerk vom Energieboard-Server bzw. App-Container zur Quelle prüfen.
3. **Messpunkt verfügbar?** Datenerfassung: Rohwert, Faktor, Einheit und Empfangszeit vergleichen.
4. **Gerät korrekt zugeordnet?** Typ, Rolle, Phase, Knoten und AC/DC prüfen.
5. **Historie vorhanden?** Recorder aktiv, Zeitraum und Abdeckung kontrollieren.

Bei einer Problemmeldung Version, Installationsart, Zeitpunkt, betroffenen Typ/Messpunkt und relevante Logs notieren. Kennwörter, Tokens und sensible Daten vor Veröffentlichung entfernen; nicht die vollständige Umgebungsdatei posten.

## Netzwerk und APT

### „No route to host“ / „Network is unreachable“

**Im LXC:**

```bash
ip -4 addr show
ip -4 route show
getent ahostsv4 deb.debian.org
```

- Default-Route muss über den tatsächlichen Router laufen. `default via 255.255.255.0` ist falsch: Das ist eine Netzmaske, kein Router.
- Adresse und Präfix müssen zum LAN passen; /24 entspricht 255.255.255.0, /25 entspricht 255.255.255.128.
- Bridge, VLAN und Proxmox-/Router-Firewall kontrollieren. DNS-Auflösung allein beweist keine funktionierende Internetroute.
- Netzwerkdaten in Proxmox für den Container dauerhaft korrigieren; eine manuelle temporäre Route im Gast wird möglicherweise beim Neustart ersetzt.

Bei allein fehlendem IPv6 kann `apt-get -o Acquire::ForceIPv4=true update` helfen. Wenn auch IPv4 scheitert, zuerst Routing/Firewall reparieren. APT-Sicherheitsprüfungen nicht abschalten. Ein wegen Netzwerkfehlern nicht abgerufenes Release-Dokument ist kein Anlass, Debian-Paketquellen als unsicher zu erzwingen.

### „Port schon belegt“

Docker: anderen freien `ENERGIEBOARD_PORT` in `.env` wählen und Compose erneut starten. Danach die Browseradresse und API-Prüfung anpassen. LXC: anderen auf 8000 lauschenden Dienst ermitteln; Energieboard-Dienstdatei verwendet fest Port 8000.

## Anwendung startet nicht

### LXC

```bash
systemctl status energieboard --no-pager
journalctl -u energieboard -n 100 --no-pager
curl -fsS http://127.0.0.1:8000/api/
```

Bei lokaler Datenbank zusätzlich:

```bash
systemctl status mongod --no-pager
journalctl -u mongod -n 80 --no-pager
```

„Installer ist für Debian 12 ... vorbereitet“: passendes Template verwenden. Fehlende gebaute Oberfläche: LXC-Paket aus `outputs/` verwenden; ein reiner Quellcode-Clone enthält kein gebautes `dist`.

### Docker

Im Projektverzeichnis:

```bash
docker compose ps
docker compose logs --tail=100 energieboard
docker compose logs --tail=100 mongo
```

Bei externer MongoDB jeweils `-f compose.external.yaml` verwenden und den nicht vorhandenen lokalen `mongo`-Dienst überspringen.

`unhealthy`: Logs des betroffenen Dienstes lesen, nicht nur wiederholt neu starten. Mögliche Ursachen sind Datenbankverbindung, Migration, inkompatibler Kernel/CPU oder fehlende Ressourcen. `Illegal instruction` bei MongoDB kann auf fehlende CPU-Funktionen hinweisen; AVX **im Gast** prüfen. Bei Kernelproblemen die aktuellen [MongoDB-Plattformhinweise](https://www.mongodb.com/docs/manual/administration/production-notes/) für den konkreten Patchstand beachten.

### Lokal erreichbar, im Browser nicht

Richtige Server-IP und Hostport, Dienst-Bindadresse, Proxmox-/Hostfirewall und Reverse-Proxy prüfen. Docker mit Bind `127.0.0.1` ist absichtlich nicht direkt aus dem LAN erreichbar. `localhost` im Browser meint den Browser-PC.

## Messwerte fehlen oder sind falsch

| Symptom | Prüfen |
|---|---|
| ioBroker nicht erreichbar | simple-api-Adapter aktiv, richtiger Port, vollständige Objekt-ID; nicht Admin-/Web-Port |
| Neue Messpunkte trotz System-ioBroker ohne Wert | Eigene Verbindung unter Datenerfassung ist erforderlich |
| MQTT „veraltet“ | Exaktes Topic, JSON-Pfad, ACLs, Publisher-Intervall und Gültigkeit |
| MQTT Retained-Wert wirkt alt | Empfangszeit ist nicht ursprünglicher Messzeitpunkt; regelmäßige Updates sicherstellen |
| Modbus Timeout/Exception | Freigeschalteter TCP-Server, Unit-ID, Funktion, Registerbereich und Geräteverbindungen |
| Modbus riesige oder unsinnige Werte | Vorzeichenfähiger Typ, 0-basierte Adresse, Faktor, Byte-/Wortreihenfolge |
| Faktor 1000 daneben | W/kW bzw. Wh/kWh und doppelte Skalierung kontrollieren |
| Docker findet Quelle unter localhost nicht | LAN-Adresse verwenden; localhost ist der App-Container |
| Rohwert korrekt, Gerät falsch | Geräteeinheit, gewähltes Feld, Richtung und Invertierung prüfen |

## Knoten fehlen oder Rest ist unplausibel

- In der Konfiguration wirklich **Typ Knoten** wählen; der Name allein macht kein Gerät zum Knoten.
- Im Flussdiagramm die richtige Ebene öffnen, Pfadleiste und weitere Diagrammseiten beachten.
- Übergeordneten Knoten und Aktivierung kontrollieren. Ein deaktivierter Elternknoten deaktiviert seine ganze Unterstruktur.
- Kein zusätzliches normales Gerät mit der vollen Knoten-Zählerleistung anlegen; der automatische Rest übernimmt dies.
- Knotenmessung muss netto positiv Verbrauch/negativ Erzeugung abbilden. Normale Erzeuger werden anhand ihrer Rolle gegengerechnet.
- Bei fehlendem Kind-/Zählerwert ist unbekannter Rest korrekt. Nicht durch 0 ersetzen.
- Ein gemessener Unterknoten zählt am Elternknoten einmal mit seinem Messwert; dessen Kinder nicht nochmals separat auf der Hauptebene anlegen.

## Gerät verschwindet nach kurzer Zeit

Nullfilter unter Darstellung kontrollieren. Standardmäßig werden Geräte erst nach 60 Sekunden strikt zwischen −1 W und +1 W ausgeblendet. „Inaktive anzeigen“ zum Prüfen aktivieren. Größere negative Erzeugerwerte müssen sichtbar bleiben. Fehlender Wert ist nicht Nullleistung. [Filterregeln](DARSTELLUNG-UND-EINBETTUNG.md#geräte-bei-nullleistung-ausblenden).

## Speicher und Hybrid

| Symptom | Erklärung / Lösung |
|---|---|
| Speicher lädt laut Quelle, Anzeige entlädt | Lade-Vorzeichen und davor wirkende allgemeine Invertierung prüfen |
| Kein Gesamt-SOC | Mindestens zwei Speicher und vollständige Kapazitäts-/SOC-Werte erforderlich |
| Keine Restlaufzeit | Laden, kleine Entladung, fehlende Reserve/SOC/Leistung oder Glättung nach Wechsel prüfen |
| DC-MPPT hat alte Phasenwerte | Gesamtleistung und Gesamtenergie zuordnen; DC-Phasen werden ignoriert |
| Hybrid lässt sich nicht speichern | Mindestens einen DC-Speicher, gültige AC-Leistung und bei Portmodus zusätzlich AC-In zuordnen |
| Speicherwechsel auf AC wird abgewiesen | Erst Zuordnung im Hybrid entfernen, dann korrigieren |
| Hybrid zeigt zu viel Erzeugung | AC-Out enthält ggf. Netzdurchleitung: AC-Out minus tatsächliches AC-In verwenden |
| Wirkungsgrad nicht verfügbar | Vollständige Bilanz bestätigen oder direkte DC-WR-Leistung zuordnen; Mindestleistung und Diagnose beachten |
| Wirkungsgrad >100 % / Vorzeichenhinweis | Messgrenzen, Skalierung, Richtung, fehlende DC-Lasten und Messzeitpunkte prüfen |
| PV-Kennzahl bei Hybrid n. v. | AC-Abgabe enthält Batterieenergie und ist kein sicherer reiner PV-Ertrag |

[Ausführliche Hybrid-Konfiguration](SPEICHER-UND-HYBRID.md).

## Historie und Energiewerte

Recorder aktivieren und Status unter System prüfen. Frisch angelegte Punkte besitzen keine Vergangenheit. Ein Zählerstand ist nicht der Tagesertrag; dafür werden zeitliche Differenzen benötigt. RUN- und Restkanäle beginnen mit der Aufzeichnung.

Lücken und unvollständige Datenabdeckung sind sichtbar und werden nicht beliebig mit Null gefüllt. Die Lückenschwelle ersetzt keine fehlenden Messungen; abgeleitete Zustandskanäle haben zusätzlich eine begrenzte Gültigkeit passend zum Recorder-Intervall. Fehlende Phasen können keine vollständige Dreiphasensumme ergeben.

DC-/Speicherzeilen werden nicht zur AC-Gesamtsumme addiert. Produktion-/Verbrauchsummen über mehrere Messgrenzen sind kein universeller PV-Ertrags- oder Haus-Gesamtzähler. [Begriffe](GLOSSAR.md) und [Datenmodell](../DATENMODELL.md) erläutern die Grenzen.

## CSV wird abgewiesen

Die genaue Vorschaufehlermeldung lesen. Häufig: unbekannte/übersetzte Spalten, Komma statt Dezimalpunkt, doppelte IDs, ungültige Verweise, Kreis in der Knotenhierarchie oder fehlender aktiver Netzanschluss. Nach zwischenzeitlicher Änderung die Vorschau neu erzeugen. Einen frischen Export bearbeiten; alte Dateien enthalten neue Felder nicht. [CSV-Anleitung](../CSV-IMPORT.md).

## Nach Update wirkt alles leer

Nicht sofort neu konfigurieren. Zuerst prüfen, ob dieselben `MONGO_URL`, `DB_NAME`, Compose-Datei und Projekt-/Volumenamen verwendet werden. Ein neuer Datenbankname oder ein anderes Volume sieht wie eine Neuinstallation aus. Beim Wechsel lokal↔extern findet keine automatische Datenkopie statt. Restore nur mit geprüftem Ziel durchführen.

## GitHub-Dockerprüfung

Im Workflow den **ersten fehlgeschlagenen Schritt** öffnen. Der historische Fehler „Bestehende Installation fehlt“ im Lauf 44885156398 stammte aus dem LXC-Updater-Test im eingeschränkten App-Container. Dieser Test läuft seit der Korrektur auf dem Linux-Runner. Der für 2.5.0 geprüfte Quellstand hat einen [erfolgreichen Dockerlauf](https://github.com/Chris87-ux/EnergieDashboard/actions/runs/45153089799).

Ein alter roter Lauf ändert sich nach einer Korrektur nicht automatisch; neuen Lauf und Commit vergleichen. Keine sinnvollen Prüfungen entfernen, nur um einen grünen Status zu erhalten.

## API liefert keine Werte

Unter Datenerfassung Protokoll API / HTTP und die passende Vorlage prüfen. Host ohne Protokoll/Port, tatsächlichen Port separat angeben. Bei HTTP 401/403 Anmeldung, Token und Berechtigungen im Quellsystem prüfen; bei 3xx den endgültigen Endpunkt statt einer Weiterleitung konfigurieren. GET-Aufruf, Antwortbasis und Messpunktpfad anhand einer aktuellen Antwort vergleichen. Home Assistant liefert mitunter `unknown`/`unavailable`; evcc-Feldnamen können sich ändern. Solche Werte bleiben unbekannt und sind kein gemessener Nullverbrauch. [API-Anleitung mit Beispielen](DATENERFASSUNG.md).

## Verbrauchergruppe fehlt oder zeigt unvollständige Werte

Gruppe unter Konfiguration anlegen und bei jedem gewünschten Verbraucher zuordnen. Die Knotenzuordnung allein erstellt keine Gruppenmitgliedschaft. Deaktivierte Verbraucher und deaktivierte Knotenunterstrukturen zählen nicht. Fehlt ein Mitgliedswert oder seine Historie, ist die Summe unbekannt bzw. unvollständig. [Berechnung und Grenzen](VERBRAUCHERGRUPPEN.md).
