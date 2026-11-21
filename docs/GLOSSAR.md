# Begriffe und Einheiten

[Dokumentationsübersicht](README.md)

| Begriff | Bedeutung in Energieboard |
|---|---|
| W / kW | Momentane Leistung. 1 kW = 1.000 W. |
| Wh / kWh | Energie über Zeit. 1 kWh = 1.000 Wh. 200 W für 30 min = 0,1 kWh. |
| Gesamtenergie-Zähler | Kumulativer Energiezählerstand; ein Zeitraumwert entsteht durch Differenzen. |
| AC / DC | Wechselstrom-/Gleichstrom-Messseite. DC besitzt keine L1–L3-Zuordnung. |
| Messgrenze | Stelle, über die Energie gemessen wird, z. B. Netzanschluss, WR-Port oder Batterie. |
| Netzbezug / Lieferung | Energie aus dem öffentlichen Netz bzw. in dieses Netz; signed Leistung positiv/negativ. |
| Zufluss / Abfluss | Konfigurierte Bilanzrolle, kein universelles Quellvorzeichen. |
| Knoten | Abschnitt/Gruppe mit Kindern und optionalem Nettozähler. |
| Restverbrauch / Resterzeugung | Differenz zwischen Abschnittszähler und bekannten Kindbeiträgen. Enthält auch Verluste/Messabweichungen. |
| RUN | Betriebssignal; zusammen mit fester Wattzahl eine Leistungsschätzung. |
| SOC | Ladezustand in Prozent. |
| SOC-Reserve | Untergrenze für die berechnete nutzbare Restenergie/Laufzeit; keine aktive Batterieregelung. |
| Kapazitätsgewichteter SOC | Restenergie aller Speicher geteilt durch Gesamtkapazität. |
| Hybrid-WR | Bidirektionaler AC/DC-Wandler mit zugeordnetem DC-Speicher und optionalen DC-MPPTs. |
| MPPT | PV-Laderegler; hier wird seine DC-Ausgangsleistung zum Bus verwendet. |
| AC-In / AC-Out | Tatsächliche AC-Ports des WR; AC-Out kann Netz-Durchleitung enthalten. |
| Wirkungsgrad | Nutzbare Wandlerausgangsleistung geteilt durch Wandleraufnahme; Messgrenzen/Richtung beachten. |
| Autarkie | Kennzahl zum gemessenen AC-Verbrauch und Netzbezug, bezogen auf den tatsächlich erfassten Anlagenumfang. |
| Eigenverbrauch | Nutzung eigener Erzeugung; bei gemischter Hybrid-AC-Abgabe nicht sicher aus dieser allein ableitbar. |
| `counter_delta` | Energie aus Zählerdifferenzen mit Resetbehandlung. |
| `power_integral` | Energie aus zeitlicher Integration gemessener Leistung. |
| `run_estimate` | Energie aus aufgezeichnetem RUN-Signal und fester Leistung. |
| `phase_sum` | Summe geeigneter vollständiger Phasenwerte. |
| Abdeckung / Lücke | Zeitliche Vollständigkeit der Auswertung; nicht mit elektrischer Effizienz verwechseln. |
| Nicht verfügbar | Wert fehlt, ist veraltet oder nicht zuverlässig berechenbar; nicht gleich 0. |
| `point:<id>` | Stabiler Verweis auf einen Messpunkt, unabhängig von Anzeigename/Quelladresse. |
| Recorder | Dienst zur lokalen Messwertaufzeichnung. |
| CSV-Export | Konfigurationsaustausch ohne vollständige Zugangsdaten und ohne Historie. |
| Datenbankbackup | Vollständiger gesicherter Datenstand einschließlich Historie und Zugangsdaten. |
| Tag / `main` | Fester Release-Stand bzw. veränderlicher Entwicklungs-/Hauptzweig. |

Die Werte sind keine Regelbefehle. Reserve, Kapazität und Balkenskala verändern das reale Verhalten der Geräte nicht.
