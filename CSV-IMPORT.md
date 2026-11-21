# CSV-Konfiguration · Energieboard 2.3.0

[Dokumentationsübersicht](docs/README.md) · [Datenerfassung](docs/DATENERFASSUNG.md) · [Vollständige Sicherung](docs/BETRIEB-UND-UPDATES.md)

Stand: 21. November 2026. CSV-Format **1**, unabhängig von Anwendung 2.3.0 und Datenbankschema 5.

## Inhalt

- [Export und Vorlage](#export-und-vorlage)
- [Typische Bearbeitung](#typische-bearbeitung)
- [Neue Modbus-Messpunkte](#beispiel-für-neue-modbus-messpunkte)
- [Neue MQTT-Messpunkte](#beispiel-für-mqtt-messpunkte)
- [Spalten und Datensatztypen](#spalten-und-datensatztypen)
- [Vollständiges Ersetzen](#vollständiges-ersetzen)
- [Zugangsdaten und Tabellenformeln](#zugangsdaten-und-tabellenformeln)
- [Hybrid-/MPPT-Felder](#hybrid-mppt-felder-ab-23)

Im Reiter **Datenerfassung** und unter **Konfiguration** den Abschnitt „Konfiguration als CSV herunterladen / hochladen“ öffnen.

## Export und Vorlage

- **Gesamtkonfiguration CSV** enthält Verbindungen, Messpunkte, Geräte, Knoten, Speicher und Systemeinstellungen einschließlich Darstellung.
- **Messpunkte CSV** enthält nur die Messpunkte und deren benötigte Spalten. Diesen Export zum Bearbeiten vieler Register/Topics verwenden.
- **Verbindungen CSV** enthält die Verbindungseinstellungen ohne Kennwörter.
- **Messpunkt-Vorlage** enthält die Spaltenüberschriften für neue Messpunkte.

Die Messhistorie wird nicht exportiert. Für eine vollständige Sicherung einschließlich Historie weiterhin das Datenbank-/LXC-Backup verwenden.

Dateiformat ist CSV-Version 1, UTF-8 mit BOM und Semikolon als Trennzeichen. Excel/LibreOffice beim Öffnen ggf. ausdrücklich auf UTF-8, Trennzeichen Semikolon und Textformat für IDs, Topics und Registerbezeichnungen einstellen. Zahlen verwenden einen Dezimalpunkt; keine Tausendertrennzeichen. Einheiten wie W oder kWh stehen in der Spalte `unit`, nicht direkt am Zahlenwert. IDs dürfen nicht durch die Tabellenkalkulation in Zahlen oder Datumswerte umgewandelt werden.

## Typische Bearbeitung

1. Vor Änderungen die Gesamtkonfiguration herunterladen und aufbewahren.
2. Messpunkte CSV herunterladen und in der Tabellenkalkulation bearbeiten.
3. Bestehende `id` unverändert lassen. Namen, Register, Skalierung oder Quellen dürfen geändert werden, ohne Geräte neu zuzuordnen.
4. Für neue Messpunkte eine neue eindeutige ID vergeben, z. B. `victron-ac-power`. Zulässig sind Buchstaben, Ziffern, `-`, `_`, `.`, `:` und maximal 100 Zeichen. IDs dürfen innerhalb eines Datensatztyps nicht doppelt vorkommen.
5. Als UTF-8-CSV mit Semikolon speichern.
6. Datei im Board auswählen. **Ergänzen / anhand der ID aktualisieren** ist der Standardmodus.
7. **Importvorschau prüfen** auswählen. Neu, geändert und unverändert werden vor der Übernahme angezeigt. Fehler müssen zuerst behoben werden.
8. Mit **Geprüften Import übernehmen** speichern. Vorher wird die aktuelle Konfiguration in MongoDB unter `config_backups` gesichert; die Erfolgsmeldung nennt die Sicherungs-ID.

Ein geänderter Eintrag wird vollständig anhand seiner Zeile übernommen. Leere optionale Felder entfernen die betreffende Zuordnung bzw. setzen den Modellstandard. Nicht in der Datei enthaltene Einträge bleiben im Ergänzungsmodus erhalten. Zum Ändern bestehender Einträge daher bevorzugt einen Export bearbeiten, statt eine neue Datei mit wenigen Spalten zu konstruieren.

## Beispiel für neue Modbus-Messpunkte

Die Verbindung `victron-gx` muss bereits im Board existieren oder in derselben vollständigen CSV als Verbindung enthalten sein. Registeradressen und Faktoren sind **Strukturbeispiele**, keine allgemeingültigen Victron-Register.

```csv
record_type;csv_version;id;name;connection_id;unit;unit_id;register;function;datatype;byte_order;word_order;scale;offset;enabled;record;stale_s
measurement;1;victron-ac-power;Victron AC-Leistung;victron-gx;W;100;820;3;int16;big;big;1;0;true;true;120
measurement;1;victron-soc;Batterie SOC;victron-gx;%;225;266;3;uint16;big;big;0.1;0;true;true;120
```

Modbus-Register sind 0-basiert. Die Funktionsnummer ist `3` oder `4`. Datentypen sind `uint16`, `int16`, `uint32`, `int32`, `float32`, `float64`. Byte- und Wortreihenfolge sind jeweils `big` oder `little`.

## Beispiel für MQTT-Messpunkte

```csv
record_type;csv_version;id;name;connection_id;address;json_path;unit;scale;offset;enabled;record;stale_s
measurement;1;generator-temp;Generator Motortemperatur;mqtt-haus;haus/bhkw/werte;engine.temperature;°C;1;0;true;true;120
measurement;1;generator-hours;Generator Betriebsstunden;mqtt-haus;haus/bhkw/werte;engine.seconds;h;0.000277777777777778;0;true;true;120
```

`json_path` bleibt bei einem einfachen Zahlenpayload leer. Für ioBroker ist `address` die vollständige Datenpunkt-ID, und `json_path` bleibt ebenfalls leer. Quellenübergreifend gilt: Wert = Rohwert × `scale` + `offset`.

## Spalten und Datensatztypen

| Spalte / Bereich | Bedeutung |
|---|---|
| `record_type` | `connection`, `measurement`, `flow` oder `settings` |
| `csv_version` | Aktuell immer `1` |
| `id` | Stabile ID; Systemeinstellungen verwenden `app` |
| `connection_id` | Vorhandene/mitimportierte Verbindung eines Messpunkts |
| `kind` | Bei Flüssen `device`, `node`, `grid` oder `storage` |
| `parent_id` | ID des übergeordneten Knotens, leer für Hauptebene |
| `category` | Gerätekategorie, z. B. `pv`, `generator`, `consumer`; bei Netz/Speicher keine Typauswahl |
| `datapoints.power_total` | Messpunktverweis, z. B. `point:victron-ac-power` |
| `datapoints.soc_reserve` | SOC-Reserve-Datenpunkt in Prozent |
| `datapoints.engine_temperature` | Motortemperatur in °C |
| `datapoints.efficiency` | Gemessene Effizienz in Prozent |
| `datapoints.fuel_consumption` | Kraftstoffverbrauch in der gewählten Einheit |
| `datapoints.operating_hours` | Betriebsstunden in Stunden |
| `storage_ids`, `mppt_ids` | Zugeordnete IDs, mehrere mit `\|` trennen |
| `sort_order` | Anzeigereihenfolge: kleinere Zahl zuerst, ohne Bilanzwirkung |
| `extra` | Zusatzmetadaten als JSON-Objekt innerhalb einer CSV-Zelle; Export übernimmt die nötigen CSV-Anführungszeichen |
| `appearance.*`, `recorder.*`, `influx.*` | Systemeinstellungen in flachen Spalten |

Unbekannte Spalten und ungültige Werte werden zurückgewiesen. Schlüssel und Werte nicht übersetzen. `true`/`false` für boolesche Einstellungen verwenden. Optionale Felder können leer bleiben. Bei vollständigen Anlagenexporten die Verwaltungsfelder und IDs möglichst unverändert lassen.

## Beispiel: bestehende Anlage um 20 Messpunkte erweitern

1. Die vorhandene Verbindung unter Datenerfassung prüfen, ihre stabile ID aus dem Verbindungen-Export übernehmen.
2. Messpunkt-Vorlage herunterladen und 20 Zeilen mit `record_type=measurement`, `csv_version=1`, neuen eindeutigen IDs und derselben `connection_id` ergänzen.
3. Erst eine Zeile importieren und den Rohwert vergleichen. Danach dieselbe Datei mit allen geprüften Register-/Topic-Zuordnungen ergänzend importieren.
4. Für neue Kennwort-Verbindungen die Zugangsdaten im Board hinterlegen; CSV transportiert sie nicht.
5. Erst danach Geräte mit den entsprechenden `point:<id>`-Verweisen zuordnen. Messpunkte allein erzeugen noch keine Verbraucher-/Erzeugerkarten.
6. Frischen Gesamtexport als Konfigurationsstand speichern und zusätzlich Datenbankbackup erstellen.

Sollen bestehende Geräteeinträge geändert werden, deren **vollständige exportierte Zeilen** bearbeiten. Fehlende neue Spalten können auf Standardwerte zurückfallen; eine schmale selbst gebaute Datei eignet sich nicht zum partiellen Ändern eines komplexen Hybrid-Geräts.

## Vollständiges Ersetzen

Der Modus **Gesamte Konfiguration ersetzen** entfernt Einträge, die nicht in der Datei stehen. Er verlangt eine zusätzliche Bestätigung. Dafür einen vollständigen Anlagenexport verwenden. Eine reine Messpunktdatei eignet sich nicht als vollständiger Ersatz, weil Verbindungen, Netzanschluss, Knoten und andere Zuordnungen fehlen würden.

Vor dem Import prüft der Server Datentypen, Verbindungs-/Messpunktverweise, Knotenkreise, Hybrid-Zuordnungen und Netzanschlüsse. Eine zwischen Vorschau und Übernahme geänderte Konfiguration führt zu einem Abbruch mit der Aufforderung, die Vorschau neu zu erstellen. Änderungen werden im laufenden Dienst gegen gleichzeitige Konfigurationsschreibzugriffe und Live-/Recorder-Zugriffe gesperrt. Bei einem Schreibfehler wird die vorherige Konfiguration zurückgespielt. Bei einem Datenbankausfall während dieser Wiederherstellung bleibt die Sicherung für den Administrator verfügbar; die Fehlermeldung nennt die Sicherungs-ID.

CSV-Import verändert oder löscht keine Messhistorie. Namens-, Quellen- und Faktoränderungen gelten für neue Aufzeichnungen; alte Messwerte werden nicht nachträglich umgerechnet. Die Anzahl gespeicherter Konfigurationssicherungen wächst mit den Importen und unterliegt keiner automatischen Löschfrist.

## Zugangsdaten und Tabellenformeln

Verbindungskennwörter und Influx-Passwörter/-Tokens werden nicht exportiert. Beim Import werden vorhandene Zugangsdaten anhand derselben ID beibehalten. Neue Verbindungen benötigen ihre Kennwörter anschließend im Board. Zugangsdatenfelder können nicht per CSV befüllt werden. Selbst in freie Zusatzmetadaten eingetragene Geheimnisse sind davon nicht automatisch erfasst.

Der Export kennzeichnet Zeichenketten, die Tabellenkalkulationen als Formel interpretieren könnten, mit einem führenden Apostroph. Beim Wiedereinlesen entfernt Energieboard seine entsprechende Kennzeichnung. IDs sowie Messpunkt-/Gerätenamen bleiben dabei erhalten.

## Hybrid-/MPPT-Felder ab 2.3

CSV-Version bleibt 1. Einen neuen Gesamtexport verwenden, damit alle Spalten enthalten sind. `hybrid_ac_mode` (`net`/`terminals`), `dc_power_unit` (`W`/`kW`), `dc_invert`, `dc_balance_complete` und `hybrid_min_power_w` sind Konfigurationsfelder. In den exportierten Datenpunktspalten stehen `datapoints.ac_input`, `datapoints.dc_power` und `datapoints.dc_load_power`. Die vorhandenen `storage_ids`/`mppt_ids` verwenden die exportierte Listen-Schreibweise. Ein Hybrid benötigt mindestens einen DC-Speicher; AC-Speicher werden als Hybrid-Verknüpfung abgewiesen.

Für MPPT `pv_type=mppt`, `category=pv`, `kind=device`, `datapoints.power_total` und optional `datapoints.energy_total` zuordnen. Phasen werden nicht verwendet. Die genaue Messgrenze und Wirkungsgradberechnung stehen in [DATENMODELL.md](DATENMODELL.md#dc-mppt-und-hybrid-wr-ab-23-schema-5). Alte CSV-Dateien ohne neue Spalten erhalten deren Standardwerte; daher bestehende Hybrid-Zeilen zum Bearbeiten frisch exportieren.
