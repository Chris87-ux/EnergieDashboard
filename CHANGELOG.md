# Änderungen

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
