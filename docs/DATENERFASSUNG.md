# Datenerfassung: ioBroker, MQTT und Modbus TCP

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

## ioBroker simple-api

### Voraussetzungen

ioBroker und sein **simple-api-Adapter** laufen bereits, der Adapter-Port ist vom Energieboard-Server erreichbar. Standard häufig 8087; nicht mit Admin-Port 8081 oder Web-Port 8082 verwechseln.

### Konfiguration

1. Verbindung mit Protokoll `iobroker`, Host z. B. `192.168.10.20`, Port `8087` anlegen.
2. „TLS / HTTPS“ nur bei einem tatsächlich per HTTPS bereitgestellten Adapter/Proxy aktivieren.
3. Messpunkt: die vollständige **Datenpunkt-ID** des Wertes eintragen, nicht den Anzeigenamen oder die Browser-URL.
4. Einheit und Faktor setzen, speichern, Wert mit ioBroker vergleichen.

Beispiel einer möglichen Objekt-ID: `alias.0.Energie.Netz.Leistung`. Die ID muss in deiner Installation existieren. Eine einheitliche Aliasstruktur in ioBroker kann spätere Quellenwechsel erleichtern.

HTTP-Anmeldedaten für simple-api werden vom aktuellen Verbindungsmodell nicht unterstützt. Einen erforderlichen Zugangsschutz passend zur eigenen Netzwerk-/Proxy-Lösung bereitstellen; nicht durch Eintragen von `benutzer:passwort@host` umgehen.

### Übernommene Altanlage

Alte direkte ioBroker-IDs mit globalem Host werden beim Start in eine Verbindung **„ioBroker (übernommen)“** und stabile Messpunkte überführt. Historische Schlüssel bleiben erhalten. Diese Verbindung danach unter Datenerfassung pflegen. Das globale ioBroker-Feld unter System bleibt für noch direkte Altzuordnungen relevant und ist keine zusätzliche Pflicht für neue Messpunkte.

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

Für 30–50 Geräte zuerst Namen/IDs und Einheiten planen, danach [CSV exportieren, bearbeiten und mit Vorschau importieren](../CSV-IMPORT.md). Verbindungskennwörter werden nicht mit exportiert. Änderungen von Faktor/Quelle gelten für neue Daten und rechnen die bestehende Historie nicht rückwirkend um.

[Weiter: Geräte und Knoten](GERAETE-UND-KNOTEN.md) · [Fehlersuche](FEHLERSUCHE.md).
