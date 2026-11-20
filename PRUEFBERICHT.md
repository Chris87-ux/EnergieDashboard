# Prüfbericht · Energieboard 2.0.0

Stand: 20. November 2026. Geprüft wurden Backend, gebaute Oberfläche, Protokolladapter, Konfigurationsübernahme, Sicherung und Updateablauf. Das ausgelieferte Programm enthält keinen Demo-Modus; Messwerte der Tests stammen ausschließlich aus isolierten Testprozessen.

## Automatisierte Prüfungen

### Backend

32 Unit-/Regressionstests mit Python 3.11 erfolgreich:

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
