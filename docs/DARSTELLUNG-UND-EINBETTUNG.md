# Darstellung und Einbettung

[Dokumentationsübersicht](README.md) · [Geräte und Knoten](GERAETE-UND-KNOTEN.md)

## Layout und Farben

Unter **Darstellung** zwischen **Kompakt / eckig**, **Modern / Karten** und **Flussdiagramm** wählen. Hintergrund, Flächen und Akzentfarbe einstellen und **Darstellung speichern**. Gerätesymbole und einzelne Farben werden unter Konfiguration bearbeitet; die Symbolsuche hilft bei der Auswahl.

## Diagramm und Knotennavigation

Die Netzkachel bleibt oben mittig und zeigt beide Richtungen. Knoten erscheinen in eigener rechteckiger Form. Ein Klick öffnet die betreffende Ebene; die Pfadleiste führt zurück. Pro Diagrammseite werden bis zu vier Elemente je Richtung gezeigt, weitere Elemente folgen auf zusätzlichen Seiten. Die Gesamtbilanz bezieht sich trotzdem auf die ganze aktive Anlage.

Unter „Produktion und Verbrauch“ sind Knoten einklappbar und Geräte suchbar. Speicher und DC-Anlage stehen separat unter der Hauptübersicht. Hybrid-WR erhalten zusätzlich ihre Messbilanz-/Wirkungsgradanzeige.

## Geräte bei Nullleistung ausblenden

Standard: Schwelle **1 W**, Wartezeit **60 Sekunden**.

```text
Ausblendebereich: −1 W < Leistung < +1 W
```

−1 W und +1 W selbst bleiben sichtbar, ebenso Erzeuger mit größeren negativen Werten. Kleine echte Werte wie −0,25 W werden zunächst mit Nachkommastellen angezeigt. Bei Schwelle 0 zählt ausschließlich exakt 0 W.

Die Wartezeit muss durchgehend beobachtet sein. Fehlende Werte oder größere Beobachtungslücken setzen die Frist zurück. Neue Leistung blendet das Gerät sofort wieder ein. „Inaktive anzeigen“ zeigt auch ausgeblendete Geräte; Konfiguration und Historie werden durch den Filter nicht gelöscht. Netzanschluss, Knotenstruktur und Speicher bleiben sichtbar.

## Direkte Adresse ohne Navigation

```text
http://<SERVER-IP>:8000/flow
```

Bei Docker den veröffentlichten Hostport statt 8000 einsetzen. Die Seite enthält die Liveübersicht ohne Hauptnavigation, nicht nur das einzelne Diagramm.

Beispiel für ioBroker VIS oder eine andere HTML-Übersicht:

```html
<iframe src="http://192.168.10.17:8000/flow"
        title="Energiefluss"
        width="100%" height="1200"
        style="border:0"></iframe>
```

Adresse durch den tatsächlich erreichbaren Energieboard-Server ersetzen. Bei mehreren Speichern oder kleinen Displays genügend Höhe einplanen bzw. die äußere Ansicht scrollbar gestalten.

## Bei Proxy und HTTPS beachten

- Eine HTTPS-Übersicht darf normalerweise kein HTTP-Dashboard als iframe laden. Energieboard ebenfalls über HTTPS bereitstellen.
- Der Proxy muss die Oberfläche, `/api/` und statische Assets weiterleiten. Die App ist auf Betrieb am URL-Wurzelpfad ausgelegt; ein beliebiges Unterverzeichnis ist nicht fertig konfiguriert.
- Proxy-Regeln wie `X-Frame-Options` oder `Content-Security-Policy: frame-ancestors` dürfen die gewünschte einbettende Seite nicht blockieren. Nur die tatsächlich benötigte Herkunft erlauben.
- Bei vorgeschalteter Anmeldung auch den Zugriff aus dem iframe und dessen Cookieverhalten prüfen.
- `/flow` versteckt Navigation, ist aber **kein Zugriffsschutz** für die anderen Seiten oder die API.

Energieboard bringt selbst weder TLS-Zertifikatsverwaltung noch Benutzeranmeldung mit. Konkrete Reverse-Proxy-Konfiguration hängt von der eingesetzten Umgebung ab.
