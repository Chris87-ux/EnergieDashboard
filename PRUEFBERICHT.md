# Energieboard – Codeprüfung und Installationspaket

Stand 19. November 2026.

## Umfang

Geprüft wurden Backend, Modelle, Datenbankzugriffe, ioBroker- und InfluxDB-Anbindung, Recorder, Energieberechnung, Frontend, Datenpunkt-Editoren sowie die Dateien für den Debian-LXC. Das Installationspaket enthält die gebaute Oberfläche und die festgelegten Python-Abhängigkeiten.

## Behobene Fehler

| Bereich | Korrektur |
| --- | --- |
| Zeitgrenzen | Zählerdeltas und Leistungsintegration werden auf den gewählten Zeitraum begrenzt. Alte Zählerwerte außerhalb des Zeitraums werden bei zu großer Lücke als unzureichende Randdaten behandelt. |
| Zählerrauschen | Kleine negative Schwankungen mit anschließender Erholung erzeugen keine zusätzlich gezählte Energie mehr. |
| MongoDB-Historie | Ein aggregierter letzter Zählerstand bekommt den Zeitstempel seines tatsächlichen letzten Messpunkts. |
| Historien zusammenführen | Recorder-Werte können interne Zeitfenster ohne InfluxDB-Messpunkt ergänzen. Der nächstgelegene verfügbare Zählerstand vor dem Zeitfenster wird bevorzugt. |
| InfluxDB 1.x | Zeitfenster werden an den angefragten Start angepasst. |
| InfluxDB 2.x | Fehlende Buckets und im CSV-Datenstrom gemeldete Laufzeitfehler werden als Fehler erkannt. |
| Kennzahlen | Fehlende Netzwerte werden als unbekannt dargestellt. Daraus entstehen keine scheinbaren 0 W oder 100 % Autarkie mehr. |
| RUN und Speicher | Die Gültigkeitsdauer neuer Aufzeichnungen wird mitgespeichert. Änderungen des Recorder-Intervalls verändern diese aufgezeichnete Gültigkeit nicht nachträglich. |
| Einstellungen | Ein Hintergrund-Neuladen überschreibt eine noch nicht gespeicherte Formulareingabe nicht mehr. |
| Zeitraumauswahl | Aktive Presets werden anhand der Server-Zeiträume aktualisiert. Minütliche Aktualisierungen sind auf laufende Zeiträume und aktive relative Presets begrenzt. |
| API-Eingaben | Host und URL werden geprüft. Reservierte Metadaten wie ID und Schema-Version werden bei Schreibzugriffen vom Server verwaltet. IPv6-Hosts werden korrekt als URL zusammengesetzt. |
| Speicheranzeige | Ein Speicher wird in der Gerätezahl einmal gezählt. Lade- und Entladekanal besitzen eine ausdrückliche Speicherzuordnung. |
| Diagnose | Der API-Status prüft die Datenbankverbindung. Ein Datenbankausfall führt zu HTTP 503. |
| Installer | Zusätzliche Vorprüfung für Oberfläche, Datenbankversion und Indizes, lesbare Laufzeitdateien für den Dienstbenutzer und Startdiagnose über das Journal. |
| Lokale MongoDB | Neu installierte MongoDB erhält einen auf 0,5 GB begrenzten WiredTiger-Cache für den Container. |

## Prüfergebnisse

| Prüfung | Ergebnis |
| --- | --- |
| Python-Syntax und Paketabhängigkeiten | Bestanden |
| Rechen- und Regressionstests | 19 Tests bestanden |
| Produktionsbuild mit TypeScript und Vite | Bestanden |
| Groß-/Kleinschreibung lokaler Frontend-Imports für Linux | 101 Imports geprüft |
| npm-Audit der Laufzeitabhängigkeiten | 0 gemeldete bekannte Schwachstellen zum Prüfzeitpunkt |
| Python-Abhängigkeiten für Linux amd64 / Python 3.11 | Passende Binärpakete und vollständige Auflösung des festgelegten Paketsatzes geprüft |
| Bash-Syntax des Installers | Bestanden |
| ShellCheck des aktuellen Installers | Bestanden |
| Installations-Vorprüfung gegen MongoDB 8.0.16 | Bestanden |
| API und echte MongoDB | Knoten, gemischte Geräte, RUN, SOC, Laden/Entladen, deaktivierte Knoten und Metadaten geprüft |
| Größere Konfiguration | API mit 50 Leistungsflüssen und Rechentest mit 50 Geräten geprüft |
| InfluxDB-Anbindung | Kontrollierte HTTP-Antworten für 1.x und 2.x sowie Fehlerfälle geprüft |
| Chromium-Browser | Knoteneditor, Gerätezuordnung, Speicher-Vorzeichen, RUN-Editor und Energieseite geprüft |
| Desktop und Mobilansicht | Browserprüfung einschließlich horizontalem Überlauf bestanden |
| LXC-Archiv | Inhalt, ausführbarer Installer, enthaltene Assets und SHA-256-Prüfsumme geprüft |

Die Laufzeitprüfungen erfolgten lokal unter Windows mit Python 3.11.2, MongoDB 8.0.16 und Chromium. Die Linux-Pakete wurden für CPython 3.11 auf amd64 aufgelöst. Bash und ShellCheck prüfen das Installationsskript statisch.

## Inbetriebnahme auf deinem Proxmox

Der erste vollständige Installationslauf mit Debian-Paketverwaltung und systemd auf deinem Proxmox-LXC sowie die Verbindung zu deinen echten ioBroker- und InfluxDB-Instanzen stehen aus. Die Anleitung enthält dafür die Container-Voraussetzungen, Installationsschritte und Diagnosebefehle.

Das Board startet mit einer leeren Gerätekonfiguration. Neue RUN- und Speicherhistorien beginnen mit aktiver lokaler Aufzeichnung. Die Topologie verwendet eine Knotenebene. Für den Recorder ist aktuell eine fortlaufende Speicherung ohne automatische Aufbewahrungsfrist vorgesehen. Diese Betriebsbedingungen sind in der Installationsanleitung beschrieben.

## Dateien

- `INSTALLATION.md` enthält die vollständige Anleitung.
- `deploy/install.sh` richtet die Anwendung im LXC ein.
- `deploy/check.py` prüft die ausgepackte Oberfläche und MongoDB.
- `deploy/energieboard.service` beschreibt den Anwendungsdienst.
- `deploy/mongod-cache.conf` enthält die Cache-Anpassung für neu installierte lokale MongoDB.
- `app/backend/tests` enthält die mitgelieferten Rechen- und Regressionstests.

Im Ausgabeverzeichnis stehen das LXC-Archiv, die separate Anleitung, dieser Prüfbericht und die Archiv-Prüfsumme bereit.
