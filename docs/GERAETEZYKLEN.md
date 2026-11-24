# Gerätezyklen und Status

[Dokumentation](README.md) · [English](en/APPLIANCE-CYCLES.md)

Ab 2.7 zählen Waschmaschine, Trockner und Geschirrspüler abgeschlossene Läufe. Die Erkennung orientiert sich am Prinzip von [ioBroker device-reminder](https://github.com/Xenon-s/ioBroker.device-reminder): Startleistung, Stillstandsschwelle, Zeitbestätigung und ein gleitender Leistungsmittelwert. Die Implementierung läuft im Dashboard; der Adapter muss nicht installiert sein. Es werden keine Geräte geschaltet und keine Nachrichten versendet.

## Einrichtung

1. Unter **Datenerfassung** die gemessene Wirkleistung des Geräts anlegen. Faktor und Einheit prüfen; W und kW dürfen nicht verwechselt werden. Recorder einschalten, möglichst 5–10 Sekunden Abtastung und passende Aktualisierungsrate an der Quelle wählen. Ein Messpunkt mit längeren Meldepausen kann keine kurzen Betriebswechsel zuverlässig erkennen.
2. Unter **Konfiguration → Gerät bearbeiten → Gerätezyklen** die Erkennung aktivieren. Nur gewöhnliche Verbraucher unterstützen diese Funktion, keine Knoten, Erzeuger oder Speicher.
3. Profil Waschmaschine, Trockner oder Geschirrspüler auswählen. Profile sind **Startwerte**, keine universellen Regeln. Beispiel Waschmaschine: Start über 10 W für 60 s, Ende höchstens 5 W für 600 s, 120-s-Mittelwert, Mindestlaufzeit 300 s. Ein Geschirrspüler hat oft längere leise Phasen; Ende wird standardmäßig erst nach 900 s bestätigt.
4. Schwellen anhand eines vollständigen Testlaufs anpassen. Es muss gelten: Standby ≤ Ende < Start. Die Endeverzögerung länger als normale Wasch-/Trockenpausen wählen. Zu kurze Zeiten erzeugen zu viele Läufe, zu lange Zeiten verzögern die Fertigmeldung.
5. Bei einem zuverlässigen Betriebssignal **Bool-Signal** wählen. Eigenen Messpunkt zuordnen oder das bestehende RUN-Signal verwenden. 1 = läuft, 0 = steht. Bool-Erkennung zählt direkte Zustandswechsel; Verzögerungen, Mittelwertfenster und Mindestlaufzeit gelten für den Leistungsmodus.
6. Auf **Gerätestatus** (`/geraete`) Status und Zähler kontrollieren. Die normale Übersicht zeigt aktiv konfigurierte Geräte ebenfalls an; `/flow` bleibt eine reine Energieeinbettung.

## Zustände und Zählweise

| Status | Bedeutung |
|---|---|
| Aus / Bereit | Ruhender Verbraucher unter Standby-/Endeschwelle |
| Startet | Startschwelle erreicht, Bestätigungszeit läuft |
| Läuft | Bestätigter Betrieb |
| Pause | Vorübergehend geringe Leistung innerhalb eines Laufs |
| Fertig | Ende einschließlich Zeit und Mittelwert bestätigt |
| Unbekannt | Fehlende/zu alte Daten oder ausgeschalteter Recorder |

Ein Lauf wird **erst beim bestätigten Ende** gezählt und in Heute/Monat/Gesamt aufgenommen. Das bestätigte Ende wird auf den Beginn des ruhigen Endabschnitts datiert; die Erkennungsverzögerung zählt nicht zur Laufzeit. „Fertig bestätigen“ quittiert nur die Anzeige, ohne den Zähler zu ändern.

Kurze Leistungsspitzen unter der Mindestlaufzeit zählen nicht. Ein bei Erstaktivierung bereits laufendes Gerät erhält „Start unbeobachtet“ und erhöht den Zähler beim Ende nicht. Größere Messlücken unterbrechen einen Lauf und erzeugen keinen vermeintlich erfolgreichen Abschluss. Die Lückengrenze ist das Maximum aus 30 s und drei Recorderintervallen. Kleine fehlende Abschnitte setzen Endebestätigungszeiten zurück.

Der Zustand und eine feste Lauf-ID liegen in MongoDB. Ein normaler kurzer Neustart setzt die Zählung fort; ein längerer Ausfall beendet die Beobachtung als unvollständig. Wiederholte Verarbeitung eines Abschlusses zählt dank eindeutiger Lauf-ID nicht doppelt. Relevante Änderungen an Schwellen oder Messzuordnung während eines Laufs markieren ihn als neu konfiguriert. Namen- und Farbänderungen setzen die Erkennung nicht zurück.

Eine Laufzeitwarnung beendet den Lauf nicht automatisch. Im Verlauf stehen Abschlussart, Zeit und, sofern die aufgezeichnete Historie reicht, kWh pro Lauf. Unvollständige Energie ist mit Stern markiert. Geräte deaktivieren oder Erkennung abschalten löscht keine vergangenen Laufereignisse; für historische Status-Charts die Gerätekonfiguration beibehalten.

## Charts und API

Status wird numerisch aufgezeichnet: 0 Aus, 1 Bereit, 2 Läuft, 3 Pause, 4 Fertig, 5 Unbekannt, 6 Startet. In **Charts** lassen sich Status und kumulierter Laufzähler mit Leistung vergleichen. Keine Werte vor Beginn der Aufzeichnung ergänzen.

API: `GET /api/cycles/presets`, `GET /api/cycles/status`, `GET /api/cycles/{device_id}/events?limit=20`, `POST /api/cycles/{device_id}/ack` mit `{}`. Geräteeinstellungen stehen in `cycle_tracking`; das vollständige Schema liefert `/api/schemas/flow`.
