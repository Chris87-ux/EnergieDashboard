# Prüfbericht · Energieboard 2.7.0

[English](docs/en/TEST-REPORT.md)

Stand: 24. November 2026. Geprüft wurden Backend, Produktionsoberfläche, Protokolladapter, Konfigurationsübernahme und Sicherung. Testdaten existieren ausschließlich in isolierten Testprozessen; die Anwendung enthält keinen Demo-Modus.

## Backend und neue Funktionen

**141 Backendtests erfolgreich**, einschließlich aller bisherigen Regressionen und neuer Prüfungen für virtuelle Restverbraucher, Gruppen ohne Doppelzählung, DC-Verbraucher am Hybrid-WR, CSV, Charts, Gerätezyklen und vier Prognoseadapter.

Charts prüfen negative/kleine Werte, Phasenhochrechnung, verschiedene Einheiten, digitale Letztwerte, fehlende Daten und begrenzte Abfragepunkte. Zyklentests prüfen Waschpausen, Leistungsspitzen, unbeobachtete Starts, Bool-Flanken, Neustarts, Datenlücken und Warnungen. Prognosetests prüfen Sommerzeit mit 23/25 Stunden, native Energie-/Leistungseinheiten, AC-Begrenzung mehrerer Flächen, fehlende Daten, HTTP-Header ohne Tokens in URLs, Quotenfehler und Wartezeiten. Lernprüfungen verhindern Zukunftsdaten in Morgenmodellen, verlangen unabhängige Folgetage für Korrekturen und prüfen Rohwert-Rückfall, Quellenfamilien und zeitlich korrekte Ausschlüsse.

## Integration mit echter MongoDB und Chromium

Erfolgreich gegen echte isolierte MongoDB und HTTP-, MQTT- und Modbus-TCP-Testquellen, mit 50 Geräten. Weiterhin geprüft: Energie-/Phasenbilanz, Netzindikatoren, Quellenalterung, verschachtelte Knoten, Speicher/Hybrid, Gruppen, CSV-Vorschau/-Übernahme mit Konkurrenzschutz, Migration und vollständiges Backup/Restore einschließlich BSON-Werten.

Zusätzliche MongoDB-Prüfungen belegen genau einen abgeschlossenen Lauf bei erneut verarbeiteter Fertigmeldung nach simuliertem Schreibabbruch; dauerhafte Anfragebudgets begrenzen zwölf gleichzeitige Reservierungen auf acht pro Token/UTC-Tag und erneuern sich am Folgetag. Die eingefrorene Morgenprognose bleibt nach späterem Abruf unverändert; die Tagesauswertung berechnet den realen Zählerdelta-Ertrag und dessen Prognosefehler. Anbieterfehler behalten vorhandene Prognosen und setzen Wartezeiten.

Chromium prüft Kopiereditor und neue IDs, Restgruppen, Geräteprofil, Statusseite, gespeicherte Charts aus Messpunkt und Knotenrest, Prognoseanlage/-quelle, Token-Ausblendung, CSV, Löschschutz und englische Oberflächen. Die bisherigen Prüfungen für Formulare, drei Layouts, Sprache/URL-Override, unveränderte Nutzernamen, Kalender, Einbettung und Desktop/Mobil bleiben aktiv; keine JavaScript-Fehler.

## Bereitstellung und Dokumentation

TypeScript/Vite-Produktionsbuild erfolgreich. Startbereitschaftstest: erwartete vorübergehende curl-Verbindungsfehler bleiben verborgen; echter Timeout zeigt den letzten Fehler. Updateharness: Austausch, Rollback und Prüfsummenfehler vor Dienststopp erfolgreich. ShellCheck und Bash-Syntax erfolgreich.

Dokumentationsprüfung erfolgreich: 44 Markdown-Dateien, 329 lokale Links/Sprungmarken, 18 JSON-Beispiele und 70 Bash-Blöcke. Paketinhalt, ausführbare Skriptmodi und SHA-256 erfolgreich geprüft. Die [Linux-Dockerprüfung für 2.7.0](https://github.com/Chris87-ux/EnergieDashboard/actions/runs/45396672363) ist vollständig grün: Compose-Build, Start, alle 141 Backendtests im Laufzeitimage, zusätzliche echte MongoDB-Tests, Healthcheck/Non-Root, Persistenz von Konfiguration/Charts/Prognosezugang nach Container-Neuerstellung und beide Linux-Skriptprüfungen.

## Prüfgrenzen

Keine realen Victron-/PV-Konten oder physischen Waschmaschinen, Trockner und Geschirrspüler waren verbunden. Cloudadapter sind gegen offizielle Antwortformate und isolierte HTTP-Antworten geprüft; tatsächliche Kontoberechtigungen, aktuelle Freikontolimits und Anbieterverfügbarkeit erfordern die Einrichtung vor Ort. Ein über mehrere Wochen besserer Prognosefehler ist ohne reale historische Daten nicht belegt und wird nicht garantiert.

Kein echter Proxmox-LXC wurde hier gebootet. Netzwerk, TLS/Proxy, Geräteadressen, Modbus-Register, Messgrenzen und Vorzeichen am Zielsystem prüfen. Ein vollständiger Probebetrieb mit passenden Geräteschwellen bleibt nötig. Historische Testdaten prüfen Rechenlogik, keine eichrechtliche Messgenauigkeit. Das Wiki-Git-Repository ist weiterhin nicht erreichbar; alle Anleitungen liegen versioniert im Repository und im Installationsarchiv vor.
