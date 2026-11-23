# Verbrauchergruppen

[Dokumentationsübersicht](README.md) · [Geräte und Knoten](GERAETE-UND-KNOTEN.md) · [CSV](../CSV-IMPORT.md)

## Zweck und Abgrenzung

Eine Gruppe fasst Verbraucher zusätzlich zur elektrischen Knotenhierarchie zusammen. Beispielsweise können Pumpen aus Haus, Hof und Werkstatt in der Gruppe „Pumpen“ liegen, obwohl sie an verschiedenen Zählern hängen. Die Zuordnung verändert weder den Knotenrest noch die Gesamtbilanz und fügt keinen weiteren Verbraucher hinzu.

## Einrichten

1. Unter **Konfiguration → Verbrauchergruppen** eine Gruppe mit Namen, Farbe und Anzeigereihenfolge anlegen.
2. Den Verbraucher bearbeiten und die optionale **Verbrauchergruppe** auswählen. Sein übergeordneter Knoten bleibt unverändert.
3. Bei weiteren Verbrauchern wiederholen. Jedes Gerät gehört höchstens einer zusätzlichen Gruppe an; „Keine Gruppe“ bleibt möglich.
4. In der Übersicht gemeinsame Leistung und Energie Heute prüfen. In der Energiebilanz wird die Energie des gewählten Zeitraums angezeigt.

Gruppierbar sind normale Verbraucher (`kind=device`, `direction=out`), einschließlich RUN-Geräten und gegebenenfalls DC-Verbrauchern. Netz, Knoten, Speicher, Erzeuger, MPPTs und Hybrid-WR gehören nicht hinein. Ein Hybrid ist ein bidirektionaler Wandler und kein normaler Gruppenverbraucher. Automatische Knotenreste werden nicht zugeordnet; sie würden sonst eine zusätzliche Messgrenze in dieselbe Gerätesumme aufnehmen.

## Berechnung und unbekannte Daten

Liveleistung ist die Summe der Leistungsbeträge der aktiven Mitglieder. RUN-Verbraucher tragen ihre feste Wattzahl bei aktivem Signal bei. Gruppenenergie ist die Summe der jeweiligen Geräteenergie im ausgewählten Zeitraum; es werden keine aktuellen kumulativen Lebensdauerzählerstände addiert.

Deaktivierte Geräte sowie Geräte unter deaktivierten Knoten zählen nicht mit. Fehlt ein benötigter Leistungswert, bleibt die Gruppenleistung unbekannt. Unvollständige Energiehistorie wird gekennzeichnet. Eine leere Gruppe zeigt 0. DC-Verbraucher werden innerhalb ihrer Gruppe erfasst, ohne sie zusätzlich auf die AC-Hausbilanz aufzuschlagen.

Die Zuordnung gilt für den aktuell ausgewählten Zeitraum auf Basis der **heutigen Konfiguration**. Ein späterer Gruppenwechsel ordnet die abrufbare Gerätehistorie der neuen Gruppe zu; historische Mitgliedschaften werden nicht zeitabhängig gespeichert. Alte, fehlerhafte oder nicht aufgezeichnete Geräteenergie wird durch eine Gruppe nicht rekonstruiert.

## Reihenfolge, Sicherung und Löschen

Kleinere Reihenfolgezahlen stehen zuerst; die Reihenfolge beeinflusst keine Rechnung. Gruppen haben stabile IDs und bleiben bei Updates und vollständigem Backup/Restore erhalten. Gesamte CSV-Exporte enthalten `record_type=consumer_group`; Gerätezeilen verwenden `group_id`. IDs beim Bearbeiten erhalten.

Eine verwendete Gruppe kann nicht gelöscht werden, auch wenn ihre Verbraucher deaktiviert sind. Zuerst sämtliche Gerätezuordnungen entfernen oder umstellen. Dadurch entstehen keine unbemerkten ungültigen Verweise.
