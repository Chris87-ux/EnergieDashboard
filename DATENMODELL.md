# Datenmodell und Erweiterungen · Version 2.3.0

## DC-MPPT und Hybrid-WR ab 2.3 (Schema 5)

**DC-MPPT:** `kind: "device"`, `category: "pv"`, `pv_type: "mppt"`. Die Anwendung setzt die Messebene auf DC und verwendet keine Phasen. `datapoints.power_total` misst die **DC-Ausgangsleistung des MPPT zum gemeinsamen DC-Bus**, nicht die PV-Eingangsleistung vor dem MPPT. `power_unit` ist W oder kW. `datapoints.energy_total` ist der optionale kumulative DC-Energiezähler dieses Ausgangs, mit `energy_unit` Wh oder kWh. Er wird live als Gesamtenergie angezeigt und für Zeiträume als Zählerdelta ausgewertet; ohne Zähler verwendet die Historie aufgezeichnete Leistung. RUN, Frequenz und alte Phasenzuordnungen werden dafür nicht verwendet. DC-MPPT-Zeilen erscheinen separat in der Energieauswertung und gehen nicht nochmals in die AC-Gesamtsumme ein.

**Hybrid-WR:** Zuerst DC-Speicher (jeweils gesamter Speicher mit Kapazität, SOC und vorzeichenbehafteter Leistung) sowie DC-MPPTs anlegen; anschließend im Hybrid auswählen. Jeder Eintrag gehört höchstens zu einem Hybrid-WR. Knoten bleiben AC-Abschnitte; DC-Geräte/Speicher können organisatorisch einem Knoten zugeordnet sein, ohne dessen AC-Restbilanz zu verfälschen. Der Hybrid-WR gehört zum AC-Knoten seines tatsächlichen AC-Anschlusses. Seine zugeordnete Batterie darf keine AC-Batterie sein.

Für die **AC-Messgrenze** stehen zwei Modi zur Verfügung:

| Feld | Bedeutung |
|---|---|
| `hybrid_ac_mode: "net"` | Standard, bisheriges Verhalten: `power_total` oder die Summe dreier Phasen ist bereits die bidirektionale Nettoleistung des Wandlers. Positiv = DC → AC, negativ = AC → DC. |
| `hybrid_ac_mode: "terminals"` | `power_total`/Phasen sind AC-Out; `datapoints.ac_input` ist die Gesamtleistung am AC-In desselben WR. Netto = AC-Out − AC-In. Beide Messgrenzen in derselben Einheit `power_unit`. Positiv an AC-In = in den WR, positiv an AC-Out = aus dem WR; Rückflusswerte bleiben negativ. `invert` kehrt beide AC-Messwerte um. |

Beispiel Durchleitung: AC-Out 2.950 W und AC-In 2.000 W ergeben **950 W Wandlerabgabe**, nicht 2.950 W PV-Erzeugung. Ein Haus-Netzzähler an anderer Messgrenze ersetzt AC-In nicht. Der Wandler muss bei Netzladung negative Nettoleistung liefern. AC-Netto wird in getrennten Abgabe-/Aufnahmekanälen aufgezeichnet. Aus einem gesamten AC-In lässt sich keine zuverlässige Nettoleistung je Phase ableiten; abgeleitete Energiekanäle zeigen daher Gesamtenergie ohne erfundene Phasenzuordnung. Netzbezug und Hybridaufnahme sind unterschiedliche Messgrenzen; wie bisher sind die tabellarischen Zufluss-/Abflusssummen keine deduplizierte Haus-PV-Ertragsmessung.

Für den **WR-Wirkungsgrad** bestehen zwei Möglichkeiten:

1. Bevorzugt `datapoints.dc_power`: tatsächliche vorzeichenbehaftete DC-Leistung **am Wandler**, positiv DC → AC, negativ AC → DC. `dc_power_unit` W/kW, `dc_invert` kehrt das Vorzeichen um. Keine alleinige Batterie- oder MPPT-Leistung einsetzen. Diese Messung hat Vorrang; fehlt ihr Wert, wird keine andere Quelle stillschweigend verwendet.
2. Ohne direkte Messung ausdrücklich `dc_balance_complete: true` bestätigen. Dann entsteht eine gekennzeichnete **Schätzung**: DC am WR = Summe MPPT-Ausgänge + Batterieentladung − Batterieladung − weitere DC-Lasten. Letztere sind optional über `datapoints.dc_load_power` mit derselben `dc_power_unit` messbar. Alle beteiligten Quellen, Speicher und Lasten am DC-Bus müssen vollständig und zeitgleich erfasst sein. Fehlt eine konfigurierte Quelle, bleibt die Schätzung unbekannt.

Bei DC → AC gilt η = AC-netto / DC-netto × 100; beim Laden AC → DC gilt η = Betrag(DC-netto) / Betrag(AC-netto) × 100. Beispiel: PV 2.000 W, Batterieladung 1.000 W, keine weiteren DC-Lasten, AC-netto 950 W → DC am WR 1.000 W, η 95 %. Netzladung AC-netto −1.000 W, Batterie lädt 900 W und PV 0 W → η 90 %. Verlustleistung = Wandlereingang − Wandlerausgang.

`hybrid_min_power_w` (Standard 100 W, muss >0 sein) muss auf beiden Wandlerseiten erreicht sein. Kleine Leistung, fehlende Werte, widersprüchliche Vorzeichen oder rechnerische Werte über 100 % ergeben **keinen Wirkungsgrad**, sondern einen Hinweis. Rein DC-seitiges PV→Batterie-Laden bei ruhendem AC-Wandler ergibt keinen AC-Wirkungsgrad. MPPT- und Batteriewirkungsgrad sind darin nicht enthalten. Ein systemseitig bereits berechneter DC-Wert ergibt keine unabhängige Wirkungsgradmessung; unterschiedliche Messzeitpunkte und Auflösung können die Anzeige unplausibel machen. Das Panel zeigt Quelle und Betriebsrichtung.

Victron trennt AC-In, AC-Out und DC-Werte ebenfalls; konkrete Quellen/Skalierung je Gerät anhand der eigenen Installation prüfen, siehe [Victron dbus-systemcalc](https://github.com/victronenergy/dbus-systemcalc-py). Energieboard liest nur und steuert den WR nicht.

Bestehende IDs, Messpunkte, Historie und Einstellungen bleiben beim Update erhalten. Vorhandene MPPTs werden automatisch auf DC/Gesamtwerte normalisiert, alte Phasenfelder bleiben gespeichert und werden ignoriert. Bestehende Hybrid-WR bleiben im Modus `net`; bei bisher zugeordnetem AC-Out bitte bewusst auf `terminals` umstellen und AC-In ergänzen. Eine irrtümlich als AC konfigurierte verknüpfte Batterie muss über Entfernen der Verknüpfung, Korrektur der Messebene und erneute Verknüpfung korrigiert werden. Vorher aufgezeichnete falsche Hybrid-Nettohistorie wird nicht rückwirkend berechnet.

## Vorzeichen und Anzeige ab 2.2

Normale Geräte bewahren das Messvorzeichen in der Anzeige, einschließlich negativer PV-/Generatorwerte und nichtnulliger Werte unter 1 W. Für die Bilanz bestimmt die konfigurierte Richtung die Rolle: Verbrauch nutzt den Betrag als Abfluss, Erzeugung den Betrag als Zufluss. `invert` ändert das dargestellte Quellvorzeichen, nicht diese feste Rolle. Die Leistungsintegration normaler Geräte nutzt ebenfalls den Betrag. Echte bidirektionale Messstellen weiterhin als Netzanschluss oder Hybrid-WR einrichten. Ein normaler Erzeuger ist kein bidirektionaler Wechselrichter.

Die Standardschwelle blendet nur Werte **größer als -1 W und kleiner als +1 W** nach 60 Sekunden aus. Genau -1 W/+1 W und größere Beträge bleiben sichtbar. Netzkanäle sind ausdrücklich vom Filter ausgenommen. Bezug und Lieferung stehen gemeinsam in einer permanenten Netzkachel oben mittig; doppelte Netz-Gerätekarten entfallen. Bereits mit der alten falschen Nullbegrenzung aufgezeichnete abgeleitete Knotenreste werden nicht rückwirkend neu berechnet. Erhaltene rohe negative Leistungshistorie normaler Geräte kann dagegen jetzt korrekt als Erzeugungsbetrag integriert werden.

Die Anwendung ist zusätzlich mit Docker Compose betreibbar. Datenmodell und Datenbankformat entsprechen der LXC-Installation; siehe [DOCKER.md](DOCKER.md).

## Neuerungen in 2.1

CSV-Export/-Import mit Vorschau und stabilen IDs ist in [CSV-IMPORT.md](CSV-IMPORT.md) beschrieben. Beim Bearbeiten eines Messpunkts oder einer Verbindung erscheint das Formular unter der betreffenden Zeile. Kleine `sort_order`-Werte stehen zuerst; diese Anzeigereihenfolge beeinflusst keine Bilanz.

`kind: "grid"` bezeichnet den Netzanschluss. Alte Grid-Geräte werden ohne neue IDs übernommen. Netzanschluss und Speicher sind eigene Typen und keine auswählbaren Gerätekategorien. Diese Typen verwenden in ihrer gespeicherten Konfiguration die neutrale Kategorie `custom`; intern erzeugte Bezug-/Einspeise- und Speicherkanäle besitzen weiterhin entsprechende Kennzeichnungen für die Bilanz. Generatoren sind Geräte mit `category: "generator"`.

Generator-Messpunkte: `engine_temperature` in °C, `efficiency` in %, `fuel_consumption` in der unter `fuel_unit` gewählten Einheit (L/h, L, m³/h, m³, kg/h, kg), `operating_hours` in Stunden. Es handelt sich um optionale Messwerte. Energieboard berechnet daraus keine eigene Effizienz oder Kraftstoffmenge. Sekundenwerte können im Messpunkt mit Faktor 1/3600 in Stunden umgerechnet werden.

Speicher unterstützen `electrical_side: "dc"` oder `"ac"`. Bei DC gibt es keine Phasenzuordnung; notwendig sind die gesamte vorzeichenbehaftete Leistung und SOC. Bei AC sind Gesamtleistung oder vollständige dreiphasige Leistungswerte möglich. Die Speicheranzeige bleibt separat. In `datapoints.soc_reserve` kann ein Reservewert in Prozent zugeordnet werden. Ein konfigurierter Reserve-Datenpunkt ersetzt den festen Wert; bei fehlendem/ungültigem Datenpunkt bleibt die Laufzeit unbekannt. Ohne Datenpunkt gilt weiterhin `reserve_soc_pct`.

Die Diagrammansicht zeigt pro Ebene direkt angeschlossene Geräte und rechteckige Unterknoten. Knoten öffnen ihre Kinder, die Pfadleiste führt zurück. Pro Diagrammseite werden bis zu vier Elemente je Richtung angezeigt; weitere Elemente einer Ebene folgen auf weiteren Seiten. Die Bilanz bezieht sich immer auf die vollständige Anlage.

`appearance.zero_threshold_w` (Standard 1 W) und `appearance.zero_delay_s` (Standard 60 s) steuern den Livefilter. Unterhalb der Schwelle verschwindet ein Gerät nach der Frist aus Diagramm und Livekarten. Schwelle 0 zählt ausschließlich exakt 0 W. Neue Leistung macht es sofort wieder sichtbar. Unbekannte Messwerte setzen die Nullfrist zurück. Bei Beobachtungslücken über höchstens 30 Sekunden beginnt die Frist neu. Der Server speichert den Zustand in `visibility`, sodass ein Browser-Neuladen die Frist nicht zurücksetzt. Knotenstruktur, Speicher/SOC, Netz-Kennzahlen, Konfiguration, Historie und Bilanz bleiben sichtbar bzw. unverändert. „Inaktive anzeigen“ hebt den Darstellungsfilter auf.

## Aufbau

Verbindung → Messpunkt → Gerät / Knoten / Speicher → Darstellung und Historie.

Verbindungen und Messpunkte werden im Reiter **Datenerfassung** angelegt. Die Auswahl in der Gerätekonfiguration zeigt Namen und Einheit. Der gespeicherte Verweis lautet `point:<id>`. Diese ID bleibt beim Bearbeiten der Quelle gleich. Namen werden beim erstmaligen Zuordnen in einen noch leeren Gerätenamen übernommen. Änderungen am Messpunktnamen überschreiben anschließend keine selbst vergebenen Gerätenamen.

Alle Protokolladapter lesen ausschließlich Werte. Energieboard schaltet oder regelt keine Geräte.

## Verbindungen

API `GET /api/connections`, `PUT /api/connections/<id>`, `DELETE /api/connections/<id>`.

```json
{
  "name": "Victron GX",
  "protocol": "modbus",
  "host": "192.168.10.20",
  "port": 502,
  "enabled": true,
  "timeout_s": 5
}
```

`protocol` ist `iobroker`, `mqtt` oder `modbus`. MQTT unterstützt `username`, `password` und `tls`. Standardports sind 8087, 1883 und 502; bei MQTT/TLS den tatsächlichen TLS-Port, häufig 8883, einstellen. Der MQTT-Broker muss bereits vorhanden sein. Für HTTPS verwendet ioBroker `tls: true`. Direkte ioBroker-simple-api-Verbindungen unterstützen in dieser Version keine HTTP-Anmeldedaten. Host enthält ausschließlich IP/Hostname, ohne Protokoll und Port.

Passwörter werden serverseitig gespeichert und in Antworten leer zurückgegeben. `password_set` zeigt ein hinterlegtes Passwort an. Ein leeres Passwort beim Speichern erhält das vorhandene Passwort. Zum vollständigen Entfernen einer Verbindung zunächst ihre Messpunkte verschieben oder löschen. Die Datenbank und Sicherungen enthalten Zugangsdaten; den Zugriff entsprechend begrenzen.

## Messpunkte

Schema mit Typen, Pflichtfeldern und Grenzen unter `GET /api/schemas/measurement`. Verwaltung über `GET /api/measurements`, `PUT /api/measurements/<id>` und `DELETE /api/measurements/<id>`. Diagnose unter `GET /api/measurements/live`.

Gemeinsame Felder:

| Feld | Bedeutung |
|---|---|
| `name` | Anzeigename, 1–100 Zeichen |
| `connection_id` | ID einer vorhandenen Verbindung |
| `unit` | Einheit nach Umrechnung, z. B. W, kW, kWh, %, bool, °C |
| `scale`, `offset` | Wert = Rohwert × Faktor + Offset |
| `enabled` | Messpunkt aktiv |
| `record` | Normalisierten Rohwert lokal aufzeichnen |
| `stale_s` | Gültigkeit einer empfangenen MQTT-Nachricht, 5–86400 Sekunden |
| `history_key` | Vom Server verwalteter Verweis auf übernommene Historie |

Die Einheit des Gerätes muss zur Einheit des Messpunktes passen. Bei Auswahl eines Leistungs-/Energiepunktes mit W/kW bzw. Wh/kWh übernimmt der Editor die Einheit. Skalierung und Geräteumrechnung nicht versehentlich doppelt anwenden. Beispiel: Ein Messgerät liefert 1234 in W; entweder W und Faktor 1 oder kW und Faktor 0.001 verwenden.

Der Recorder speichert normalisierte Werte. Änderungen von Faktor, Offset oder Quelle gelten für künftig aufgezeichnete Daten. Bereits gespeicherte Werte werden nicht rückwirkend umgerechnet. Abgeleitete RUN-, Rest-, Netz- und Speicherkanäle werden bei aktivem Recorder zusätzlich aufgezeichnet, auch wenn deren Rohwertaufzeichnung ausgeschaltet ist.

### MQTT-Zahlenwert

```json
{
  "name": "Werkstatt Leistung",
  "connection_id": "VERBINDUNGS-ID",
  "address": "haus/werkstatt/power",
  "unit": "W",
  "scale": 1,
  "offset": 0,
  "stale_s": 120
}
```

Payload z. B. `850.5`. Für RUN sind `true`, `false`, `1`, `0` möglich. Topic exakt angeben; Wildcards werden nicht unterstützt. Ein Topic kann mehreren Messpunkten mit unterschiedlichen JSON-Pfaden zugeordnet werden.

### MQTT-JSON

Payload:

```json
{"data":{"power":850.5,"soc":72,"channels":[100,200]}}
```

Für Leistung `json_path: "data.power"`, für SOC `"data.soc"`, für den zweiten Kanal `"data.channels.1"`. Leerer Pfad erwartet einen einfachen Zahlen-/Boolwert. Pfade verwenden Punkte als Trenner; Schlüsselnamen mit Punkten und beliebige Ausdrücke werden nicht unterstützt. Fehlerhafte, fehlende oder nicht endliche Werte werden als nicht verfügbar markiert.

MQTT verwendet QoS 1 für Subscriptions. Eine gespeicherte Nachricht wird in der Diagnose als solche gekennzeichnet. Ihr ursprüngliches Messalter ist ohne Zeitstempel im Publisher-Protokoll unbekannt; die Gültigkeit zählt ab Empfang. Nach Ablauf von `stale_s` oder nach einem Verbindungsabbruch wird kein aktueller Wert angezeigt. Für zuverlässig erkannte Geräteausfälle regelmäßig publizieren und eine passende Gültigkeit wählen. Externe Publisher-Zeitstempel und individuelle LWT-Verfügbarkeitstopics werden in dieser Version noch nicht ausgewertet.

### Modbus TCP

```json
{
  "name": "Wechselrichter AC-Leistung",
  "connection_id": "VERBINDUNGS-ID",
  "unit_id": 100,
  "register": 820,
  "function": 3,
  "datatype": "int16",
  "byte_order": "big",
  "word_order": "big",
  "scale": 1,
  "offset": 0,
  "unit": "W"
}
```

Die Zahlen sind ein Strukturbeispiel. Register und Skalierung immer aus der Dokumentation des konkreten Gerätes übernehmen; dieses Beispiel ist keine universelle Victron-Zuordnung.

Registeradressen sind **0-basiert**, keine 4xxxx-Referenznummern. Bei Handbuchangabe 40001 kann deshalb Adresse 0 gemeint sein; die Herstellerkonvention prüfen. Unterstützt werden FC03 Holding Register und FC04 Input Register sowie uint16, int16, uint32, int32, float32 und float64. Größere Typen lesen entsprechend mehrere aufeinanderfolgende Register. Byte- und Wortreihenfolge sind separat einstellbar. TCP-Verbindungen werden pro Erfassungsdurchlauf geöffnet; Register werden je Verbindung nacheinander abgefragt. RS485/RTU und Schreibfunktionen sind nicht enthalten.

### ioBroker

`address` ist die vollständige Objekt-ID des simple-api-Datenpunktes. Neue Messpunkte benötigen keinen globalen ioBroker-Host unter System. Direkte alte Datenpunkt-IDs werden aus Kompatibilitätsgründen weiterhin unterstützt; dafür gilt der globale Host.

Beim ersten Start der neuen Version werden bestehende direkte Zuordnungen mit konfiguriertem ioBroker-Host automatisch in Messpunkte übernommen. Die Verbindung heißt „ioBroker (übernommen)“. Deren Verbindungsdaten danach unter **Datenerfassung** pflegen. IDs und historische Schlüssel bleiben erhalten. Übernommene InfluxDB-Historie bleibt zugänglich. Neu angelegte Messpunkte verwenden zunächst die lokale MongoDB-Historie; freie Influx-Measurement-Zuordnungen sind noch kein Eingabefeld.

## Geräte, Netzanschluss und Knoten

Vollständiges Schema unter `GET /api/schemas/flow`. Geräteverwaltung über `/api/flows`. `id`, `schema_version` und `created_at` werden vom Server verwaltet. Konfigurationsobjekte enthalten u. a. `kind`, `name`, `category`, `direction`, `parent_id`, `datapoints`, Einheiten und Darstellungsfelder.

Ein Netzanschluss auf der Hauptebene ist für ein eingerichtetes Board erforderlich. Ohne ihn zeigt die Oberfläche einen Einrichtungshinweis. Ein eingerichteter letzter Netzanschluss lässt sich erst nach Anlegen eines Ersatzes deaktivieren/löschen.

Für **einen vorzeichenbehafteten Netzleistungswert** `kind: "grid"` und `grid_mode: "signed"` wählen. Positiv ist Bezug, negativ Einspeisung; `invert` kehrt die Quelle um. Optionale kumulative Energiezähler werden unter `datapoints.energy_import` und `datapoints.energy_export` zugeordnet. Für **getrennte Leistungswerte** zwei Einträge vom Typ Netzanschluss mit `grid_mode: "directional"`, einmal `direction: "in"` und einmal `"out"`, anlegen. Jeder Richtungswert muss nach Vorzeichenumkehr positiv sein. Beide Modelle dürfen nicht gleichzeitig für denselben Netzanschluss aktiv sein.

Knoten können andere Knoten enthalten. Kreiszuordnungen werden abgewiesen. AC-Abschnittszähler messen positiv Verbrauch und negativ Erzeugung. DC-Geräte dürfen zur Orientierung einem Knoten zugeordnet werden, bleiben in der AC-Verrechnung separat.

```text
Rest = Abschnittszähler − direkte Verbraucher + direkte Erzeuger − Unterabschnitte netto
```

Ein gemessener Unterknoten geht mit seinem Zählerwert ein. Bei einem ungemessenen Unterknoten wird die Summe seines Abschnitts verwendet. Jeder gemessene Knoten erzeugt zwei stabile historische Restkanäle für Verbrauch und Erzeugung. Live ist jeweils der zum Vorzeichen passende Kanal aktiv; der andere ist null. Ohne Kinder entspricht der Rest dem gesamten Zählerwert. Fehlende Kinder-/Zählerwerte ergeben einen nicht verfügbaren Rest. Speicher und DC-MPPTs werden dabei nicht abgezogen.

Der Rest enthält ungemessene Geräte, zeitliche Messabweichungen und Verluste. Es ist keine automatische Fehlerkorrektur. Phasen des Abschnittszählers sind separat sichtbar. Die automatische Restenergie wird als Gesamtwert aus aufgezeichneter Restleistung integriert; sie ist keine vollständig phasenaufgelöste Differenzbilanz.

Deaktivierte Knoten deaktivieren ihre gesamte Unterstruktur für Anzeige und Aufzeichnung. Vor dem Löschen müssen Kinder verschoben werden. Änderungen der Zuordnung ändern den aktuellen Aufbau; eine historische Rekonstruktion früherer Topologien ist noch nicht enthalten. Bereits aufgezeichnete Restkanäle werden dabei nicht neu berechnet.

RUN-Geräte verwenden `datapoints.run` und `run_power_w`. Ungleich null/true bedeutet Betrieb. Die aufgezeichnete geschätzte Leistung wird zeitlich integriert; unbekannte Signale gelten nicht als aus. RUN-Historie beginnt mit der Aufzeichnung.

## PV, Hybrid-WR und Speicher

Bei Kategorie Photovoltaik stehen `pv_type: "wr"`, `"hybrid"` und `"mppt"` zur Verfügung. Ein normaler WR liefert einen richtungsbezogenen AC-Erzeugungswert. Ein Hybrid-WR verwendet einen vorzeichenbehafteten AC-Wert: positiv AC-Abgabe, negativ AC-Aufnahme. Bei abweichendem Quellvorzeichen `invert` verwenden. Damit wird auch Laden aus dem AC-Netz erfasst.

Ein Hybrid-WR kann zuvor angelegte Speicher über `storage_ids` und DC-MPPTs über `mppt_ids` auswählen. Die Oberfläche verlangt beim Anlegen eines Hybrid-WR einen Speicher. Ein Speicher/MPPT kann jeweils einem Hybrid-WR zugeordnet sein. Das Modell bildet vollständige Speicher ab, keine einzelnen Batteriemodule.

DC-Geräte haben `electrical_side: "dc"`; MPPTs bleiben unabhängig davon außerhalb der AC-Summen. Speicher erscheinen ausschließlich im separaten Speicherbereich. Ihre Knotenzuordnung ist eine Zuordnung zur Orientierung und kein zusätzlicher AC-Bilanzfluss.

Speicherfelder:

| Feld | Bedeutung |
|---|---|
| `capacity_kwh` | Feste Gesamtkapazität; neue Speicher benötigen diese Angabe im Editor |
| `reserve_soc_pct` | SOC-Untergrenze für die Restlaufzeit, Standard 0 % |
| `charge_sign` | `positive` oder `negative`: Vorzeichen der Quelle beim Laden |
| `max_power_w` | Skalenmaximum des Leistungsbalkens; Standard 5000 W |
| `datapoints.power_total` | Leistung mit Vorzeichen |
| `datapoints.soc` | SOC in Prozent zwischen 0 und 100 |

Restenergie = Kapazität × SOC / 100. Nutzbare Energie = Kapazität × max(SOC − Reserve, 0) / 100. Ab zwei Speichern erscheint ein gemeinsamer Speicher mit kapazitätsgewichtetem SOC. Fehlende Kapazitäten/SOCs machen den Gesamt-SOC unverfügbar; fehlende Leistungen machen die Gesamtleistung unverfügbar. Gleichzeitiges Laden und Entladen verschiedener Speicher wird für den gemeinsamen Balken saldiert, die Einzelanzeigen bleiben sichtbar.

Die Restlaufzeit nutzt ein zeitabhängiges exponentielles 5-Minuten-Mittel der vorzeichenbehafteten Leistung und die bis Reserve nutzbare Energie. Sie erscheint nur bei aktueller und geglätteter Entladung über 50 W. Nach Datenlücken über 120 s oder einem Serverneustart beginnt die Glättung neu. Der erste Wert basiert auf der ersten verfügbaren Leistung. Der Gesamtspeicher verwendet seine saldierte geglättete Leistung. Laufzeit und Energieinhalt sind rechnerische Schätzungen ohne Alterungs-, Temperatur- oder Verlustmodell.

AC-Leistung eines Hybrid-WR enthält ggf. Batterieentladung. Deshalb zeigt Energieboard bei aktiven Hybrid-WR keinen daraus abgeleiteten PV-Erzeugungs-/Eigenverbrauchswert. MPPT-Leistungen erscheinen separat als DC-Werte. Netzbezug und Einspeisung bleiben direkt messbar; Autarkie bezieht sich auf den erfassten AC-Verbrauch. Ohne vollständige Verbraucher-/Restmessung sind diese Kennzahlen entsprechend nur auf den erfassten Umfang bezogen.

Speicher-Lade-/Entladeenergie wird separat aufgezeichnet und in der Energietabelle gezeigt; sie wird nicht zu AC-Gesamtsummen addiert.

## Das Feld „Zusätzliche Felder (JSON)“

Dieses Feld ist für Metadaten gedacht. Inhalt ist ein JSON-Objekt, maximal 16 KiB, mit gültigen JSON-Werten. Beispiel zum direkten Einfügen:

```json
{
  "manufacturer": "Victron",
  "location": "Technikraum",
  "notes": "DC-Speicher am Hybrid-Wechselrichter",
  "tags": ["speicher", "technikraum"],
  "custom": {
    "inventory_number": "BAT-01",
    "commissioned": "2026-11-20"
  }
}
```

Zeichenketten und Schlüssel benötigen doppelte Anführungszeichen. Kommentare, nachgestellte Kommas, NaN/Infinity und JavaScript-Ausdrücke sind ungültig. In einer vollständigen API-Konfiguration steht dieses Objekt unter dem Schlüssel `extra`.

Die Metadaten werden gespeichert und von der API zurückgegeben. Sie führen keinen Code aus und verändern keine Berechnung. Kapazität, Vorzeichen, Datenpunktzuordnung und Hybrid-Zuordnungen werden in den dafür vorgesehenen regulären Feldern eingestellt. Früher in `extra.capacity_kwh` eingetragene Werte müssen einmal in das reguläre Kapazitätsfeld übernommen werden. Beliebige Formeln und benutzerdefinierte Programmausführung sind nicht vorgesehen.

## Versionierung

Anwendungsversion in `VERSION`; Datenbankschema aktuell Version 4. Additive Migrationen laufen beim Start und dürfen mehrfach ausgeführt werden. Ein neueres Datenbankschema wird von dieser Version abgewiesen. Ein Downgrade erfolgt zusammen mit der dazugehörigen Datenbanksicherung. Messpunkt- und Geräte-IDs bleiben bei Updates erhalten.
