# Änderungen

## Dokumentation nach 2.3.0 · 21. November 2026

- Zentraler Dokumentationsindex mit Lesereihenfolge und getrennten Anleitungen für Proxmox-LXC und Docker-Erstinstallation.
- Schritt-für-Schritt-Konfiguration für Messquellen, Netz, Knoten, RUN, Generator, Speicher, DC-MPPT und Hybrid-WR.
- Eigene Seiten für Darstellung/Einbettung, Backup/Restore, Updates/Umzug, Fehlersuche, Glossar und Entwicklung.
- Datenmodell, API-/JSON-Beispiele, CSV-Hinweise und Versionsangaben auf Anwendung 2.3.0 / Schema 5 abgeglichen.
- Anwendungslogik und historische Release-Tags bleiben unverändert; neue Anleitungen werden mit dem aktuellen LXC-Paket ausgeliefert.

## 2.3.0

- DC-MPPT ohne Phasen, Frequenz oder RUN; DC-Leistung und kumulative Gesamtenergie, separate DC-Energiezeilen ohne doppelte AC-Zählung.
- Hybrid-WR mit AC-Netto oder AC-Out minus AC-In; Netzdurchleitung wird nicht als Wandlererzeugung gezählt.
- Hybrid-Panel mit bidirektionalem Wirkungsgrad aus direkter DC-WR-Messung oder bestätigter vollständiger DC-Busbilanz, Verlustleistung und Diagnose ungültiger Messwerte.
- Sichere DC-Speicher-/MPPT-Zuordnungen, passende CSV-Felder und additive Migration auf Schema 5.
- Erweiterte Tests für Hybrid-Richtungen, Einheiten, Messgrenzen, CSV und MPPT-Browserkonfiguration. Docker-Updater-Test läuft auf dem Linux-Host; der frühere Fehler „Bestehende Installation fehlt“ war bereits vor dieser Version behoben.

## 2.2.0

- Eine gemeinsame, dauerhaft sichtbare Netzkachel oben mittig für Bezug und Lieferung; keine getrennten Netzgeräte im Diagramm oder in Live-Gerätelisten.
- Negative Gerätewerte bleiben als Messwerte erhalten. Die Bilanz verwendet den Betrag gemäß konfigurierter Verbraucher-/Erzeugerrolle; auch historische Leistungsintegration berücksichtigt negative Erzeugerwerte.
- Kleine Leistungswerte unter 1 W werden mit Nachkommastellen angezeigt. Der Ausblendebereich bleibt strikt zwischen -1 W und +1 W bei der Standardschwelle.
- Dockerfile mit mehrstufigem Build, Compose für lokale bzw. externe MongoDB, persistentem Datenvolume, Healthchecks und Appbetrieb ohne Root-Rechte.
- Docker-Anleitung einschließlich Backup, Update und LXC-Umzug sowie automatisierter Linux-Docker-Prüfung.

## 2.1.0

- Hierarchisches Flussdiagramm mit rechteckigen Knoten, Navigation zu Kindern und Pfadleiste.
- Nullleistungsfilter mit serverseitig gespeicherter 60-Sekunden-Frist, einstellbarer Schwelle und Schalter für inaktive Geräte. Unbekannte Werte bleiben sichtbar.
- Inline-Bearbeitung von Verbindungen und Messpunkten, Hinweis bei ungespeicherten Änderungen.
- CSV für Gesamtanlage, Messpunkte und Verbindungen; Vorlage, Importvorschau, ID-Erhalt, Sicherung und Schutz gegen veraltete Vorschauen.
- Netzanschluss als eigener Typ; Netz/Speicher aus der Kategorieauswahl entfernt, bestehende Zuordnungen migriert.
- Generator/BHKW mit Symbol und Messpunkten für Motortemperatur, Effizienz, Kraftstoffverbrauch und Betriebsstunden.
- Speicher mit AC-/DC-Auswahl, passenden Leistungs-/Phasenfeldern und SOC-Reserve als Datenpunkt oder festem Ersatzwert.
- „Reihenfolge“ heißt „Anzeigereihenfolge“ mit Erklärung der Sortierung.

## 2.0.0

- Quellenunabhängige Messpunkte und eigener Reiter Datenerfassung für ioBroker, MQTT und Modbus TCP.
- Automatische Übernahme alter ioBroker-Zuordnungen mit unveränderten historischen Schlüsseln.
- Verschachtelte AC-Knoten mit Kreisprüfung und automatisch aufgezeichneten Restkanälen.
- Verbindlicher Netzanschluss, vorzeichenbehaftete oder getrennte Bezug-/Einspeisemessung.
- Separater Speicherbereich mit Kapazität, gewichteter Gesamtanzeige, Restenergie, Reserve und geglätteter Restlaufzeit.
- PV-Auswahl für WR, Hybrid-WR und DC-MPPT; getrennte AC-/DC-Behandlung und bidirektionaler Hybrid-AC-Anschluss.
- Drei Darstellungen, globale Farben, mehr als 50 suchbare Symbole und eingebettete Ansicht unter /flow.
- Update-Skript mit festem Download-Commit, Prüfsumme, Sicherung und automatischem Rückfall.
- JSON-Schemata und ausführliche Beschreibung in DATENMODELL.md.
