# Prüfbericht · Energieboard 2.2.0

Stand: 21. November 2026. Geprüft wurden Backend, gebaute Oberfläche, Protokolladapter, Konfigurationsübernahme, Sicherung und Updateablauf. Das ausgelieferte Programm enthält keinen Demo-Modus; Messwerte der Tests stammen ausschließlich aus isolierten Testprozessen.

## Neue Prüfungen für 2.2

- Gemeinsame Netzkachel mit Bezug und Lieferung; nur eine sichtbare Netzkachel, oben mittig, auch im eingebetteten Dashboard. Getrennte Netz-Geräte entfallen im Diagramm und in Live-Gerätelisten.
- Negative Erzeugerleistung bleibt als Messwert erhalten. Knotenrest und Gesamtbilanz nutzen den Betrag gemäß konfigurierter Rolle.
- Der Filter wurde ausdrücklich für -1000, -1.1, -1, +1, +1.1 und +1000 W sowie für den Nullbereich getestet. Er blendet standardmäßig nur strikt zwischen -1 und +1 W aus; Netzkanäle bleiben unabhängig davon sichtbar.
- Kleine Werte ±0.25 W sowie ±0.0001 W werden im Backend nicht mehr auf null gerundet. Im Browser wird die Anzeige von -0,25 W und +0,25 W geprüft.
- Integration historischer negativer Erzeugerleistung liefert den korrekten positiven Energiebeitrag.
- Dockerfile, lokale/externe Compose-Variante, persistentes MongoDB-Volume, Healthchecks, Non-Root-App und Docker-Anleitung ergänzt. Der Laufzeittest wird mit dem Workflow [Docker build and persistence](https://github.com/Chris87-ux/EnergieDashboard/actions/workflows/docker.yml) auf Linux ausgeführt. Er baut das Image, startet Compose, prüft 48 Backendtests im Image und Konfigurationspersistenz nach Container-Neuerstellung. Auf dem Entwicklungs-PC wurde keine Docker-Laufzeit installiert.

Die unten genannten Windows-Integrations-/Browserprüfungen verwenden lokale Testquellen und echte MongoDB. Ein tatsächlich an Proxmox bzw. die eigenen Geräte angeschlossener Docker-Host ist davon zu unterscheiden.

## Neue Prüfungen für 2.1

- CSV-Rundlauf für vollständige Konfiguration und kompakte Messpunktdateien mit stabilen IDs und erhaltenen Kennwörtern.
- Echte API-Importvorschau und Übernahme mit MongoDB-Konfigurationssicherung; zwischenzeitlich geänderte Konfiguration weist die veraltete Vorschau zurück.
- Fehlerhafte Spalten, Datentypen, doppelte IDs, fehlende Referenzen und Knotenkreise werden abgewiesen. Ein simulierter CSV-Schreibfehler im isolierten Unit-Test stellt die vorherige Konfiguration wieder her.
- Nullleistungsfilter mit kontrollierten Zeitwerten bis einschließlich 60 Sekunden, Rücksetzen bei unbekannten Werten/Beobachtungslücken und sofortiges Wiedereinblenden bei Leistung. Persistenter Zustand zusätzlich gegen MongoDB geprüft; die Minute wurde dabei über gespeicherte Zeitstempel simuliert.
- Browser: verstecktes Nullgerät und „Inaktive anzeigen“, rechteckige Knotenauswahl und Pfadleiste sowie Diagrammseiten vor/zurück.
- Browser: CSV-Dateiupload, Vorschau und Übernahme; Bearbeitungsformular als direktes Geschwisterelement unter der Messpunktzeile.
- Browser: Netz als eigener Typ, Netz/Speicher nicht als auswählbare Gerätekategorien, Generator-Messfelder und Symbolauswahl.
- Generator-Messwerte für Motortemperatur, Effizienz, Kraftstoffverbrauch und Betriebsstunden beeinflussen die Leistungsbilanz nicht.
- Speicher: AC mit drei Phasen und SOC-Reserve-Datenpunkt einschließlich fehlendem Reservewert; DC ohne Phasenfelder, Energie-/Frequenzfelder und RUN-Einstellung.
- TypeScript/Vite-Produktionsbuild und Browserprüfung aller bisherigen Ansichten einschließlich Mobilformat bleiben erfolgreich.

Beim Prüfen der Knotennavigation wurde die anklickbare SVG-Fläche auf den Knoten selbst begrenzt. Verbindungskurven lösen dadurch keinen unbeabsichtigten Knotenwechsel aus. Diagrammseiten enthalten höchstens vier Elemente je Richtung, um überlagerte Beschriftungen zu vermeiden.

## Automatisierte Prüfungen

### Backend

48 Unit-/Regressionstests mit Python 3.11 erfolgreich:

- Energiegrenzen, Zählerresets und Zählerrauschen, Datenlücken und übernommene Historie.
- Fehlende Netzwerte erzeugen keine scheinbar vollständige Autarkie; fehlende DC-Speicherwerte verfälschen den Vollständigkeitsstatus der AC-Summen nicht.
- Gemischte Verbraucher/Erzeuger, verschachtelte und ungemessene Unterknoten, automatische Restkanäle und 50 Geräte.
- Separate DC-Speicher und MPPTs ohne doppelte AC-Verrechnung.
- Gewichteter Gesamt-SOC, fehlender SOC, Reserve, Vorzeichen und geglättete Restlaufzeit.
- Bidirektionale Netz-/Hybrid-Leistung und getrennte Netzenergiezähler.
- RUN-Historie mit aufgezeichneter Leistung und zeitlich begrenzter Gültigkeit.
- JSON-Pfade, gültige Zusatzmetadaten, Größenbegrenzung und Ablehnung nicht endlicher Zahlen.
- Modbus-Datentypen, Byte-/Wortreihenfolge, echte lokale TCP-Antwort, falsche Transaktions-ID und Registerfehler bei weiter verfügbaren anderen Registern.
- InfluxDB-2-CSV-Fehler und wiederholte Header, lokale Ergänzung fehlender Historienfenster.
- API meldet Datenbankausfall mit HTTP 503.

Die Erwartungen älterer Tests wurden dort angepasst, wo sich die angeforderte Fachlogik geändert hat: Speicher gehören nicht mehr in AC-Gesamtsummen; gemessene Knoten erzeugen zusätzliche Restkanäle.

### Integration mit echter MongoDB

Eine isolierte MongoDB 8.0.16, FastAPI über HTTP und lokale ioBroker-/MQTT-/Modbus-Protokollserver wurden gemeinsam betrieben. Geprüft wurden:

- Übernahme bestehender ioBroker-Datenpunkte in stabile Messpunkt-IDs.
- Wiederholte Migration ohne zusätzliche oder verlorene Messpunkte.
- Speicherung und Auswahl von Messpunkten, geschützte referenzierte Einträge und maskierte Passwörter.
- Ablehnung von Knotenkreisen und Löschen/Deaktivieren des letzten Netzanschlusses.
- Verschachtelte Verrechnung, Hybrid-Zuordnung, zwei Speicher und 50 zusätzliche Einzelgeräte.
- MQTT-JSON über tatsächliche Subscription mit Paho, gespeicherte Nachricht und Ablauf der Gültigkeit.
- Modbus TCP über tatsächliche Socket-Verbindung und Float-Register.
- Aufzeichnung normalisierter Messwerte und abgeleiteter Restwerte.
- Rekursive Deaktivierung einer Knotenunterstruktur.
- Vollständiger Datenbank-Backup-/Restore-Durchlauf einschließlich Historie, BSON-Binär-/Dezimal-/Zeitwerten und eindeutigen Indizes.

Die Protokollserver sind Testfixtures; die tatsächlichen Victron-Geräte oder ein produktiver MQTT-Broker wurden dabei nicht angesprochen. TLS, spezielle Broker-ACLs, Gerätestörungen und gerätespezifische Register müssen am Zielsystem geprüft werden.

### Browser

Chromium mit Desktopansicht 1440 px und Mobilansicht 390 px:

- Verbindungen und Messpunkte über die tatsächlichen Formulare angelegt.
- Fallback für ID-Erzeugung ohne `crypto.randomUUID` geprüft, damit HTTP-Betrieb funktioniert.
- Suchbare Symbolauswahl mit mehr als 50 Symbolen und Namensübernahme aus Messpunkt einschließlich langer Namen getestet.
- Alle drei Darstellungen gespeichert und nach Navigation erneut geprüft.
- Globale Farben, Gesamt-/Einzelspeicher, Knoten-/Gerätesuche und Einbettung unter `/flow` geprüft.
- Keine Navigation in der eingebetteten Ansicht.
- Kein horizontaler Überlauf auf den geprüften mobilen Seiten: Übersicht, Flow, Datenerfassung, Darstellung, Konfiguration, System und Energiebilanz.
- Keine JavaScript-Laufzeitfehler während des Durchlaufs.

Desktop- und Mobilansichten wurden zusätzlich anhand erzeugter Screenshots visuell kontrolliert.

## Installation, Updates und Paket

- TypeScript-Prüfung und Vite-Produktionsbuild erfolgreich.
- Python-Abhängigkeiten einschließlich Paho MQTT widerspruchsfrei (`pip check`).
- Bash-Syntax und ShellCheck für Installer und Updater erfolgreich.
- Isolierter Updater-Test mit echten Archiv-/Prüfsummenoperationen und simulierten Hostbefehlen: erfolgreicher Austausch, absichtlicher Installationsfehler mit Rückfall und Ablehnung einer falschen Prüfsumme vor dem Dienststopp.
- MongoDB-Sicherung/Wiederherstellung separat gegen die echte Testdatenbank geprüft.
- Archiv enthält gebaute Oberfläche, Quellcode, Installer, Updater, Sicherungswerkzeug, Versionsdatei und Dokumentation. Dateiinhalt, relative Archivpfade, Verzeichnis-/Skriptrechte und SHA-256 werden beim Paketbau geprüft.

Bei den Browserprüfungen wurden zwei Fehler gefunden und behoben: Formularschaltflächen lösten zunächst kein Submit aus, und die Beschriftung nativer Selects war für die eindeutige Zuordnung ungeeignet. Die betreffenden Tests bestehen nach den Korrekturen.

## Prüfgrenzen und Betriebsverhalten

Die Prüfungen liefen unter Windows mit Python 3.11, echter MongoDB und Chromium. Es wurde hier kein vollständiger Debian-/Proxmox-LXC gestartet. APT, Linux-Dateirechte, systemd und der Proxmox-Kernel wurden nicht in einem realen Zielcontainer ausgeführt. Die Updater-Fallprüfung ersetzt deshalb keinen Zielsystemtest der gesamten Installation. Physische Geräte, reale Lastwechsel, Datenqualität und langfristiges Datenwachstum konnten nicht vorweggenommen werden.

Die Anwendung bietet keine eigene Anmeldung, keine Schaltfunktionen, keine automatische Datenlöschfrist und keine historische Rekonstruktion früherer Knoten-/Gerätezuordnungen. Speicherenergie und Restlaufzeit sind rechnerische Schätzungen. Bei Hybrid-WR wird PV-Erzeugung/Eigenverbrauch aus der gemischten AC-Abgabe nicht als gesicherter Wert ausgegeben. MQTT-Publisher-Zeitstempel und gerätespezifische LWT-Topics sind noch nicht ausgewertet; die Gültigkeit beginnt beim Empfang.

Ein neuer Speicher benötigt eine feste Kapazität; bei übernommenen Speichern diese neue Angabe einmal ergänzen. Knoten-Restenergie und neue Messpunkte beginnen mit der Aufzeichnung. Bereits vorhandene Historie wird erhalten und nicht rückwirkend neu bilanziert.

Die Integrations- und Browserprüfungen sind im Repository unter `app/backend/tests/` enthalten. Der isolierte Updater-Test steht unter `deploy/test_update.py`. Die Installationsanleitung beschreibt den Aufruf und den verbleibenden Abgleich am Zielsystem.
