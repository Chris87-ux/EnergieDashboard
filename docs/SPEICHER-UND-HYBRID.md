# Speicher, DC-MPPT und Hybrid-Wechselrichter

[Dokumentationsübersicht](README.md) · [Datenquellen](DATENERFASSUNG.md) · [Technische Felder](../DATENMODELL.md)

## Bilanz und Phasen ab 2.4

Produktion, Verbrauch, Netzbezug/-lieferung und Speicherbewegungen sind getrennt. Autarkie und Eigenverbrauch gelten in der Übersicht für Heute, in der Energiebilanz für den gewählten Zeitraum. Produktion eines Hybrid-WR kommt aus zugeordneten MPPTs; ohne MPPT ist eine AC-/Batteriebilanz-Schätzung gekennzeichnet. Bei dreiphasiger Gesamtleistung werden fehlende Phasen symmetrisch berechnet, reale Messwerte bleiben vorrangig. Knoten zeigen ihre Restwerte auch je Phase. Alle Formeln, Messgrenzen und Grenzen der Herkunftszuordnung stehen in der [technischen Referenz](../DATENMODELL.md#bilanz-und-phasen-ab-24).

## Vorher die Messgrenzen festlegen

Bei DC-gekoppelten Systemen sind PV-Leistung, Batterieleistung und AC-Abgabe verschiedene Werte. Beispiel:

```text
PV → MPPT → gemeinsamer DC-Bus ↔ Batterie
                         ↕
                     Hybrid-WR
                     AC-In / AC-Out
```

Nicht dieselbe Energie an mehreren Stellen als zusätzliche PV-Erzeugung zählen. DC-MPPTs und Speicher erscheinen deshalb separat. Der Hybrid stellt den bidirektionalen Wandler an seiner **AC-Messgrenze** dar. Für ein Victron-System die konkret verfügbaren Datenpunkte, Einheiten und Vorzeichen prüfen; universelle Registerzuordnungen gibt es hier nicht.

## 1. Gesamten Speicher anlegen

**Konfiguration → Speicher hinzufügen**. Jeder Eintrag beschreibt einen vollständigen Speicher, keine einzelnen Module.

| Einstellung | Bedeutung |
|---|---|
| Feste Gesamtkapazität | kWh des ganzen Speichers, z. B. 10 |
| AC/DC | Tatsächliche Anschlussseite; Hybrid-verknüpfte Batterie muss DC sein |
| Leistung | Vorzeichenbehaftete gesamte Batterieleistung, W oder kW |
| Lade-Vorzeichen | Gibt an, welches Vorzeichen der normalisierten Quelle beim Laden gilt |
| SOC | Datenpunkt in %, 0 bis 100 |
| SOC-Reserve | Optionaler Datenpunkt in % oder fester Reservewert |
| Maximale Balkenleistung | Nur Skalierung der Anzeige; keine Ladebegrenzung |
| Knoten | Organisatorische Zuordnung; kein zusätzlicher AC-Verbrauchsfluss |

Bei **DC** entfallen Phasenfelder. Bei AC können Gesamtleistung oder vollständige dreiphasige Werte verwendet werden. Batterieanzeige und Energiekanäle bleiben trotzdem vom normalen AC-Summieren getrennt.

### Vorzeichen prüfen

Während eines eindeutig erkennbaren Ladevorgangs die Quelldaten beobachten und das passende **Lade-Vorzeichen** wählen. Eine zusätzliche allgemeine Vorzeichenumkehr wirkt davor; nicht versehentlich zweimal umkehren. Die Anzeige muss danach „Laden“ zeigen und bei Entladung die andere Seite des Balkens.

### SOC-Reserve und Restlaufzeit

Ohne Reserve-Datenpunkt gilt der feste Wert. Ist ein Datenpunkt zugeordnet, ersetzt er den festen Wert. Ist dieser Wert nicht verfügbar/ungültig, bleibt die davon abhängige Laufzeit unbekannt.

```text
Restenergie = Kapazität × SOC / 100
Bis Reserve nutzbar = Kapazität × max(SOC − Reserve, 0) / 100
```

Die Restlaufzeit verwendet ein exponentiell geglättetes 5-Minuten-Leistungsmaß. Sie erscheint nur bei aktueller **und** geglätteter Entladung über 50 W. Bei Laden oder sehr kleiner Entladung gibt es keine belastbare Restlaufzeit. Nach Serverneustart oder längerer Messlücke beginnt die Glättung neu. Energieinhalt und Laufzeit sind Schätzungen ohne Alterungs-, Temperatur- oder Verlustmodell.

### Mehrere Speicher

Ab zwei Speichern erscheint ein Gesamtspeicher. Sein SOC wird **mit den Kapazitäten gewichtet**, nicht einfach gemittelt:

```text
10 kWh bei 80 % + 5 kWh bei 20 %
= 9 kWh Restenergie bei 15 kWh Gesamtkapazität
= 60 % Gesamt-SOC
```

Fehlender SOC oder fehlende Kapazität macht den Gesamt-SOC unbekannt. Gleichzeitig ladende und entladende Speicher werden im gemeinsamen Leistungsbalken saldiert; Einzelanzeigen bleiben erhalten.

## 2. DC-MPPT anlegen

**Neuer Fluss → Gerät → Photovoltaik → DC-MPPT**.

1. DC-Leistungsdatenpunkt zuordnen: **Ausgang des MPPT zum DC-Bus**.
2. Optional kumulativen **Gesamtenergie-DC-Zähler** dieses Ausgangs zuordnen.
3. Leistungseinheit W/kW und Zählereinheit Wh/kWh kontrollieren.
4. Optional Knoten zur Orientierung zuordnen und speichern.

Keine Phasen, Netzfrequenz oder RUN-Schätzung konfigurieren. Ein Tagesertrag, der jeden Tag nullt, ist nicht dasselbe wie ein dauerhaft kumulativer Gesamtzähler; bevorzugt den echten Gesamtzähler verwenden.

Live erscheint der aktuelle Gesamtzähler. Im Energiebericht wird die Differenz im gewählten Zeitraum berechnet. Ohne Zähler kann aufgezeichnete Leistung integriert werden. DC-Energie wird separat gekennzeichnet und nicht nochmals in die AC-Gesamtsumme addiert.

## 3. Hybrid-WR anlegen und verknüpfen

Zuerst Speicher und MPPTs speichern, dann **Gerät → Photovoltaik → Hybrid-WR**:

1. AC-Leistung des Wandlers bzw. seine tatsächlichen AC-Ports auswählen.
2. Mindestens einen zuvor angelegten **DC-Speicher** zuordnen.
3. Zugehörige DC-MPPTs auswählen.
4. AC-Knoten des tatsächlichen Anschlusses wählen.
5. AC-Messmodus und ggf. DC-Messung für Wirkungsgrad konfigurieren.

Ein Speicher/MPPT kann jeweils nur einem Hybrid zugeordnet sein. Vor Umtypisierung, Wechsel eines verknüpften DC-Speichers auf AC oder Löschen die Verknüpfung im Hybrid entfernen. Nicht zum Hybrid gehörende Speicher bleiben eigenständige Speicher.

## 4. AC-Messmodus richtig wählen

### A. WR-Nettoleistung

Nur verwenden, wenn der ausgewählte Wert bereits die reine **bidirektionale Wandlerleistung** darstellt:

- Positiv = DC → AC, AC-Abgabe.
- Negativ = AC → DC, AC-Aufnahme/Netzladung.

Gesamtwert oder vollständige Phasenwerte zuordnen. Bei abweichendem Quellvorzeichen die AC-Vorzeichenumkehr verwenden.

### B. AC-Out minus AC-In

Wenn AC-Out auch Netz-Durchleitung enthält:

- Gesamtleistung/Phasenfelder = tatsächlicher **AC-Out**.
- Zusätzlich **AC-In Gesamtleistung** zuordnen.
- Beide Portmessungen in derselben AC-Einheit bereitstellen.

```text
AC netto = AC-Out − AC-In
2.950 W − 2.000 W = 950 W Wandlerabgabe
```

Positiv an AC-In bedeutet in den WR, positiv an AC-Out aus dem WR; Rückfluss kann negativ sein. Die allgemeine AC-Vorzeichenumkehr kehrt **beide** Portwerte um. Falls die Quellen unterschiedliche Konventionen besitzen, den betreffenden Messpunkt mit Faktor −1 normalisieren.

Ein Netzzähler für das ganze Grundstück ist kein Ersatz für AC-In am WR. Alle relevanten Portwerte müssen dieselbe Systemgrenze abbilden. Bei dreiphasiger Konfiguration wird die Nettoleistung ohne entsprechende Port-Phasenmessungen symmetrisch aufgeteilt und als berechnet markiert; dies ist keine gemessene Phasenbilanz.

## 5. Wirkungsgrad konfigurieren

### Bevorzugt: DC-Leistung direkt am Wandler

Unter Datenpunkte **DC-Leistung direkt am WR** auswählen. Gemeint ist die Leistung über die DC-Schnittstelle **des Wandlers**, nicht allein Batterie- oder MPPT-Leistung. Einheit W/kW und separate DC-Vorzeichenumkehr setzen:

- Positiv = DC → AC.
- Negativ = AC → DC.

Die direkte Messung hat Vorrang. Ist ihr Datenpunkt konfiguriert, liefert aber keinen Wert, wird nicht stillschweigend auf eine andere Berechnung gewechselt.

### Alternative: bestätigte vollständige DC-Busbilanz

Nur wenn wirklich sämtliche Quellen, Speicher und weiteren DC-Lasten am betrachteten Bus erfasst sind, **„DC-Bilanz vollständig“** aktivieren. Weitere DC-Lasten optional als Datenpunkt zuordnen.

```text
DC netto am WR = MPPT-Ausgänge + Batterieentladung
                − Batterieladung − weitere DC-Lasten
```

Das Ergebnis wird als **Schätzung aus DC-Bilanz** gekennzeichnet. Fehlt eine konfigurierte Quelle oder liegt die Messgrenze falsch, ist kein verlässlicher Wirkungsgrad ableitbar. Zeitlich nicht passende Messwerte können trotz richtiger Zuordnung unplausible Ergebnisse erzeugen.

### Berechnung und Beispiele

| Betriebsfall | Beispiel | Wirkungsgrad |
|---|---|---|
| DC → AC | DC 1.000 W, AC netto 950 W | 950/1.000 = 95 % |
| PV lädt gleichzeitig Batterie | MPPT 2.000 W, Ladung 1.000 W, AC netto 950 W | DC netto 1.000 W → 95 % |
| Netzladung | AC netto −1.000 W, DC netto −900 W | 900/1.000 = 90 % |
| Nur PV → Batterie, Wandler ruht | AC netto nahe 0 | Kein AC-Wandlerwirkungsgrad |

Standard-Mindestleistung: **100 W auf beiden Wandlerseiten**. Fehlende Werte, kleinere Leistung, gegensätzliche AC-/DC-Vorzeichen oder rechnerisch mehr als 100 % ergeben einen Hinweis statt eines scheinbar gültigen Wertes. Verluste sind Wandlereingang minus Wandlerausgang. MPPT-/Batterieverluste gehören nicht automatisch zu diesem Wirkungsgrad.

Ein durch das Victron-System bereits berechneter DC-Wert ist keine unabhängige Messung des Wirkungsgrads. Für die Beurteilung die Herkunft der Quelle beachten; technische Orientierung: [Victron dbus-systemcalc](https://github.com/victronenergy/dbus-systemcalc-py).

## 6. Bilanz und Kontrolle

Hybrid-AC-Abgabe kann Batterieentladung enthalten. Sie darf nicht pauschal als reine PV-Erzeugung bezeichnet werden; daher werden zugeordnete MPPT-Messungen oder gekennzeichnete Schätzungen verwendet. Netzbezug/Lieferung bleiben messbar. Die Energie-Produktion-/Verbrauchsummen sind Summen definierter Messgrenzen, kein automatisch deduplizierter Gesamt-PV-Ertragszähler.

Nach der Einrichtung drei echte Betriebsfälle prüfen: PV-Erzeugung, Batterieladung und Batterieentladung bzw. Netzladung. AC-In/Out und DC-Messung jeweils mit den Originalwerten vergleichen. Bestehende Hybrid-Konfigurationen bleiben nach dem Update im Modus „Nettoleistung“; wenn bisher AC-Out zugeordnet war, den Modus bewusst korrigieren. Frühere fehlerhafte abgeleitete Historie wird nicht rückwirkend neu berechnet.
