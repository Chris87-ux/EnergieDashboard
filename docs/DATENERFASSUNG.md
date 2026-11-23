# Datenerfassung: API, MQTT und Modbus TCP

[Dokumentationsübersicht](README.md) · [Erste Schritte](ERSTE-SCHRITTE.md) · [CSV für viele Messpunkte](../CSV-IMPORT.md)

## Prinzip: Quelle → Messpunkt → Gerät

Eine **Verbindung** beschreibt einen Server oder ein TCP-Gerät. Ein **Messpunkt** beschreibt genau einen Wert. Ein **Gerät/Knoten/Speicher** wählt passende Messpunkte aus; diese dürfen aus verschiedenen Verbindungen stammen.

Jeder Messpunkt besitzt eine stabile ID wie `point:werkstatt-leistung`. Das Gerät verweist darauf und nicht auf einen wechselnden Namen. Quelle, Name und Adresse können bei gleichbleibender ID geändert werden. Löschen und Neuanlegen erzeugt dagegen eine neue Identität. Der Editor übernimmt einen Messpunktnamen nur in einen noch leeren Gerätenamen.

## Gemeinsamer Ablauf

1. **Datenerfassung → Verbindung hinzufügen**: Name, Protokoll, Host/IP ohne URL-Präfix, Port und Aktiv setzen.
2. **Messpunkt hinzufügen**: Verbindung, sprechenden Namen, Adresse bzw. Register und Einheit festlegen.
3. Faktor und Offset prüfen: **Wert = Rohwert × Faktor + Offset**.
4. Speichern und unter **Messpunkte und Diagnose** Rohwert, Ergebnis und Empfang kontrollieren.
5. Unter **Konfiguration** den Wert dem passenden Feld des Geräts zuordnen.

„Bearbeiten“ öffnet das Formular direkt unter dem betroffenen Eintrag. Filter/Suche verwenden, um bei vielen Messpunkten den richtigen Eintrag zu finden.

| Quelle liefert | Messpunkt einstellen | Geräte-Einheit |
|---|---|---|
| 1500 W | W, Faktor 1 | W |
| 1.5 kW | kW, Faktor 1 | kW |
| 1500 W, gewünscht kW | kW, Faktor 0.001 | kW |
| 12500 Wh | Wh, Faktor 1 | Wh |
| SOC 725 mit Faktor 0.1 laut Hersteller | %, Faktor 0.1 → 72.5 % | SOC in % |
| Betriebsstunden in Sekunden | h, Faktor 1/3600 als Dezimalzahl | Stunden |

Skalierung nicht doppelt anwenden. `power_unit`/`energy_unit` im Gerät müssen der **normalisierten** Messpunkteinheit entsprechen. Bei der Auswahl erkennt der Editor unterstützte Leistungs-/Energieeinheiten; Ergebnis trotzdem kontrollieren.

## API / HTTP: gemeinsamer Adapter

Unter **Verbindung hinzufügen → Protokoll API / HTTP** eine Vorlage wählen. Sie setzt Vorschlagswerte, die anschließend frei geändert werden können. Host/IP ohne `http://` und ohne Port eintragen; Port separat setzen. TLS aktiviert HTTPS, dessen Zertifikat vertrauenswürdig sein muss. Vorlagen erzeugen keine Demoverbindungen und ersetzen keine Zugangsfreigabe auf dem Quellsystem.

| Vorlage | Portvorschlag | GET-Aufruf | Antwort-Basispfad | Antworttyp / Anmeldung |
|---|---:|---|---|---|
| Frei | 80 | `/{address}` | leer | Einzelwert / keine |
| ioBroker | 8087 | `/getBulk/{addresses}` | `val` | ioBroker Bulk / keine |
| Home Assistant | 8123 | `/api/states/{address}` | `state` | Einzelwert / Bearer |
| evcc | 7070 | `/api/state` | `result` | Einzelwert / keine |

**GET-Aufruf** ist eine konfigurierbare Pfadvorlage, kein Shellbefehl. `{address}` wird durch die URL-kodierte Adresse eines Messpunkts ersetzt. `{addresses}` fügt bis zu 40 Adressen für einen Bulk-Aufruf zusammen. Auch eine feste URL wie `/api/state` oder `/metrics/latest` ist möglich; gleiche URLs werden pro Erfassungsdurchlauf nur einmal abgerufen. Der Aufruf beginnt mit `/`; Host, Fragmente, beliebige Variablen und Skriptausdrücke gehören nicht hinein. Nur lesende Endpunkte verwenden. POST/PUT/Schreibzugriffe werden nicht unterstützt. HTTP-Weiterleitungen werden nicht automatisch verfolgt; den endgültigen Endpunkt konfigurieren.

Zuerst wird der **Antwort-Basispfad** der Verbindung angewendet, danach der **JSON-Pfad** des Messpunkts. Unterstützt sind Punktnotation (`data.power`), Array-Indizes ab 0 (`channels.0.power`) und bei API auch JSON Pointer (`/data/power`). Leere Pfade verwenden den aktuellen Wert selbst. Der resultierende Wert muss eine Zahl, ein numerischer String oder ein Boolwert sein; `on`/`off` werden als 1/0 gelesen. `unknown`, `unavailable`, fehlende Felder und nicht endliche Werte bleiben unbekannt und werden nicht zu 0.

### ioBroker simple-api

Voraussetzung ist ein erreichbarer simple-api-Adapter. Vorlage **ioBroker** wählen, Host und tatsächlichen Port setzen. Im Messpunkt unter Adresse die vollständige Datenpunkt-ID eintragen, etwa `alias.0.Energie.Netz.Leistung`. `json_path` bleibt bei der Standardvorlage leer.

Der bisher feste ioBroker-Befehl ist jetzt veränderbar:

| GET-Aufruf | Antworttyp | Basispfad |
|---|---|---|
| `/getBulk/{addresses}` | ioBroker Bulk | `val` |
| `/get/{address}` | Einzelwert | `val` |
| `/getPlainValue/{address}` | Einzelwert | leer |

Vorhandene ioBroker-Verbindungen werden beim Start mit unveränderten IDs auf API / HTTP und die ioBroker-Vorlage migriert. Auch direkte alte ioBroker-Zuordnungen behalten ihren historischen Bezug. Das globale ioBroker-Feld unter System bleibt nur für direkte Altzuordnungen relevant. Neue Quellen unter Datenerfassung pflegen.

### Home Assistant

1. Die REST-API muss vom Energieboard-Server erreichbar sein; Port des tatsächlichen HA-Servers oder Proxys prüfen.
2. Einen langlebigen Zugriffstoken in deinem Home-Assistant-Profil erstellen.
3. API-Vorlage **Home Assistant**, Host/Port und Token unter Bearer-Anmeldung eintragen. Den Wert ohne vorangestelltes `Bearer ` einfügen.
4. Messpunktadresse ist die Entity-ID, beispielsweise `sensor.netzleistung`. Bei der Vorlage wird deren `state` ausgewertet; Einheit und Faktor passend zum Sensor setzen.
5. Für ein numerisches Attribut statt `state` den Basispfad leeren und am Messpunkt z. B. `attributes.power` eintragen. Diesen Pfad gibt es nur, wenn die Entity ihn tatsächlich liefert.

### evcc

1. API-Vorlage **evcc** und tatsächlichen Host/Port setzen. Standardaufruf `/api/state`, Basispfad `result`.
2. Pro Messpunkt unter Adresse den relativen Wertpfad eintragen, z. B. `grid.power`, `pvPower` oder `loadpoints.0.chargePower`. Ohne zusätzlichen JSON-Pfad verwendet die Vorlage diese Adresse zum Auslesen des gemeinsamen Zustands.
3. Ein expliziter Messpunkt-JSON-Pfad hat Vorrang vor dem evcc-Adresspfad. Einheiten, Vorzeichen und vorhandene Felder anhand deiner API-Antwort prüfen.
4. Falls deine Instanz Anmeldung verlangt, passende Bearer- oder Header-Anmeldung konfigurieren. Die Vorlage ohne Anmeldung ist keine Zusicherung, dass deine Installation anonym erreichbar ist.

Die REST-Zustandsstruktur von evcc kann sich zwischen Versionen ändern; deshalb bleiben GET-Aufruf und Pfade frei bearbeitbar. Array-Indizes sind 0-basiert, unabhängig von der Nummerierung etwaiger MQTT-Topics.

### Freie API und Anmeldung

Beispiel: Der Server liefert unter `/meter/latest` `{"metrics":{"power":850.5}}`. Verbindung API / HTTP, Vorlage Frei, GET `/meter/latest`, Basispfad `metrics`; Messpunkt-JSON-Pfad `power`, Einheit W. Bei einer festen freien URL kann die Adresse leer bleiben. Bei Pfadvorlagen mit Variable ist sie erforderlich. Klartextantworten wie `850.5` funktionieren mit beiden Pfaden leer.

Anmeldungen: keine, HTTP Basic mit Benutzername/Passwort, Bearer-Token oder eigener Token-Header, z. B. `X-API-Key`. Benutzerdefinierte Header erhalten den Token unverändert. Token und Passwörter werden in normalen API-Antworten und CSV nicht ausgegeben. Ein beim Bearbeiten leeres Geheimnisfeld erhält den gespeicherten Wert; **Gespeicherten API-Token entfernen** löscht ihn ausdrücklich. MongoDB und vollständige Sicherungen enthalten Zugangsdaten und sind entsprechend zu schützen.

Offizielle Protokollreferenzen: [ioBroker simple-api](https://github.com/ioBroker/ioBroker.simple-api/blob/master/README.md), [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest/), [evcc REST API](https://docs.evcc.io/integrations/rest-api/), [evcc Zustandsstruktur](https://docs.evcc.io/en/reference/state/).

## MQTT

### Voraussetzungen

Ein vorhandener Broker, z. B. der eigene ioBroker-MQTT-Adapter oder Mosquitto, und regelmäßig publizierende Geräte. Energieboard installiert keinen Broker. Erforderliche Leserechte für die Topics müssen vorhanden sein.

### Einfacher Zahlenwert

1. Verbindung `mqtt` mit tatsächlichem Host/Port anlegen; häufig 1883 oder bei TLS 8883.
2. Bei Bedarf Benutzername/Passwort und TLS setzen. Das Serverzertifikat muss vertrauenswürdig sein; die Oberfläche bietet keinen eigenen Zertifikatsupload.
3. Messpunkt-Topic exakt setzen, z. B. `haus/werkstatt/leistung`.
4. Payload z. B. `850.5`, JSON-Pfad leer, Einheit W, Faktor 1.
5. MQTT-Gültigkeit passend zum Veröffentlichungsintervall einstellen und Diagnose prüfen.

Es werden **keine Topic-Wildcards** wie `+` oder `#` unterstützt. RUN-Payload darf `true`/`false` oder 1/0 sein.

### JSON-Payload aufteilen

Topic `haus/technik/werte`, Payload:

```json
{"data":{"power":850.5,"soc":72,"channels":[100,200]}}
```

| Messpunkt | JSON-Pfad | Einheit |
|---|---|---|
| Leistung | `data.power` | W |
| SOC | `data.soc` | % |
| Zweiter Kanal | `data.channels.1` | nach Quelle |

Mehrere Messpunkte können dasselbe Topic mit verschiedenen Pfaden verwenden. Punktnotation und numerische Array-Indizes sind unterstützt; keine JavaScript-Ausdrücke, JSONPath-Filter oder Schlüssel mit Punkten.

### Gültigkeit und gespeicherte Nachrichten

`stale_s` zählt ab **Empfang** durch Energieboard. Bei einem Publisher alle 10 Sekunden sind etwa 30–60 Sekunden ein möglicher Startwert; an die tatsächliche Quelle anpassen. Nach Ablauf oder erkanntem Verbindungsabbruch ist der Wert nicht verfügbar. Ein nur bei Änderungen sendender Publisher kann deshalb auch bei konstantem Betrieb veralten; regelmäßiges Senden/Heartbeat einrichten.

Retained-Nachrichten werden in der Diagnose gekennzeichnet. Ihr ursprüngliches Messalter ist ohne ausgewerteten Publisher-Zeitstempel unbekannt. Gerätespezifische LWT-Topics und externe Payload-Zeitstempel wertet Energieboard derzeit nicht gesondert aus. Ein frisch empfangener Retained-Wert ist deshalb kein Nachweis für ein laufendes Endgerät.

## Modbus TCP

### Voraussetzungen

Modbus TCP am Gerät/Gateway freischalten, Server-IP/Port und **Hersteller-Registertabelle** bereitlegen. Unterstützt sind reine Lesezugriffe über TCP; kein serielles RTU und keine Schreibbefehle.

### Schritt für Schritt

1. Verbindung `modbus`, Geräte-IP, tatsächlichen TCP-Port (häufig 502) und Timeout setzen.
2. Messpunkt anlegen und Unit-ID des Zielgeräts wählen. Bei Gateways kann eine andere Unit-ID als 1 nötig sein.
3. Registeradresse **0-basiert** eintragen. Eine Handbuchangabe `40001` kann Adresse 0 mit FC03 bedeuten; Herstellerkonvention prüfen, nicht pauschal 40000 abziehen.
4. Funktion 3 (Holding Register) oder 4 (Input Register), Datentyp, Byte- und Wortreihenfolge wählen.
5. Faktor, Offset und Einheit aus dem Handbuch übernehmen.
6. Zuerst einen bekannten plausiblen Messwert lesen, dann weitere Register hinzufügen.

| Datentyp | Registerzahl | Verwendung |
|---|---|---|
| `uint16` / `int16` | 1 | Ganzzahl ohne/mit Vorzeichen |
| `uint32` / `int32` | 2 | Größere Ganzzahl ohne/mit Vorzeichen |
| `float32` | 2 | 32-Bit-Gleitkomma |
| `float64` | 4 | 64-Bit-Gleitkomma |

Für negative Netz-/Batterieleistung einen **vorzeichenfähigen** Datentyp verwenden. Extrem große Zahlen oder ständig unplausible Werte sprechen häufig für falschen Typ, Registerbasis, Faktor oder Reihenfolge. Victron-Register hängen u. a. vom Gerät und der Unit-ID ab; Beispielregister im [Datenmodell](../DATENMODELL.md) sind keine universelle Gerätevorgabe.

Pro Verbindung werden Register nacheinander gelesen. Viele langsame oder nicht antwortende Register können einen gesamten Erfassungsdurchlauf verlängern. Timeouts und Polling an das Gerät anpassen.

## Aufzeichnung und viele Datenpunkte

„Rohwert aufzeichnen“ speichert den **normalisierten** Messpunktwert bei aktivem Recorder lokal. Der Recorder muss zusätzlich unter System eingeschaltet sein. Abgeleitete RUN-, Knotenrest-, Netz-, Hybrid- und Speicherkanäle werden für ihre Energieauswertung ebenfalls aufgezeichnet.

Für 30–50 Geräte zuerst Namen/IDs und Einheiten planen, danach [CSV exportieren, bearbeiten und mit Vorschau importieren](../CSV-IMPORT.md). Verbindungskennwörter und API-Tokens werden nicht mit exportiert. Änderungen von Faktor/Quelle gelten für neue Daten und rechnen die bestehende Historie nicht rückwirkend um.

[Weiter: Geräte und Knoten](GERAETE-UND-KNOTEN.md) · [Fehlersuche](FEHLERSUCHE.md).
