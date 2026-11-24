# Erste Schritte: vom leeren Dashboard zur geprüften Anlage

[English](en/GETTING-STARTED.md)

[Dokumentationsübersicht](README.md) · [Datenerfassung](DATENERFASSUNG.md) · [Geräte und Knoten](GERAETE-UND-KNOTEN.md)

Nach der Installation fehlen zunächst Messquellen und Geräte. Einrichtungshinweise und „Nicht verfügbar“ sind in diesem Zustand normal. Alle folgenden Schritte finden im Browser unter `http://<SERVER-IP>:8000` statt.

## Bilanz und Phasen ab 2.4

Produktion, Verbrauch, Netzbezug/-lieferung und Speicherbewegungen sind getrennt. Autarkie und Eigenverbrauch gelten in der Übersicht für Heute, in der Energiebilanz für den gewählten Zeitraum. Produktion eines Hybrid-WR kommt aus zugeordneten MPPTs; ohne MPPT ist eine AC-/Batteriebilanz-Schätzung gekennzeichnet. Bei dreiphasiger Gesamtleistung werden fehlende Phasen symmetrisch berechnet, reale Messwerte bleiben vorrangig. Knoten zeigen ihre Restwerte auch je Phase. Alle Formeln, Messgrenzen und Grenzen der Herkunftszuordnung stehen in der [technischen Referenz](../DATENMODELL.md#bilanz-und-phasen-ab-24).

## 1. System festlegen

**System** öffnen, Anlagenname und Zeitzone setzen, z. B. `Europe/Berlin`. Zeitzone beeinflusst „Heute“ und Tagesgrenzen. Live-Aktualisierung zunächst auf **5 Sekunden**, Recorder auf **15 Sekunden** lassen und **Einstellungen speichern**.

Die Live-Aktualisierung und das Recorder-Intervall erfüllen unterschiedliche Aufgaben. Ein schnelleres Browser-Polling ersetzt keine feinere Aufzeichnung. Der Recorder erfasst alle eingerichteten Protokolle.

## 2. Eine Verbindung anlegen

Unter **Datenerfassung → Verbindung hinzufügen** Protokoll, Host/IP und Port eintragen. Beispiel: Protokoll API / HTTP, Vorlage ioBroker mit Host `192.168.10.20` und simple-api-Port `8087`. Host ohne `http://`, Port separat. Verbindung aktivieren und speichern.

Nicht das alte globale ioBroker-Feld unter System als Ersatz für neue Messpunktverbindungen verwenden. Es bleibt für direkte Altzuordnungen verfügbar. [Protokollanleitungen](DATENERFASSUNG.md).

## 3. Einen bekannten Messpunkt prüfen

**Messpunkt hinzufügen**, Verbindung auswählen, Name, Einheit und Quelladresse setzen. Leistung zuerst in **W**, Faktor **1**, Offset **0**, sofern die Quelle bereits W liefert. Aktiv und „Rohwert aufzeichnen“ einschalten.

In **Messpunkte und Diagnose** prüfen:

- Rohwert entspricht der Quelle.
- Normalisierter Wert und Einheit sind korrekt.
- Empfangszeit ist aktuell bzw. bei MQTT innerhalb der Gültigkeit.
- Ein kontrollierter Lastwechsel erscheint auch im Dashboard.

Beispiel: Quelle liefert 1.234 W. Mit W und Faktor 1 muss 1234 erscheinen. Nicht gleichzeitig Faktor 0.001 anwenden und das Gerät weiter auf W stellen.

## 4. Netzanschluss zuerst einrichten

Unter **Konfiguration → Netzanschluss hinzufügen**:

1. Name und Leistungsdatenpunkt auswählen.
2. Einen vorzeichenbehafteten Wert oder zwei getrennte Richtungswerte wählen.
3. Vorzeichen prüfen: **positiv = Bezug, negativ = Einspeisung** beim vorzeichenbehafteten Netz.
4. Optional getrennte kumulative Zähler für Bezug und Lieferung zuordnen.
5. Speichern. Die gemeinsame Netzkachel muss oben mittig erscheinen.

Getrennte Richtungswerte werden als zwei Einträge vom Typ Netzanschluss angelegt, aber gemeinsam dargestellt. Nicht zusätzlich einen vorzeichenbehafteten Anschluss aktiv lassen. [Details](GERAETE-UND-KNOTEN.md#netzanschluss).

## 5. Abschnitt und erstes Gerät einrichten

Einen **Knoten** anlegen, bei vorhandenem Abschnittszähler dessen Leistung zuordnen. Danach einen Verbraucher mit eigenem Leistungswert hinzufügen und unter **Knoten / Anschluss** diesem Knoten zuordnen.

Die Knotenkachel im Diagramm öffnen: Kindgerät und automatischer Rest müssen erkennbar sein. Der Zähler selbst ist kein zusätzlich manuell anzulegendes Verbrauchsgerät. Mit einem zweiten gemessenen Gerät muss sich der Rest entsprechend ändern.

Weitere Abschnitte erst nach diesem Vergleich ergänzen. [Bilanzbeispiele](GERAETE-UND-KNOTEN.md#knoten-und-restbilanz).

## 6. PV, Generator und RUN-Geräte ergänzen

- Normaler PV-WR: Gerät, Kategorie Photovoltaik, Typ WR, Richtung Erzeugung/Produktion.
- Generator/BHKW: Gerät, Kategorie Generator/BHKW, Richtung Produktion; optionale Betriebswerte zuordnen.
- RUN-Gerät: festen Wattwert und RUN-Datenpunkt hinterlegen; nur sinnvoll, wenn die feste Leistung den Betrieb ausreichend beschreibt.
- Hybrid-WR mit Batterie: zuerst Speicher und DC-MPPTs anlegen, danach den Hybrid verknüpfen. [Eigene Anleitung](SPEICHER-UND-HYBRID.md).

## 7. Historie prüfen

Unter **System** muss der Recorder aktiv sein und Messwerte schreiben. Unter **Energie** einen Zeitraum wählen, in dem bereits mindestens zwei geeignete Messwerte vorhanden sind. Ein gerade angelegter Zähler liefert noch keinen vergangenen Tagesertrag.

Methoden, Datenabdeckung und Lücken beachten. RUN-Energie ist geschätzt. DC-MPPT- und Speicherenergie stehen separat; die AC-Summen sind keine Summe aller sichtbaren Zeilen. [Begriffe](GLOSSAR.md).

## 8. Darstellung und Einbettung wählen

Unter **Darstellung** Layout und Farben speichern. Standardmäßig verschwinden Geräte erst nach 60 Sekunden mit **−1 W < Leistung < +1 W**. Netz, Knotenstruktur und Speicher bleiben sichtbar. „Inaktive anzeigen“ hebt den Darstellungsfilter auf.

Die Ansicht ohne Navigation liegt unter `/flow`. [Darstellung und iframe](DARSTELLUNG-UND-EINBETTUNG.md).

## 9. Konfiguration sichern

Eine **Gesamtkonfiguration CSV** herunterladen. Sie erhält Zuordnungen, enthält aber keine vollständigen Zugangsdaten und keine Messhistorie. Zusätzlich eine [Datenbanksicherung](BETRIEB-UND-UPDATES.md) erstellen und außerhalb des Servers aufbewahren.

## 10. Abnahme vor dem Dauerbetrieb

| Prüfung | Erwartung |
|---|---|
| Netz bei bekanntem Verbrauch | Bezug in plausibler Höhe |
| Netz bei tatsächlicher Einspeisung | Lieferung statt zusätzlichem Bezug |
| Geräteleistung | Richtige Einheit und Größenordnung |
| Knoten mit Kindern | Kindersumme und Rest ergeben den Zähler netto |
| DC-MPPT | Keine Phasen, DC-Leistung und ggf. Gesamtzähler |
| Speicher | SOC plausibel, Laden/Entladen richtig herum, Kapazität pro gesamtem Speicher |
| Hybrid | Messgrenze eindeutig; keine Netzdurchleitung als Erzeugung |
| Quellenunterbrechung | Fehlender/veralteter Wert statt angenommener Null |
| Historie | Recorder schreibt, nachvollziehbare Methode/Abdeckung |
| Neustart | Daten und Zuordnungen bleiben erhalten |
| Sicherung | Vollständiges Backup vorhanden; Rückweg bekannt |

Erst danach die Anlage schrittweise auf 30–50 Geräte erweitern. Für Serienänderungen [CSV](../CSV-IMPORT.md) verwenden.

## Verbraucher zusätzlich gruppieren

Unter Konfiguration zuerst [Verbrauchergruppen](VERBRAUCHERGRUPPEN.md) anlegen und anschließend bei den gewünschten Verbrauchern auswählen. Die Knotenzuordnung bleibt bestehen.
