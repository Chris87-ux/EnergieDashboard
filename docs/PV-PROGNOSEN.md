# PV-Prognosen einrichten und bewerten

[Dokumentation](README.md) · [English](en/PV-FORECASTS.md)

Ab Version 2.7 unter **PV-Prognose** (`/prognose`). Alle Quellen sind zunächst deaktiviert. Du benötigst Internetzugriff des Servers über HTTPS, eine korrekte Systemzeit und aufgezeichnete PV-Istwerte. Die kostenlosen Angebote sind für die hier vorausgesetzte private Nutzung gedacht; aktuelle Kontobedingungen und Limits beim Anbieter prüfen.

## 1. Zuerst eine zuverlässige Istmessung

Unter **Datenerfassung** die DC-Leistung und möglichst den kumulativen PV-Energiezähler aufzeichnen. Bei reinen PV-Wechselrichtern darf alternativ der reine AC-PV-Ertrag verwendet werden. Unter **Konfiguration** den zugehörigen DC-MPPT oder PV-Wechselrichter anlegen und die Einheiten kontrollieren.

**Nicht den AC-Ausgang eines Hybrid-WR als PV-Ertrag verwenden:** Dort stecken Laden/Entladen und eventuell Netzenergie mit drin. Mehrere MPPTs dürfen addiert werden, wenn sie unterschiedliche Flächen messen. Weder denselben Zähler zweimal noch Gesamtzähler und dessen Teilzähler gemeinsam auswählen. Identische Datenpunktzuordnungen werden abgewiesen; überlappende physische Messgrenzen musst du selbst vermeiden.

Kumulative Energiezähler haben Vorrang vor Leistungsintegration. Datenlücken bleiben als unvollständig sichtbar. Für das Lernen muss ein ganzer abgeschlossener Tag vollständig und mit mindestens 98 % Zeitabdeckung vorliegen. Die Aufzeichnung beginnt erst ab Aktivierung; alte Erträge werden nicht erfunden.

## 2. PV-Anlage anlegen

1. **PV-Anlage hinzufügen**, Namen, Breiten-/Längengrad und gegebenenfalls Zeitzone eintragen. Leer bedeutet Systemzeitzone.
2. PV-Istquellen auswählen. Messseite **DC**, **AC** oder bewusst **gemischt** festlegen. Für einen Victron-DC-Bus sind die MPPT-Erträge normalerweise die passende Referenz.
3. Jede physische Fläche mit installierter **kWp**, Neigung und Azimut anlegen. Süd = 0°, Ost = −90°, West = 90°, Nord = ±180°; waagerecht = 0° Neigung.
4. **Tagesanfangsprognose festhalten um** einstellen, standardmäßig **00:05 lokale Zeit**. Zur fairen Bewertung muss die Prognose davor eingetroffen sein. Am Einrichtungstag nach diesem Zeitpunkt gibt es daher gewöhnlich noch keine Morgenprognose.
5. Lernfenster standardmäßig **45 Tage**, Mindestzahl **7 gültige Tage**. Für Open-Meteo wird der lokale PV-Ertrag mit kWp × geneigter Einstrahlung × Ertragsfaktor modelliert; Standardfaktor 0,85 an Messseite und Anlage anpassen. Eine optionale AC-Grenze begrenzt die gemeinsame Leistung aller Flächen nur bei Messseite AC.
6. Optional ein aktiv aufgezeichnetes Bool-Signal für **Abregelung** auswählen: 1 bedeutet Abregelung. Jeder Tag mit aktivem Signal oder lückenhaftem Signal wird vom Lernen ausgeschlossen.
7. Anlage aktivieren und speichern. Anschließend Quellen hinzufügen und einzeln aktivieren.

## 3. Vier Quellen

| Quelle | Einrichtung | Besonderheiten |
|---|---|---|
| Victron VRM | Persönlicher Zugriffstoken und Installations-ID aus VRM | Native PV-Prognose einer bereits in VRM erfassten Anlage. Standort und Ertragshistorie müssen dort vorhanden sein. Header `X-Authorization: Token …`; kein veralteter Bearer-Login. |
| Forecast.Solar | Kein Konto für die öffentliche kostenlose Schnittstelle | Heute und morgen. Die lokale Flächenkonfiguration wird an die API übergeben; jeder Flächenabruf zählt einzeln. Verfügbarkeit kann durch Wartung eingeschränkt sein. |
| Solcast Hobbyist | Privates Hobbyist-Konto, Token und ein bis zwei Ressourcen-IDs der Dachflächen | Anbieterlimit typischerweise zehn Anfragen/UTC-Tag. Energieboard reserviert höchstens **acht** pro Token/UTC-Tag; zwei Flächen benötigen zwei Anfragen pro Aktualisierung. Weitere Programme mit demselben Token verbrauchen zusätzlich Anbieterbudget. |
| Open-Meteo | Kein Token | Kostenlose Wetter-API für private Nutzung. **Lokales PV-Modell aus Einstrahlung**, kein fertiger PV-Ertragsdienst. Verschattung, Schnee und reale Temperaturverluste werden nicht vollständig modelliert. Attribution bleibt sichtbar. |

Anbieteranleitungen: [VRM API](https://vrm-api-docs.victronenergy.com/), [VRM-Prognose und Solcast](https://professional.victronenergy.com/news/detail/212/), [Forecast.Solar](https://forecast.solar/), [Solcast Hobbyist](https://docs.solcast.com.au/docs/section/rooftop-sites-hobbyist), [Open-Meteo](https://open-meteo.com/en/docs), [Open-Meteo-Nutzungsbedingungen](https://open-meteo.com/en/pricing).

Regelmäßiger Abruf ungefähr alle sechs Stunden, Prüfung des Zeitplans jede Minute. Lokale Limits gelten zusätzlich: VRM 48/Tag und 30/Stunde; Forecast.Solar und Open-Meteo jeweils 120/Tag sowie 10 bzw. 30/Stunde. Sie sind Schutzgrenzen der Anwendung und keine Garantie des Anbieters. Ein manueller Abruf wahrt Limits, Mindestabstand von 15 Minuten und Fehlerwartezeiten. HTTP 429 berücksichtigt `Retry-After`. Fehlgeschlagene Versuche verbrauchen ebenfalls eine Reservierung. Die Zähler liegen dauerhaft in MongoDB und überstehen einen Neustart.

Tokens werden nur serverseitig verwendet und in normalen API-Antworten und CSV nicht ausgegeben. Ein leeres Tokenfeld behält den gespeicherten Wert; zum Löschen die ausdrückliche Option verwenden. Vollständige Datenbanksicherungen enthalten Zugangsdaten und gehören an einen geschützten Ort. Das Dashboard selbst nur im vertrauenswürdigen Netz oder hinter einem geschützten Reverse Proxy betreiben.

## 4. Gewichtung und Abhängigkeiten selbst bestimmen

Unter **PV-Anlage bearbeiten → Gewichtung und Abhängigkeiten** gibt es drei Modi:

| Modus | Verhalten |
|---|---|
| Automatisch nach Prognosefehler | Gewicht aus dem Fehler früherer gültiger Tage. Ohne Lerndaten sind Stimmen gleich. Optional abhängige Quellen gruppieren. |
| Gleich pro Quelle | Jede verfügbare Quelle erhält `1 / Anzahl` der Mischung, unabhängig von Gruppen und automatischer Obergrenze. Bei drei Quellen je 33,33 %. |
| Manuell nach Quellengewichten | Im Editor jeder Quelle das relative Gewicht einstellen. `1:1:2` ergibt 25/25/50 %, `0:1:3` ergibt 0/25/75 %. Keine automatische Begrenzung. |

**Warum vorher 25/25/50 %?** VRM und Solcast teilen standardmäßig die Gruppe `solcast`, weil VRM Solcast-Strahlungsdaten nutzt. Open-Meteo bildet eine zweite Gruppe. Ohne Lerndaten bekommt jede Gruppe 50 %, innerhalb der gemeinsamen Gruppe erhalten VRM und Solcast jeweils die Hälfte. Das war eine Voreinstellung für Abhängigkeiten, keine bereits nachgewiesene Genauigkeit.

Im automatischen Modus kannst du **Abhängige Quellen gemeinsam gewichten** ausschalten. Dann zählt jede Quelle einzeln. Mit aktivierter Gruppierung steht im Quelleneditor **Abhängigkeitsgruppe** zur Verfügung:

- `auto`: Standardgruppe verwenden, also VRM/Solcast gemeinsam, andere Anbieter getrennt.
- `independent`: diese Quelle immer einzeln behandeln.
- Eigener Name: alle Quellen mit demselben Namen gehören zusammen, zum Beispiel `wettermodell-a`. Groß-/Kleinschreibung und äußere Leerzeichen werden vereinheitlicht. Der Name `solcast` verbindet auch mit der Standardgruppe.

Die **automatische Obergrenze pro Stimme** lässt sich von 50 bis 100 % einstellen, Standard 70 %. Eine Stimme ist bei Gruppenbildung eine Gruppe, innerhalb der Gruppe wiederum eine einzelne Quelle. Bei nur einer verfügbaren Stimme gilt 100 %. Gleich- und Manuell-Modus ignorieren die Obergrenze und die Gruppierung.

Fehlende Quellen werden nicht als Nullprognose verwendet; die verbleibenden Gewichte werden auf 100 % normiert. Manuelles Gewicht 0 schließt nur aus der Mischung aus; Abruf und Einzelvergleich laufen weiter, solange die Quelle aktiv ist. Sind alle verfügbaren manuellen Gewichte 0, bleibt die Mischung unbekannt und es erscheint ein Hinweis.

Änderungen gelten sofort in der **aktuellen Vorschau** und beim nächsten Stichtag für neue Tagesanfangsprognosen. Bereits festgehaltene Gewichte werden nicht rückwirkend geändert. Das Tagesprotokoll speichert Modus, Gruppenentscheidung, Obergrenze und die tatsächlich verwendeten Gewichte.

## 5. Was genau wird gelernt?

- Um 00:05 wird pro Quelle die letzte **vollständige** Tagesprognose festgehalten, die bis dahin fertig eingetroffen und höchstens 18 Stunden alt war. Tagessummen werden in der Anlagenzeitzone gebildet; Sommerzeittage haben 23 oder 25 Stunden.
- Diese Prognose ist unveränderlich. **Aktuelle Vorschau** und **Morgen** dürfen sich durch neue Abrufe ändern. War der Dienst ausgefallen, dürfen nur bereits gespeicherte Daten von vor dem Stichtag verwendet werden. Spätere Abrufe füllen keine angebliche Tagesanfangsprognose auf.
- Frühestens zehn Minuten nach Tagesende werden Ist-kWh und Fehler berechnet. In der Tagesbewertung gewinnt die Originalquelle mit dem kleinsten absoluten kWh-Fehler. Fehlende Werte sind keine Nullprognosen.
- Der Kandidatenfaktor entsteht aus dem Median früherer Verhältnisse Ist/Prognose, wird bei wenig Daten Richtung 1 abgeschwächt und auf **0,5 bis 1,5** begrenzt. Kleine Originalprognosen unter 0,1 kWh beeinflussen den Faktor nicht.
- Nach mindestens sieben geeigneten Tagen kann ein Korrekturkandidat entstehen. Er wird erst eingesetzt, wenn er an mindestens sieben **weiteren** Tagen einen kleineren mittleren absoluten Fehler als die Originalwerte derselben Tage erzielt hat. Bis dahin gilt das Original. Bei schlechterem Ergebnis fällt die Anwendung auf den Faktor 1 zurück. Dadurch kann der Standardfall frühestens nach etwa 14 geeigneten Tagen korrigieren.
- Quellen mit kleinerem historischem Fehler bekommen mehr Gewicht, einzelne Stimmen standardmäßig höchstens 70 %, sofern mehrere Stimmen vorhanden sind. VRM nutzt Solcast-Einstrahlungsdaten; daher werden VRM und Solcast zuerst in derselben Quellenfamilie gemischt und bekommen zusammen nur eine Familienstimme gegenüber anderen Quellen.
- Jeder Tag protokolliert Original, Korrekturkandidat, verwendeten Faktor, kWh-Offset, Gewichte, Lerntage, Ergebnis und Ausschlussgründe. Der Offset ist **Original × (verwendeter Faktor − 1)**; es wird keine konstante nächtliche Energie erfunden. Geometrie-, Messseiten- oder relevante Quellenänderungen starten eine neue Lernbasis. Alte Protokolle bleiben erhalten.
- Eine angezeigte Fehlerspanne ist das historische 80. Perzentil absoluter Mischungsfehler. Sie ist **keine garantierte 80-%-Konfidenz** und kein Versprechen einer jeden Tag besseren Prognose.

Schnee, Wartung, Ausfälle oder nicht gemessene Abregelung im **Tagesvergleich und Modellprotokoll** manuell ausschließen und begründen. Die Änderung wird protokolliert und beeinflusst nur künftiges Lernen; frühere Vorhersagen werden nicht rückwirkend umgerechnet. Ausschluss aufheben ist ebenfalls möglich. Tage mit unterschiedlichen Messgrenzen nicht für einen gemeinsamen Vergleich verwenden.

Die Anbieter-Rangliste zeigt MAE in kWh und die Anzahl gültiger Tage. Ranglisten mit unterschiedlichen Tageszahlen sind nur eingeschränkt vergleichbar. Der Gesamtfehler bewertet ausschließlich die eingefrorenen Morgenprognosen, nicht die nachträglich verbesserte Tagesvorschau.

## 6. VRM-Einheitenkorrektur in 2.7.1

In 2.7.0 wurden stündliche VRM-Werte fälschlich direkt als kWh summiert. Die Stundenwerte entsprechen **Wh pro Stunde** (beziehungsweise der mittleren W-Leistung dieser Stunde); die interne Energie muss durch 1.000 geteilt werden. Ein Tageswert von 38.894,84 Wh entspricht **38,89484 kWh**. Referenz zur stündlichen API-Interpretation: [evcc-VRM-Implementierung](https://github.com/evcc-io/evcc/blob/master/templates/definition/tariff/victron.yaml).

Beim ersten Start von 2.7.1 korrigiert die Migration eindeutig zuordenbare alte VRM-Snapshots, Tageswerte, gewichtete Mischungen und bereits vorhandene Fehlerwerte genau einmal. Originalwerte und Zeitpunkt bleiben im Korrekturprotokoll erhalten. Andere Anbieterwerte, eingefrorene Gewichte, Istmessungen und manuelle Ausschlüsse bleiben bestehen. Im Tagesprotokoll wird die Korrektur angezeigt. Diese technische Einheitenkorrektur ist die ausdrückliche Ausnahme von der Unveränderlichkeit der Morgenprognose; es fließen dabei keine späteren Wetterdaten ein.

VRM erhält eine neue Parserrevision und startet seine Lerngrundlage neu, damit die falschen Einheiten keine Faktoren oder Erfolgszähler weiter beeinflussen. Alte Korrekturstatistiken werden nicht als gültige neue VRM-Statistik verwendet. Andere Quellen behalten ihre Lerndaten. Ohne verbliebene Anbieter-ID oder gespeicherte eindeutige Typinformation werden alte Quellen nicht anhand ihres frei gewählten Namens erraten.

**Reine AC-PV-Anlagen sind ohne Batterie zulässig.** Wähle einen gewöhnlichen PV-Wechselrichter (Typ WR) mit dessen reiner PV-Produktion. Die Auswahl setzt AC automatisch; DC-MPPT setzt DC, eine kombinierte Auswahl setzt bewusst gemischt. Ein Hybrid-Ausgang mit Batterie-/Netzanteilen bleibt als reine PV-Istquelle ungeeignet.

## 7. Fehlersuche

**Keine Tagesanfangsprognose:** Einrichtung nach 00:05, kein vollständiger Abruf davor, Anbieterfehler oder Daten älter als 18 Stunden. Bis zum nächsten korrekt vorbereiteten Tag warten; nichts rückdatieren.

**Keine Istwerte oder Lerntage:** Recorder, PV-Energiezähler, Einheiten, Zeitzone und Messseite kontrollieren. Abregelungssignal nicht als Leistungswert konfigurieren. Ein vorübergehend fehlender Anbieter verhindert nicht die Auswertung anderer Quellen.

**Keine Korrektur nach einer Woche:** Sieben Tage dienen zunächst dem Lernen. Anschließend muss der Kandidat an neuen Tagen besser als das Original sein; bei fehlenden oder ausgeschlossenen Tagen dauert das länger.
