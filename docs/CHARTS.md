# Eigene Charts

[Dokumentation](README.md) · [English](en/CHARTS.md)

Unter **Charts** (`/charts`) können beliebig viele Übersichten gespeichert werden, je Chart bis zu acht Reihen. Die Konfiguration liegt in MongoDB und übersteht Updates und Docker-Neuerstellungen bei erhaltenem Datenvolume.

## Chart erstellen

1. Die gewünschten Datenpunkte in **Datenerfassung** anlegen und **Aufzeichnen** aktivieren. Den Recorder unter System einschalten. Ab 2.7 werden auch aufgezeichnete Messpunkte gespeichert, die noch keinem Gerät zugeordnet sind.
2. **Charts → Chart hinzufügen** wählen, Namen vergeben und Quelle auswählen. Der Quellenname wird automatisch übernommen; eine eigene Beschriftung ist optional.
3. Mit **Reihe hinzufügen** weitere Quellen und Farben auswählen. Jede Quelle höchstens einmal pro Chart verwenden, maximal acht Reihen.
4. Speichern und oben Zeitraum wählen. „Heute“ aktualisiert sich ungefähr jede Minute; „Aktualisieren“ lädt die angezeigten Daten neu. Eigene Zeiträume sind auf höchstens 400 Tage pro Abfrage begrenzt.
5. Legenden anklicken, um Reihen sichtbar/unsichtbar zu schalten. Mit Maus oder Zeitschieber Einzelwerte prüfen.

## Verfügbare Quellen

- **Messpunkt:** Originalwert nach Erfassungsfaktor/Transformation, in der Einheit des Messpunkts. Ein kW-Messpunkt bleibt kW.
- **Leistung:** berechnete Gesamtleistung eines Geräts oder Knotens in W, einschließlich symmetrischer Phasenergänzung. Negative Werte und kleine Beträge bleiben erhalten.
- **Knotenrest:** automatisch berechneter Restverbrauch über die bestehende aufgezeichnete Restreihe; keine doppelte Bilanzierung.
- **SOC sowie Laden/Entladen:** SOC aus der Speicherzuordnung und getrennte abgeleitete Leistungsreihen. Speicher-Gesamtleistung ist Laden minus Entladen.
- **Gerätestatus / Zyklen:** aufgezeichnete Zustände und abgeschlossene Laufanzahl der Geräteerkennung; siehe [Gerätezyklen](GERAETEZYKLEN.md).

RUN-Leistung, Knotenrest und Speicherkanäle sind erst nach Aufzeichnung vorhanden. Eine Quellenoption bedeutet nicht, dass bereits Historie existiert. Bei fehlenden Daten bleibt eine Lücke. Geräte und Messpunkte erst aus Charts entfernen, bevor du ihre Konfiguration löschst. Eine Deaktivierung bewahrt vorhandene Historie.

## Darstellung und Genauigkeit

Unterschiedliche Einheiten bekommen getrennte Achsen, maximal zwei pro Teilgrafik. Mehr Einheiten erzeugen weitere Teilgrafiken. Gleiche Einheiten werden gemeinsam skaliert. Bool-, Status- und Zählerreihen erscheinen als Stufen; andere Messungen als Linien mit Lücken. Die numerischen Statuscodes erklärt die Anleitung zur Zykluserkennung.

Abfragen liefern höchstens ungefähr 480 Zeitfenster je Reihe und mindestens ein Recorderintervall pro Fenster. Für kontinuierliche Werte wird ein Fenstermittel, für digitale Werte der letzte Wert des Fensters verwendet. Das ist eine Visualisierung, **keine Ersatzberechnung für kWh**. Für Energieauswertungen die Energiebilanz mit Zählerdifferenzen und Zeitintegration verwenden.

Fehlende Werte werden nie als 0 gefüllt. Die Aggregation zeigt nur Fenster mit Beobachtung; sie verbindet keine fehlenden Fenster. Bei langen Zeiträumen einzelne Ereignisse in einen kürzeren Zeitraum zoomen. Es gibt keine nachträgliche Rekonstruktion von Status oder RUN-Leistung vor deren Aufzeichnung.

## Sichern und übertragen

Die Gesamtkonfiguration als CSV enthält `record_type=chart`, `name`, `sort_order` und eine JSON-Liste in der Spalte `series`. Beispiel für den Zellinhalt (CSV-Export übernimmt die nötige Maskierung):

```json
[{"kind":"measurement","reference_id":"meter-power","label":"","color":"#38BDF8","unit":"W"},{"kind":"power","reference_id":"workshop:rest_consumption","label":"Rest Werkstatt","color":"#F59E0B","unit":"W"}]
```

IDs müssen in der Zielkonfiguration existieren. Beim Import werden Quellen geprüft; Einheiten kommen aus der Quelle. CSV überträgt Konfiguration, keine Messhistorie. Für vollständigen Umzug das Datenbankbackup nutzen.

API: `GET /api/chart-sources`, `GET /api/charts`, `PUT /api/charts/{id}`, `DELETE /api/charts/{id}`, `GET /api/charts/{id}/data?start=2026-11-24T00:00:00%2B01:00&end=2026-11-25T00:00:00%2B01:00`. Zeitangaben mit Zeitzone bevorzugen.
