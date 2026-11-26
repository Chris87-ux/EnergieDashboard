# Änderungen

[English](docs/en/CHANGELOG.md)

## 2.7.1 · 26.11.2026

- VRM-Stundenwerte korrekt von Wh in kWh umrechnen. Fehlerhafte Werte aus 2.7.0 einmalig und protokolliert reparieren, Mischungen/Fehler neu berechnen, echte Messhistorie erhalten.
- Gewichtung pro Anlage wählbar: automatisch, gleiche Anteile oder manuelle relative Quellengewichte einschließlich 0. Quellengruppen individuell benennen/auflösen; automatische Obergrenze einstellbar.
- Aktuelle Vorschau zeigt neue Gewichtung sofort; Tagesprotokolle behalten tatsächlich eingefrorene Gewichte. VRM-Parserrevision setzt fehlerhafte Lernstatistik zurück.
- Reine AC-PV-Installationen ohne Akku explizit unterstützt und Messseite bei Auswahl automatisch übernehmen. DC und gemischte Anlagen bleiben möglich.
- Deutsch/Englisch, CSV, zusätzliche Regressionen und wiederholbare Migration. Schema 8 schützt vor Rückstart der alten Einheitenlogik.

## 2.7.0 · 24.11.2026

- Messpunkte direkt neben dem Eintrag kopieren, mit neuer ID und ohne Übernahme alter Historienkanäle.
- Mehrere DC-Verbraucher je Hybrid-WR, gemessen oder über RUN. Einzelzuordnung und Sammelmesswert schließen sich aus; keine zusätzliche AC-Doppelzählung.
- Automatische Restverbraucher in der Konfiguration mit eigenem Namen, Symbol, Farbe, Reihenfolge und Verbrauchergruppe, ohne eigene Messpunkte.
- Geräte-/Komponentenbegriffe statt „Neuer Fluss“; doppelte globale ioBroker-Eingabe unter System entfernt, Altbestandsübernahme bleibt erhalten.
- Gespeicherte Charts aus Rohmesspunkten und berechneten Werten, getrennte Einheitenachsen und sichtbare Datenlücken. Aufzeichnung auch ohne Gerätezuordnung.
- Status und dauerhafte abgeschlossene Laufzähler für Waschmaschine, Trockner und Geschirrspüler, inklusive Pausen, Mindestzeiten, Neustart-/Lückenbehandlung und Verlaufsenergie.
- Vier private PV-Prognosequellen: VRM, Forecast.Solar, Solcast und Open-Meteo als lokales Einstrahlungsmodell. Dauerhafte Abruflimits, unveränderte Tagesanfangsprognosen, Vergleich mit Ist-Ertrag, geprüfte Faktoren, Quellenfamilien und protokollierte Ausschlüsse.
- Neue Funktionen auf Deutsch und Englisch dokumentiert und übersetzt. CSV-Konfiguration enthält Charts, Zyklusparameter und Prognosen ohne Tokens.
- Schema 7 additiv; bestehende IDs, Historie und Gruppen bleiben. CSV bleibt Version 1. Die Startbereitschaftsprüfung vermeidet vorübergehende curl-Verbindungsfehler beim Update.

## 2.6.0 · 24. November 2026

- Deutsch/Englisch für Navigation, Übersichten, Formulare, Hinweise, Dialoge und die eingebaute Installationshilfe.
- Pro Browser gespeicherte Sprache, explizite URL-Auswahl auch für Einbettungen sowie passende Zahlen-, Datums- und Kalenderformate.
- Englische eingebaute API-Meldungen und Zeitraumbeschriftungen per Accept-Language, ohne Namen, IDs, Konfiguration oder Historie zu verändern.
- Vollständige gegliederte englische Installations-, Konfigurations-, Betriebs- und Entwicklerdokumentation neben den deutschen Anleitungen.
- 103 Backendtests einschließlich sechs Sprachtests, erweiterte Browserprüfung beider Sprachen. Schema bleibt 6, CSV bleibt 1.

## 2.5.0 · 23. November 2026

- Datenerfassung als allgemeine HTTP-GET-API mit veränderbarer Aufrufvorlage, JSON-/Klartextauswertung und Vorlagen für ioBroker, Home Assistant und evcc.
- Bearer-, Basic- und benutzerdefinierte Token-Header-Anmeldung; maskierte Geheimnisse, Erhalt beim Bearbeiten/CSV und ausdrückliches Token-Löschen.
- Bestehende ioBroker-Verbindungen werden bei unveränderten IDs und erhaltener Historie übernommen.
- Optionale Verbrauchergruppen unabhängig von Knoten: Liveleistung, Tages- und Zeitraumenergie, CSV und Backup/Restore. Gruppen beeinflussen keine Gesamtbilanz.
- Schema 6; CSV-Format unverändert 1.
- LXC-Startprüfung puffert erwartete anfängliche curl-Verbindungsfehler; echte Startfehler bleiben sichtbar und lösen einen fehlgeschlagenen Updateablauf aus.
- Formularwechsel während des Speicherns und Absenden des Gruppenformulars korrigiert.
- 97 Backendtests, Integration mit echter MongoDB und HTTP/MQTT/Modbus-Testquellen, Chromium und Produktionsbuild erfolgreich. Neue API-/Gruppen-Anleitungen ergänzt.


## 2.4.0 · 23. November 2026

- Gemeinsame Berechnung für Live-/Energiebilanz; Netzbezug, Lieferung und Speicherbewegungen nicht als zusätzliche Produktion/Verbrauch summiert.
- Hybridproduktion aus MPPT-Messung statt pauschal n. v.; ohne MPPT ausdrücklich markierte AC-/Batteriebilanz-Schätzung.
- Autarkie/Eigenverbrauch im Dashboard aus dem heutigen Energiezeitraum; Energiebilanz mit denselben Formeln für ihren Zeitraum.
- Netzfrequenz ausschließlich aus dem Netzanschluss; heutige/zeitraumbezogene Bezug- und Lieferenergie gemeinsam in der Netzkachel.
- Bezeichnungen Produktion/Verbrauch in der Oberfläche. Bestehende Richtungskennungen und IDs bleiben erhalten.
- Symmetrische Ergänzung dreiphasiger Gesamt-/Teilphasenwerte, auch RUN und Historie, mit sichtbarer Kennzeichnung. Reale Messwerte haben Vorrang.
- Phasenbezogene Knotenreste und neue historische Restphasendaten; AC-Speicher werden vorzeichenrichtig im Knoten berücksichtigt, Speicher-Invertierung korrigiert.

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
