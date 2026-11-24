# Prüfbericht · Energieboard 2.6.0

[English](../docs/en/TEST-REPORT.md)

Stand: 24. November 2026. Geprüft wurden Backend, gebaute Oberfläche, Protokolladapter, Konfigurationsübernahme, Sicherung und Updateablauf. Das ausgelieferte Programm enthält keinen Demo-Modus; Messwerte der Tests stammen ausschließlich aus isolierten Testprozessen.

## Prüfungen für 2.6

103 Backendtests erfolgreich: alle 97 bisherigen Regressionen sowie sechs neue Tests für Sprachverhandlung, Platzhalter, übersetzte API-Fehler, geschützte Namen/Metadaten und abgeleitete Beschriftungen. TypeScript/Vite-Produktionsbuild erfolgreich.

Vollständige Integration mit echter isolierter MongoDB, HTTP/MQTT/Modbus-Testquellen, 50 Geräten, Historie, CSV, Migration und Backup/Restore erfolgreich. Chromium prüft Deutsch und Englisch über den tatsächlichen Sprachschalter: Speicherung pro Browser, URL-Override, Zahlen/Kalender, Formulare, API-Zeiträume, unveränderte Gerätekonfiguration, Abbruch bei ungespeicherten Eingaben, Einbettung und alle Seiten im Mobilformat ohne JavaScript-Fehler. Die bisherigen Konfigurations-/Bilanzprüfungen bleiben aktiv.

Die englischen Anleitungen liegen unter docs/en und sind im Archiv enthalten. Dokumentationslinks, lokale Sprungmarken, JSON-Beispiele, Bash-Syntax, Archivinhalt und SHA-256 werden vor Veröffentlichung geprüft. Linux-Docker-CI wird vor der Release-Markierung bestätigt. Prüfgrenzen: lokale Protokollfixtures, keine echten Produktionsgeräte und kein tatsächlicher Proxmox-LXC-Boot; Namen und eigene Metadaten bleiben absichtlich in ihrer eingegebenen Sprache.

## Prüfungen für 2.5

97 unterschiedliche Backendtests erfolgreich: 80 bestehende Regressionen und 17 neue Tests für API-Vorlagen, Legacy-Konvertierung, Pfadvariablen, JSON Pointer, Home-Assistant-Bearer, evcc-Sammelantwort, Klartext, Bulk-Teilmengen, isolierte HTTP-Fehler, Basic/Token-Header, Token-Erhalt/-Löschen sowie Gruppenberechnung, Fehlwerte, Zeitraumvollständigkeit und CSV-Referenzen.

Integration mit echter isolierter MongoDB und HTTP-API erfolgreich. Lokale HTTP-Quellen liefern ioBroker-, Home-Assistant-, evcc- und freie API-Antworten. Gruppen werden gespeichert, quer über Knoten summiert, bei Knotendeaktivierung reduziert und einschließlich Historie gesichert/wiederhergestellt. Bestehende 50-Geräte-, MQTT-, Modbus-, Migration-, CSV- und Energiebilanzprüfungen bleiben erfolgreich. Chromium prüft API-Vorlagen, Verbindung/Messpunkt-Formulare, Gruppenanlage und -zuordnung sowie Darstellung in Übersicht und Energiebilanz; Desktop/Mobil ohne JavaScript-Fehler. TypeScript/Vite-Build erfolgreich.

LXC-Readiness-Harness bestätigt stille anfängliche curl-Fehler mit anschließendem Erfolg sowie sichtbaren finalen Fehler bei dauerhafter Nichterreichbarkeit. Updater-Harness prüft Erfolg und Rücknahme nach Fehler; ShellCheck und Bash-Syntaxprüfung erfolgreich. Die [Linux-Dockerprüfung für 2.5.0](https://github.com/Chris87-ux/EnergieDashboard/actions/runs/45153089799) ist vollständig erfolgreich: Compose-Validierung, Image-Build, 97 Backendtests im Laufzeitimage, Healthcheck/Non-Root, Persistenz nach App-Neuerstellung und beide Linux-Skriptprüfungen. Dokumentationslinks, JSON-Beispiele, Bash-Syntax, Archivinhalt und SHA-256 wurden ebenfalls geprüft.

Prüfgrenzen: keine echten Home-Assistant-/evcc-/Victron-Produktionsgeräte, kein tatsächlicher Proxmox-LXC-Boot und keine Fremdserver-TLS-/Proxy-Konfiguration. Die Protokolltests verwenden isolierte lokale Server. Zugangsdaten, Messgrenzen, Einheiten und API-Feldpfade müssen in der Zielanlage geprüft werden. Die nachfolgenden Abschnitte dokumentieren frühere Prüfstände.

## Prüfungen für 2.4

80 Backendtests erfolgreich, einschließlich neuer Fälle für Netztransfer, Export, Nullproduktion, unbekannte Werte, Hybrid mit/ohne MPPT, AC-Speicher, falsche Vorzeichen, ganze dreiphasige Gesamtleistung, einzelne/echte asymmetrische Phasen, RUN, Phasenreste, historische Gesamt-/Teilphasenzähler, identische Live-/Zeitraumbilanz und getrennte Netzzähler. Die Netzfrequenz wird gegenüber einer abweichenden Generatorfrequenz getestet.

Integration mit echter Test-MongoDB, HTTP/MQTT/Modbus, 50 Geräten und Chromium erfolgreich: gemeinsame Netzkachel mit Frequenz und Tagesenergie, Hybridproduktion verfügbar, berechnete RUN-Phasen, Zeitraumkennzahlen, geänderte Bezeichnungen, CSV, Migration, Backup/Restore sowie Desktop-/Mobilansichten ohne JavaScript-Fehler. TypeScript/Vite-Build erfolgreich. Physische Geräte und tatsächlicher Proxmox-LXC sind weiterhin nicht Teil dieser Prüfung.

Der neue Quellstand besteht die vollständige [Linux-Dockerprüfung](https://github.com/Chris87-ux/EnergieDashboard/actions/runs/45128748869): Build, alle 80 Backendtests im Laufzeitimage, Healthcheck, Persistenz nach App-Neuerstellung und Linux-Updater-Erfolgs-/Fehlerfälle erfolgreich. Die nachfolgenden Abschnitte dokumentieren die älteren Prüfstände und deren Grenzen.

## Dokumentationsstand

Die Benutzeranleitungen wurden am 21. November 2026 neu gegliedert und mit Modellen, Editor, Compose-Dateien, Installer, Updater und Backupwerkzeug abgeglichen. Einstieg: [Dokumentationsübersicht](../docs/README.md). Dokumentationslinks, lokale Sprungmarken, JSON-Beispiele, Bash-Syntax der Anleitungsblöcke sowie Paketinhalt und SHA-256 werden vor Veröffentlichung geprüft. Ergebnis: 19 Markdown-Dateien einschließlich ausgelieferter Kopien, 166 lokale Links/Sprungmarken, 8 JSON-Blöcke und 42 Bash-Blöcke geprüft; TypeScript/Vite-Build erfolgreich. Das neue Paket enthält alle zehn Dateien unter `docs/`. Der [Dockerlauf nach der Dokumentationsüberarbeitung](https://github.com/Chris87-ux/EnergieDashboard/actions/runs/44921677494) besteht ebenfalls: Build, alle 60 Backendtests im Laufzeitimage, Healthcheck, Persistenz und Linux-Updaterfälle erfolgreich. Diese Dokumentationsprüfung ersetzt keine erneute reale Zielinstallation; die folgenden Anwendungstests beziehen sich auf den genannten geprüften 2.3.0-Quellstand.

## Neue Prüfungen für 2.3

- 60 Backendtests erfolgreich: zusätzlich DC-MPPT-Normalisierung, relevante Datenpunkte, getrennte DC-Zählerenergie, Entladung, PV mit gleichzeitiger Batterieladung, Netzladung, mehrere MPPTs/Speicher, DC-Lasten, Einheiten und Vorzeichen, AC-Netzdurchleitung, Rückspeisung und dreiphasige AC-Out-Summe.
- Wirkungsgrad aus direkter DC-WR-Messung oder ausdrücklich bestätigter DC-Busbilanz. Fehlende/inkompatible Quellen, kleine Leistungen, entgegengesetzte Vorzeichen und Werte über 100 % erzeugen keinen scheinbaren gültigen Wirkungsgrad.
- CSV-Rundlauf erhält neue Hybrid-Felder und verweigert AC-Speicher als DC-Hybrid-Verknüpfung.
- Echte API prüft DC-Gesamtenergie, Wirkungsgrad, MPPT-Normalisierung und ungültigen Wechsel eines zugeordneten Speichers auf AC. Migration Schema 4→5 wird wiederholt ausgeführt; IDs, Datenpunkte und Historie bleiben erhalten.
- Chromium prüft fehlende Phasen-/RUN-/Frequenzfelder für DC-MPPT, DC-Energiezuordnung, neue Hybrid-AC-/DC-Eingaben und den angezeigten Wirkungsgrad. Bestehende Desktop-/Mobilprüfungen bleiben aktiv.
- Der im gemeldeten Screenshot sichtbare Dockerfehler gehört zum älteren Lauf 44885156398. Die Ursache war der Updater-Test im schreibgeschützten/noexec App-Container. Der Test wird seit dem Korrekturlauf 44885373167 auf dem Linux-Runner ausgeführt; App-Build und Persistenz bleiben weiterhin echte Dockerprüfungen.
- Endgültiger Quellstand erfolgreich auf Linux geprüft: [Docker build and persistence – Lauf 44906013502](https://github.com/Chris87-ux/EnergieDashboard/actions/runs/44906013502). Compose-Validierung (lokal/externe DB), Image-Build, Start mit MongoDB, alle 60 Backendtests im Laufzeitimage, Health-/Non-Root-Prüfung, Konfigurationspersistenz nach App-Neuerstellung und Updater-Erfolgs-/Fehlerfälle bestanden. Auch der vorhergehende Lauf 44905786043 war erfolgreich.

## Neue Prüfungen für 2.2

- Gemeinsame Netzkachel mit Bezug und Lieferung; nur eine sichtbare Netzkachel, oben mittig, auch im eingebetteten Dashboard. Getrennte Netz-Geräte entfallen im Diagramm und in Live-Gerätelisten.
- Negative Erzeugerleistung bleibt als Messwert erhalten. Knotenrest und Gesamtbilanz nutzen den Betrag gemäß konfigurierter Rolle.
- Der Filter wurde ausdrücklich für -1000, -1.1, -1, +1, +1.1 und +1000 W sowie für den Nullbereich getestet. Er blendet standardmäßig nur strikt zwischen -1 und +1 W aus; Netzkanäle bleiben unabhängig davon sichtbar.
- Kleine Werte ±0.25 W sowie ±0.0001 W werden im Backend nicht mehr auf null gerundet. Im Browser wird die Anzeige von -0,25 W und +0,25 W geprüft.
- Integration historischer negativer Erzeugerleistung liefert den korrekten positiven Energiebeitrag.
- Dockerfile, lokale/externe Compose-Variante, persistentes MongoDB-Volume, Healthchecks, Non-Root-App und Docker-Anleitung ergänzt. Der Linux-Lauf [Docker build and persistence](https://github.com/Chris87-ux/EnergieDashboard/actions/runs/44885373167) ist erfolgreich abgeschlossen. Image-Build, Compose-Start mit MongoDB, 48 Backendtests im Laufzeitimage, Non-Root-Betrieb, Frontend/API und Konfigurationspersistenz nach Container-Neuerstellung wurden geprüft. Auch der isolierte LXC-Updater-Test auf dem Linux-Runner besteht. Die externe Compose-Variante wurde auf gültige Konfiguration geprüft; eine zusätzliche externe Produktionsdatenbank war nicht angeschlossen. Auf dem Entwicklungs-PC wurde keine Docker-Laufzeit installiert.

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

Die lokalen Integrations-/Browserprüfungen liefen unter Windows mit Python 3.11, echter MongoDB und Chromium. Zusätzlich wurde die Docker-Bereitstellung auf einem Linux-GitHub-Runner gebaut und gestartet. Es wurde hier kein vollständiger Debian-/Proxmox-LXC gestartet. APT, die Dateirechte der direkten LXC-Installation, systemd und der Proxmox-Kernel wurden nicht in einem realen Proxmox-Zielcontainer ausgeführt. Die Updater-Fallprüfung ersetzt deshalb keinen Zielsystemtest der gesamten Installation. Physische Geräte, reale Lastwechsel, Datenqualität und langfristiges Datenwachstum konnten nicht vorweggenommen werden.

Die Anwendung bietet keine eigene Anmeldung, keine Schaltfunktionen, keine automatische Datenlöschfrist und keine historische Rekonstruktion früherer Knoten-/Gerätezuordnungen. Speicherenergie und Restlaufzeit sind rechnerische Schätzungen. Bei Hybrid-WR wird PV-Erzeugung/Eigenverbrauch aus der gemischten AC-Abgabe nicht als gesicherter Wert ausgegeben. MQTT-Publisher-Zeitstempel und gerätespezifische LWT-Topics sind noch nicht ausgewertet; die Gültigkeit beginnt beim Empfang.

Ein neuer Speicher benötigt eine feste Kapazität; bei übernommenen Speichern diese neue Angabe einmal ergänzen. Knoten-Restenergie und neue Messpunkte beginnen mit der Aufzeichnung. Bereits vorhandene Historie wird erhalten und nicht rückwirkend neu bilanziert.

Die Integrations- und Browserprüfungen sind im Repository unter `app/backend/tests/` enthalten. Der isolierte Updater-Test steht unter `deploy/test_update.py`. Die Installationsanleitung beschreibt den Aufruf und den verbleibenden Abgleich am Zielsystem.
