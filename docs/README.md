# Dokumentation

Anwendungsstand **2.4.0**, Schema **5**, CSV **1** · Stand **23. November 2026**.

Die Dateien im Repository bilden die vollständige versionierte Dokumentation. Historische Tags behalten ihre damalige Fassung. Die Anleitungen lassen sich zusätzlich ins [GitHub-Wiki](https://github.com/Chris87-ux/EnergieDashboard/wiki) übernehmen; bei dieser Aktualisierung war dessen Git-Endpunkt trotz aktiviertem Wiki noch nicht erreichbar.

## 1. Installieren

1. [Proxmox-LXC: Voraussetzungen, Container, Netzwerk und Erstinstallation](../INSTALLATION.md)
2. [Docker: Host vorbereiten, Compose starten, externe Datenbank](../DOCKER.md)
3. [Erste Schritte: vom leeren Dashboard zur geprüften Anlage](ERSTE-SCHRITTE.md)

## 2. Konfigurieren

4. [Datenerfassung: ioBroker, MQTT und Modbus TCP](DATENERFASSUNG.md)
5. [Geräte und Knoten: Netz, Sensoren, RUN, Generator und Restbilanz](GERAETE-UND-KNOTEN.md)
6. [Speicher und Hybrid-WR: SOC, DC-MPPT, Messgrenzen und Wirkungsgrad](SPEICHER-UND-HYBRID.md)
7. [CSV: viele Messpunkte bearbeiten und Konfiguration übertragen](../CSV-IMPORT.md)
8. [Darstellung: Farben, Nullfilter, Diagramm und Einbettung](DARSTELLUNG-UND-EINBETTUNG.md)

## 3. Betreiben

9. [Betrieb, Sicherung, Wiederherstellung, Updates und Umzug](BETRIEB-UND-UPDATES.md)
10. [Fehlersuche nach Symptomen](FEHLERSUCHE.md)
11. [Begriffe und Einheiten](GLOSSAR.md)

## 4. Nachschlagen und entwickeln

12. [Datenmodell, API-Felder und erweitertes JSON](../DATENMODELL.md)
13. [Entwicklung und Prüfungen](ENTWICKLUNG.md)
14. [Prüfbericht und Prüfgrenzen](../PRUEFBERICHT.md)
15. [Änderungsverlauf](../CHANGELOG.md)

## Empfohlene Lesereihenfolge

**Neue Anlage:** eine Installationsanleitung → Erste Schritte → Datenerfassung → Geräte und Knoten → bei Bedarf Speicher und Hybrid-WR → Backup.

**Bestehende Anlage:** Backup → Änderungen des Zielreleases → Update-Anleitung der eigenen Installationsart → Abnahme in Erste Schritte. Für Docker keine LXC-Skripte ausführen.

**Viele Geräte:** zuerst einen bekannten Messpunkt jedes Protokolls vollständig prüfen. Danach CSV nutzen und schrittweise Abschnitte ergänzen. Nicht mit 50 ungeprüften Registerzuordnungen beginnen.

## Vor der Konfiguration bereitlegen

| Information | Beispiel / Zweck |
|---|---|
| Installationsart und Server-IP | LXC oder Docker, Browserzugriff |
| Quellen | ioBroker-Host, MQTT-Broker, Modbus-Geräte und Ports |
| Messpunktverzeichnis | IDs/Topics/Register, Datentyp, Faktor, Einheit |
| Messgrenzen | Netz, AC-Abschnitt, AC-In/Out, DC-Bus, Batterie |
| Vorzeichen | Bezug/Einspeisung, Ladung/Entladung, Wandlerleistung |
| Speicher | Gesamtkapazität in kWh, SOC, Reserve, Leistungswert |
| Historie | Recorder-Intervall, ggf. vorhandene InfluxDB |
| Betrieb | Sicherungsziel, Speicherplatz, gewünschter Zugriffsschutz |

## Konventionen in den Anleitungen

- Shellblöcke stehen für Linux/Bash. Die jeweilige Seite nennt, **auf welchem System** sie ausgeführt werden.
- `<SERVER-IP>` und ähnliche Platzhalter ersetzen. Beispieladressen sind keine Vorgabe für dein Netzwerk.
- Dezimalzahlen in Konfiguration und CSV verwenden einen Punkt; die Oberfläche zeigt deutsche Zahlenformate.
- Voraussetzungen wie MQTT-Broker, Modbus-Freischaltung oder ioBroker simple-api werden nicht automatisch mitinstalliert.
- „Nicht verfügbar“ bedeutet fehlende oder ungeeignete Daten und darf nicht als 0 interpretiert werden.

[Zur Projektübersicht](../README.md)
