# Netz, Geräte und Knoten konfigurieren

[English](en/DEVICES-AND-NODES.md)

[Dokumentationsübersicht](README.md) · [Messpunkte vorbereiten](DATENERFASSUNG.md) · [Speicher und Hybrid](SPEICHER-UND-HYBRID.md)

## Bilanz und Phasen ab 2.4

Produktion, Verbrauch, Netzbezug/-lieferung und Speicherbewegungen sind getrennt. Autarkie und Eigenverbrauch gelten in der Übersicht für Heute, in der Energiebilanz für den gewählten Zeitraum. Produktion eines Hybrid-WR kommt aus zugeordneten MPPTs; ohne MPPT ist eine AC-/Batteriebilanz-Schätzung gekennzeichnet. Bei dreiphasiger Gesamtleistung werden fehlende Phasen symmetrisch berechnet, reale Messwerte bleiben vorrangig. Knoten zeigen ihre Restwerte auch je Phase. Alle Formeln, Messgrenzen und Grenzen der Herkunftszuordnung stehen in der [technischen Referenz](../DATENMODELL.md#bilanz-und-phasen-ab-24).

## Typ und Kategorie unterscheiden

Unter **Konfiguration** gibt es die Typen **Gerät**, **Knoten**, **Netzanschluss** und **Speicher**. Die Kategorie beschreibt ein Gerät genauer, z. B. Photovoltaik, Generator/BHKW, Wärmepumpe, E-Auto, Verbraucher oder Benutzerdefiniert. Netz und Speicher sind eigene Typen, keine auszuwählenden Gerätekategorien.

| Typ | Zweck | Wesentliche Angaben |
|---|---|---|
| Gerät | Einzelverbraucher/-erzeuger | Richtung, Leistungswert oder RUN |
| Knoten | Abschnitt mit Kindern, optional eigenem Zähler | Übergeordneter Knoten, optional Nettoleistung |
| Netzanschluss | Bezug/Lieferung an der Anlage | Hauptebene, Messmodell und Leistung |
| Speicher | Gesamte Batterie | AC/DC, Kapazität, SOC, signed Leistung |

Name, Symbol und Farbe beeinflussen die Darstellung. **Anzeigereihenfolge** sortiert kleinere Zahlen zuerst und verändert keine Zuordnung, Messung oder Bilanz. Ein Wert 10 erscheint vor 100.

## Netzanschluss

### Ein vorzeichenbehafteter Leistungswert

1. **Netzanschluss hinzufügen**, Namen setzen.
2. Vorzeichenbehafteten Netzmodus wählen.
3. Gesamtleistung oder vollständige Phasenwerte auswählen, Leistungseinheit kontrollieren.
4. Quelle prüfen: **positiv Bezug, negativ Einspeisung**. Bei umgekehrter Quelle „Vorzeichen umkehren“ verwenden.
5. Optional getrennte kumulative Energiezähler für Bezug und Einspeisung zuordnen.

Eine einzige dauerhafte Kachel zeigt beide Richtungen oben mittig. Bei 0 W bleibt sie sichtbar.

### Getrennte Richtungswerte

Zwei Einträge vom Typ Netzanschluss mit getrenntem Richtungsmodus anlegen:

- **Produktion/Bezug**: Datenpunkt für die aktuelle Bezugsleistung.
- **Verbrauch/Lieferung**: Datenpunkt für die aktuelle Einspeiseleistung.

Die Werte müssen die jeweilige Richtung eindeutig abbilden. Nicht zusätzlich das signed Modell aktivieren. Höchstens ein aktiver Anschluss je Richtung bzw. ein signed Anschluss ist vorgesehen. Mindestens ein aktiver Netzanschluss bleibt erforderlich; den letzten erst nach Anlegen eines Ersatzes deaktivieren/löschen.

Netzanschlüsse liegen auf der **Hauptebene** und sind AC-Messungen. Sie erhalten keinen übergeordneten Knoten. Ein Haus-/Abschnittszähler gehört nur dann zusätzlich als Knoten hinein, wenn er eine andere sinnvolle Messgrenze beschreibt. Ein zusätzlicher normaler Verbraucher mit demselben vollständigen Hausverbrauch führt sonst zu Doppelzählung.

## Gerät mit Leistungssensor

1. **Neuer Fluss**, Typ Gerät und passende Kategorie auswählen.
2. Richtung: Verbraucher = Verbrauch, Erzeuger = Produktion.
3. Unter „Knoten / Anschluss“ den tatsächlichen Abschnitt wählen; ohne Zuordnung bleibt das Gerät auf der Hauptebene.
4. Gesamtleistung und optional Energiezähler auswählen. Bei dreiphasiger Messung die tatsächlich verfügbaren L1–L3-Werte zuordnen.
5. Einheiten prüfen, speichern und mit der Quelle vergleichen.

Normale Verbraucher/Erzeuger behalten das Quellvorzeichen in der Liveanzeige. Für die Bilanz bestimmt die **konfigurierte Rolle** den Betrag: −2.000 W eines Erzeugers zählen als 2.000 W Erzeugung. „Vorzeichen umkehren“ ändert bei normalen Geräten nicht diese feste Rolle. Einen tatsächlich bidirektionalen Netzanschluss oder Hybrid-WR deshalb mit dem passenden Typ/Modus konfigurieren.

### Phasen und Gesamtwerte

- Einphasig nur einstellen, wenn die Zuordnung tatsächlich bekannt ist.
- Bei dreiphasiger Leistung kann eine Gesamtleistung verwendet werden; sonst müssen alle drei Phasen für eine vollständige Summe verfügbar sein.
- Leistungs- und Energiezählerfelder sind unabhängig. Ein Gesamtzähler liefert keine gemessene Phasenaufteilung.
- DC-MPPT und DC-Speicher haben keine AC-Phasenzuordnung.
- Abgeleitete Knotenrest-/Hybridkanäle zeigen Gesamtenergie; aus einer gesamten Differenzmessung werden keine Phasenwerte erfunden.

## Gerät nur mit RUN-Signal

Im Datenpunkt-Reiter **RUN** aktivieren, eine feste Leistung in W und den RUN-Messpunkt zuordnen. `true` bzw. jeder Zahlenwert ungleich 0 bedeutet Betrieb, `false`/0 bedeutet aus.

Beispiel: Pumpe mit angesetzten 200 W läuft 30 Minuten → geschätzte Energie **0,1 kWh**. Die laufende feste Leistung erscheint live. Energie entsteht aus der aufgezeichneten RUN-Zeit, nicht aus einer angenommenen rückwirkenden Laufzeit. Fehlende Signale gelten nicht als „aus“.

RUN ist für Geräte geeignet, deren Leistungsansatz sinnvoll ist. Bei stark variierender Leistung einen echten Sensor verwenden. RUN wird bei DC-MPPT und Hybrid-WR nicht angeboten; dort sind Messwerte erforderlich.

## Generator / BHKW

Gerät, Kategorie **Generator/BHKW**, normalerweise Richtung Produktion wählen. Zusätzlich zur elektrischen Leistung sind optionale Datenpunkte möglich:

| Datenpunkt | Erwartete Einheit |
|---|---|
| Motortemperatur | °C |
| Effizienz | % |
| Kraftstoffverbrauch | Gewählte Einheit, z. B. L/h, L, m³/h, m³, kg/h oder kg |
| Betriebsstunden | h |

Diese Werte werden angezeigt, nicht aus Leistung oder Kraftstoff automatisch berechnet. Eine Mengenangabe in L ist kein Verbrauch pro Stunde. Betriebssekunden im Messpunkt in Stunden umrechnen. Die Generator-Effizienz ist ein gelieferter Messwert; die Hybrid-Effizienz hat eine eigene Berechnung.

## Knoten und Restbilanz

### Struktur aufbauen

Zuerst Knoten anlegen, danach Kinder zuordnen. Knoten können Knoten enthalten. Beispiel:

```text
Hauptebene
└── Hof (Abschnittszähler)
    ├── Werkstatt (Unterzähler)
    │   ├── Maschine (Sensor)
    │   └── Pumpe (RUN)
    └── Dach-PV (AC-WR)
```

Knoten werden im Flussdiagramm in eigener rechteckiger Form gezeigt. Anklicken öffnet die Kinder; die Pfadleiste führt zurück. Die Hauptansicht zeigt die aktuelle Ebene und nicht sämtliche Nachfahren gleichzeitig. Große Ebenen sind auf mehrere Diagrammseiten aufgeteilt.

### Mit eigenem Abschnittszähler

Der Zähler misst **netto**, positiv Verbrauch und negativ Erzeugung. Ohne Kinder zeigt der automatische Rest den ganzen Messwert. Sobald Kinder eigene Werte besitzen, werden sie gegengerechnet.

```text
Rest = Zähler netto − Kinder netto
Kinder netto = Verbraucher − Erzeuger + Unterknoten netto
```

Beispiel: Knoten 1.000 W, Motor 300 W, RUN-Pumpe 200 W, PV-Erzeugung 100 W:

```text
Kinder netto = 300 + 200 − 100 = 400 W
Restverbrauch = 1.000 − 400 = 600 W
```

Bei negativem Rest erscheint Resterzeugung. Nicht manuell nochmals einen Verbraucher/Erzeuger mit dem ganzen Abschnittszähler anlegen. Die automatischen Restkanäle übernehmen genau diese Aufgabe.

### Verschachtelung und fehlende Daten

Ein **gemessener Unterknoten** geht beim Elternknoten einmal mit seinem Zähler-Netto ein. Seine Kinder werden dort nicht nochmals abgezogen. Ein **ungemessener Unterknoten** ist eine Gruppe und liefert seine Kindersumme.

Fehlt ein notwendiger Zähler-/Kinderwert, bleibt der Rest unbekannt. Restwerte enthalten auch ungemessene Lasten, Verluste und zeitliche Messabweichungen; sie sind keine automatische Korrektur falscher Sensorzuordnungen. DC-MPPTs und DC-Speicher bleiben aus dieser AC-Restverrechnung herausgenommen; AC-Speicher werden vorzeichenrichtig verrechnet.

Kreise sind verboten. Zum Löschen eines Knotens zuerst seine Kinder verschieben. Deaktivieren eines Knotens deaktiviert auch seine Unterstruktur für Anzeige und Aufzeichnung. Umhängen verändert die aktuelle Topologie, aber berechnet alte Resthistorie nicht rückwirkend neu.

## Kontrolle nach Änderungen

Einen bekannten Verbraucher einschalten und sowohl Kind als auch Rest beobachten. Der ganze Abschnitt darf sich nur um die reale zusätzliche Last ändern. Danach CSV sichern und die Historie ab dem Änderungszeitpunkt prüfen. Bei Problemen: [Fehlersuche](FEHLERSUCHE.md).
