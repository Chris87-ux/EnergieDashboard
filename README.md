# Energieboard 2.7.1

[English](README.en.md)

Energieboard stellt Stromerzeugung, Verbrauch, Netzanschluss und Speicher im eigenen Netzwerk dar. Es läuft direkt in einem Proxmox-LXC oder mit Docker Compose. Messwerte kommen über konfigurierbare HTTP-APIs (Vorlagen für ioBroker, Home Assistant und evcc), MQTT oder Modbus TCP. Konfiguration und Aufzeichnung liegen in MongoDB. Die Anwendung enthält keine Demodaten und steuert keine Geräte.

## Hier beginnen

| Dein Vorhaben | Anleitung |
|---|---|
| Noch keine Installation, Proxmox vorhanden | [Erstinstallation im Proxmox-LXC](INSTALLATION.md) |
| Linux-Docker-Host oder Docker-VM vorhanden | [Erstinstallation mit Docker Compose](DOCKER.md) |
| Dashboard läuft, aber noch keine Messwerte | [Erste Schritte und Abnahme](docs/ERSTE-SCHRITTE.md) |
| Datenpunkte aus APIs, MQTT oder Modbus einrichten | [Datenerfassung](docs/DATENERFASSUNG.md) |
| Verbraucher, Generator, Netz und verschachtelte Zähler anlegen | [Geräte und Knoten](docs/GERAETE-UND-KNOTEN.md) |
| Verbraucher zusätzlich zusammenfassen | [Verbrauchergruppen](docs/VERBRAUCHERGRUPPEN.md) |
| Batterie, DC-MPPT oder Hybrid-WR konfigurieren | [Speicher und Hybrid-WR](docs/SPEICHER-UND-HYBRID.md) |
| Bestehende Anlage sichern oder aktualisieren | [Betrieb, Backup und Updates](docs/BETRIEB-UND-UPDATES.md) |
| Fehler oder unplausible Bilanz | [Fehlersuche](docs/FEHLERSUCHE.md) |

**[Gesamte Dokumentation](docs/README.md) · [Änderungen](CHANGELOG.md) · [Prüfbericht](PRUEFBERICHT.md)**

## Funktionen

- Netzbezug und Einspeisung gemeinsam in einer dauerhaft sichtbaren Netzkachel.
- Verschachtelte AC-Knoten mit automatischem Restverbrauch bzw. Resterzeugung und anklickbarer Diagrammnavigation.
- Geräte mit Leistungssensor oder RUN-Signal und fester geschätzter Leistung.
- Generator/BHKW mit optionaler Motortemperatur, Effizienz, Kraftstoffverbrauch und Betriebsstunden.
- DC-MPPT ohne Phasen, mit DC-Leistung und kumulativer Gesamtenergie.
- Hybrid-WR mit AC-Netto oder AC-Out minus AC-In; Wirkungsgrad aus direkter DC-Messung oder bestätigter DC-Bilanz.
- Separate Speicher mit kapazitätsgewichtetem Gesamt-SOC, Leistungsbalken, Restenergie und geglätteter Restlaufzeit.
- Optionale Verbrauchergruppen mit gemeinsamer Liveleistung und Zeitraumenergie, unabhängig von der Knotenhierarchie.
- Deutsch/Englisch im Kopfbereich, persönliche Sprachwahl und englische Zahlen-/Datumsformate.
- CSV-Import/-Export mit Vorschau, stabilen IDs und Sicherung vor der Übernahme.
- Drei Darstellungen, globale Farben, suchbare Symbole und Einbettung über `/flow`.
- Nullleistungsfilter: standardmäßig erst nach 60 Sekunden strikt zwischen −1 W und +1 W ausblenden; Netz bleibt sichtbar.
- Updates mit erhaltener Konfiguration und Historie; direkter LXC-Updater mit Sicherung und automatischem Rückfall.

## Welche Installationsart?

| | Proxmox-LXC direkt | Docker Compose |
|---|---|---|
| Betriebssystem | Debian 12 Bookworm amd64 mit systemd | Linux amd64, Docker Engine und aktuelles Compose-Plugin |
| Anwendung | Python-Dienst im LXC | App-Container und optional MongoDB-Container |
| Einstieg | [LXC-Anleitung](INSTALLATION.md) | [Docker-Anleitung](DOCKER.md) |
| Update | `deploy/update.sh` | Git-Tag wechseln und Compose neu bauen |
| Daten | MongoDB lokal oder extern | Benanntes MongoDB-Volume oder externe MongoDB |

Startgröße für 30–50 Geräte: etwa 2 vCPU, 4 GB RAM, 32 GB SSD plus Platz für Historie und Sicherungen. Dies ist eine Planungsempfehlung, keine Speicherzusage. Lokale MongoDB 8.0 benötigt eine geeignete CPU mit AVX und einen kompatiblen Kernel; die jeweilige Installationsanleitung erläutert die Prüfung.

## Zugriff nach der Installation

```text
http://<SERVER-IP>:8000/
```

Unter **Datenerfassung** Verbindungen und Messpunkte anlegen, anschließend unter **Konfiguration** zuerst den Netzanschluss. Die [Ersteinrichtung](docs/ERSTE-SCHRITTE.md) führt durch den gesamten Ablauf.

Energieboard besitzt keine eigene Anmeldung. Im vertrauenswürdigen LAN betreiben oder einen Reverse-Proxy mit Zugriffsschutz verwenden. Die Datenquellen müssen vom Server bzw. App-Container erreichbar sein.

## Version und Verlässlichkeit

Aktueller Anwendungsstand: **2.7.1**, Datenbankschema **8**, CSV-Format **1**. Dokumentation: **24. November 2026**. Für Installationen feste Tags wie `v2.7.1` verwenden; `main` kann bereits neuere Änderungen enthalten.

[Prüfbericht und bekannte Grenzen](PRUEFBERICHT.md): 103 Backendtests sowie Integrations-, Browser- und Linux-Dockerprüfungen. Physische Victron-Geräte und ein produktiver Proxmox-LXC wurden hier nicht angeschlossen. Energieboard ist eine Anzeige und Auswertung; Schätzwerte ersetzen keinen geeichten Zähler.

## Neue Auswertungen ab 2.7

- [PV-Prognosen](docs/PV-PROGNOSEN.md): vier Quellen, unveränderte Morgenprognosen, geprüfte Korrekturen und Tagesprotokolle.
- [Gerätezyklen](docs/GERAETEZYKLEN.md): Waschmaschine, Trockner und Geschirrspüler mit Status und abgeschlossenen Läufen.
- [Charts](docs/CHARTS.md): eigene gespeicherte Ansichten aus Messpunkten, Knotenrest, Speicher- und Gerätestatus.
- Messpunkte kopieren, mehrere DC-Verbraucher pro Hybrid-WR und konfigurierbare Restverbraucher mit Gruppenzuordnung.

Der Recorder muss für Historie und Zykluserkennung aktiv sein. Prognosezugänge werden erst durch eigene Konfiguration aktiviert.
