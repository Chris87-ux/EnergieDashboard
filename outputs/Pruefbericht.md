# Prüfbericht · Energieboard 2.7.1

[English](../docs/en/TEST-REPORT.md) · Stand: 26. November 2026.

## Ergebnis

**152 Backendtests erfolgreich**, Produktionsbuild erfolgreich. Vollständige Integration mit echter isolierter MongoDB und HTTP-/MQTT-/Modbus-TCP-Testquellen sowie 50 Geräten erfolgreich. Chromium prüft Deutsch/Englisch, Desktop/Mobil, Konfiguration, Diagramme, Charts, Gerätezyklen und Prognosen ohne JavaScript-Fehler. Die Anwendung enthält keinen Demo-Modus; alle Testwerte stammen aus isolierten Testprozessen.

## Neue Regressionen für 2.7.1

- VRM-Stundensummen aus Wh nach kWh: das Beispiel 38.894,84 Wh ergibt 38,89484 kWh. Keine Batterie-/Verbrauchsprognose wird dazuaddiert.
- Startgewichte 25/25/50 durch gemeinsame VRM-/Solcast-Gruppe, gleiche Einzelgewichte, unabhängige Quellen und frei gewählte Gruppen.
- Manuelle relative Gewichte einschließlich 0, Normierung bei fehlenden Quellen, unbekannte Mischung bei ausschließlich Gewicht 0 und benutzerdefinierte automatische Obergrenze.
- Änderungen der Gewichtspräferenzen lassen physische Quellenrevisionen bestehen; VRM-Einheitenkorrektur erhält dagegen eine neue Parserrevision mit frischer Lernbasis.
- Einheitenmigration korrigiert alte Snapshots, Tagesmischungen und Fehlerwerte genau einmal. Ursprüngliche Berechnungen, Istwerte, tatsächlich verwendete Gewichte und manuelle Ausschlüsse bleiben nachvollziehbar erhalten. Nicht eindeutig identifizierte Anbieter werden nicht geraten.
- Echte MongoDB: zweimalige Migration, neue Parserrevision und Schema 8 geprüft; reale Recorder-Messwerte sind vor und nach der Migration identisch.
- Browser: alle Gewichtungsmodi, Obergrenze, Gruppenschalter, relative Quellengewichte und benutzerdefinierte Gruppen speichern. Reine AC-PV-Anlage ohne Akku mit automatisch übernommener Messseite anlegen und wieder entfernen. CSV-Vorschau bleibt gültig und Tokens bleiben verborgen.

## Bestehende Funktionen

Alle bisherigen Regressionen bleiben aktiv: Vorzeichen und kleine Leistungen, Netzbilanz, symmetrische Phasen, verschachtelte Knoten, Restverbraucher und Gruppen ohne Doppelzählung, Speicher/Hybrid/DC-Lasten, unabhängige Messpunktaufzeichnung, Charts mit Datenlücken/Einheiten, Gerätestatus und dauerhafte Zähler, Prognosequoten, Zeitgrenzen ohne Zukunftsdaten, validierte Korrekturfaktoren und manuelle Ausschlüsse.

Die komplette Integration prüft weiterhin stabile IDs, Quellenalterung, rekursives Abschalten, CSV-Konfliktschutz, Wiederholungsmigration und vollständiges Backup/Restore einschließlich BSON-Werten. Gerätezähler bleiben bei simuliertem Schreibabbruch eindeutig. Morgenprognosen werden nicht durch spätere Wetterabrufe ersetzt; die technische Einheitenkorrektur ist eine protokollierte Ausnahme.

## Bereitstellung

Startbereitschaft und Update-Rollback erfolgreich. Dokumentationsprüfung erfolgreich: 44 Markdown-Dateien, 329 lokale Links/Sprungmarken, 18 JSON-Beispiele und 70 Bash-Blöcke. Installationsarchiv, ausführbare Skriptmodi und SHA-256 erfolgreich geprüft. Die [Linux-Dockerprüfung für 2.7.1](https://github.com/Chris87-ux/EnergieDashboard/actions/runs/45820902586) ist vollständig grün: Compose-Build/Start, alle 152 Backendtests im Laufzeitimage, echte MongoDB-Regressionsprüfungen einschließlich VRM-Migration, Healthcheck/Non-Root, Persistenz nach Container-Neuerstellung und beide Linux-Skriptprüfungen.

## Prüfgrenzen

Kein Zugriff auf deine Produktionsdatenbank oder echte VRM-/Solcast-Konten. Die Korrektur wird erst beim Update auf deinem Server angewendet. Cloudadapter sind mit offiziellen Formaten und isolierten HTTP-Antworten geprüft; aktuelle Kontorechte und tatsächliche Anbieterwerte bleiben vor Ort zu prüfen. Es wurde kein echter Proxmox-LXC gebootet und keine physische Anlage vermessen. Messgrenzen und Einheiten der PV-Istquelle müssen zur prognostizierten Anlage passen. Gewichtung ist konfigurierbar und verspricht keine tägliche Verbesserung der Wettervorhersage.
