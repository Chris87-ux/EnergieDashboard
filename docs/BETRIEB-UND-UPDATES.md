# Betrieb, Backup, Wiederherstellung und Updates

[Dokumentationsübersicht](README.md) · [LXC-Installation](../INSTALLATION.md) · [Docker-Installation](../DOCKER.md) · [Fehlersuche](FEHLERSUCHE.md)

## Inhalt

- [Was sichern?](#was-sichern)
- [LXC-Sicherung](#lxc-sicherung)
- [LXC-Update](#lxc-update)
- [Docker-Sicherung](#docker-sicherung)
- [Docker-Update](#docker-update)
- [Wiederherstellung](#wiederherstellung)
- [Umzug zwischen LXC und Docker](#umzug-zwischen-lxc-und-docker)
- [Regelmäßiger Betrieb](#regelmäßiger-betrieb)

## Was sichern?

| Sicherung | Enthält | Reicht wofür? |
|---|---|---|
| Konfiguration CSV | Konfiguration und stabile IDs, keine vollständigen Kennwörter, keine Historie | Serienbearbeitung und Konfigurationsvorlage |
| `deploy/backup.py` | Ganze gewählte Datenbank einschließlich Historie, BSON-Werten und Indizes | Vollständiger Datenstand |
| Anwendungs-/Umgebungsdateien | Anwendungsversion, bei LXC `.venv`/Dienstdatei, bei Docker `.env`/Compose-Auswahl | Passende Laufzeit und Verbindungsdaten |
| Proxmox-/Hostbackup | Je nach Sicherung Container/VM und Datenträger | Wiederherstellung des Hosts/Gasts |

Backups enthalten Zugangsdaten und gehören an einen geschützten Ort **außerhalb** des Quellsystems. Ein externes MongoDB-System und nicht eingeschlossene Bindmounts sind nicht automatisch im Proxmox-Backup enthalten. Ein laufender Dateisystem-Snapshot ist kein Nachweis für eine konsistente Datenbanksicherung.

Alle folgenden Datenbank-Backups stoppen die **App** vorübergehend, lassen MongoDB aber laufen. Dadurch sind Recorder und Konfigurationsschreiber angehalten. Andere Anwendungen dürfen die Energieboard-Datenbank ebenfalls nicht beschreiben.

## LXC-Sicherung

Als root **im LXC**:

```bash
(
  set -e
  backup_root="/var/backups/energieboard/manual-$(date -u +%Y%m%dT%H%M%S)-$$"
  install -d -m 0700 "$backup_root"
  systemctl stop energieboard
  trap 'systemctl start energieboard' EXIT
  /opt/energieboard/.venv/bin/python /opt/energieboard/deploy/backup.py backup "$backup_root/database"
  tar -czf "$backup_root/application.tar.gz" -C /opt energieboard
  cp /etc/energieboard/energieboard.env "$backup_root/energieboard.env"
  cp /etc/systemd/system/energieboard.service "$backup_root/energieboard.service"
  chmod 0600 "$backup_root/energieboard.env"
  echo "Sicherung: $backup_root"
)
```

Der Neustart wird auch bei einem Fehler versucht. Bei fehlgeschlagener Sicherung nicht von einem vollständigen Backup ausgehen; Fehlermeldung und Dienststatus prüfen. Der Zielordner `database` muss neu sein. Anschließend die ganze Sicherung geschützt auf ein anderes System kopieren.

## LXC-Update

Als root **im LXC**. Nicht parallel ausführen. Ausreichend freien Platz für alte Anwendung/Python-Umgebung, neue Anwendung und vollständiges Datenbankbackup vorhalten. Vor größeren Änderungen zusätzlich Proxmox-Backup und externe Datenbanksicherung einplanen.

Auf den dokumentierten Release-Stand aktualisieren:

```bash
bash /opt/energieboard/deploy/update.sh v2.4.0
```

Für ein späteres Release den passenden bestehenden Tag einsetzen. Ohne Argument verwendet der Updater `main`; für einen bewusst reproduzierbaren Stand ist ein fester Tag vorzuziehen.

Wenn eine sehr alte Installation noch keinen Updater besitzt, diesen einmalig laden:

```bash
curl -fL --retry 3 https://raw.githubusercontent.com/Chris87-ux/EnergieDashboard/v2.4.0/deploy/update.sh -o /tmp/energieboard-update.sh
bash /tmp/energieboard-update.sh v2.4.0
```

### Ablauf

1. Tag auf festen Commit auflösen; Archiv und SHA-256 von demselben Commit laden.
2. Prüfsumme und Archivpfade kontrollieren.
3. App stoppen und Datenbank, Anwendung, Dienst- und Umgebungsdatei unter `/var/backups/energieboard/<Zeitpunkt>-<PID>/` sichern.
4. Anwendung austauschen, bestehende Umgebung/Datenbank weiterverwenden und Abhängigkeiten installieren.
5. Migration beim Start ausführen, API prüfen und Commit in `/opt/energieboard/INSTALLED_COMMIT` speichern.
6. Bei Fehler nach Austausch alte Anwendung und gesicherte Datenbank wiederherstellen. Scheitert der Datenbank-Restore, bleibt die App angehalten und meldet den Sicherungspfad.

Der Updater installiert keine neue MongoDB und ändert die vorhandene Umgebungsdatei nicht. `MONGO_URL` und `DB_NAME` müssen weiter auf dieselbe Datenbank zeigen. Bestehende IDs und Historie bleiben erhalten; neu erforderliche Angaben, z. B. Kapazität, einmal ergänzen.

Nach Erfolg:

```bash
systemctl status energieboard --no-pager
curl -fsS http://127.0.0.1:8000/api/
journalctl -u energieboard -n 60 --no-pager
```

Danach Netz-/Speicherwerte, Knoten und Recorder im Browser prüfen. Sicherungen werden nicht automatisch entfernt.

## Docker-Sicherung

**Auf dem Docker-Host im Projektverzeichnis**, bei der beschriebenen Installation `/opt/energieboard-docker`.

Die Befehle verwenden Bash-Arrays, damit dieselbe Compose-Auswahl durchgehend gilt. Bei externer MongoDB die markierte Zeile entsprechend ersetzen.

```bash
(
  set -e
  compose=(docker compose)
  # Bei externer MongoDB stattdessen: compose=(docker compose -f compose.external.yaml)
  backup_name="$(date -u +%Y%m%dT%H%M%S)-$$"
  mkdir -p backups
  chmod 0700 backups
  "${compose[@]}" stop energieboard
  trap '"${compose[@]}" start energieboard' EXIT
  "${compose[@]}" run --rm --no-deps --user "$(id -u):$(id -g)" \
    -v "$PWD/backups:/backups" energieboard \
    python /opt/energieboard/deploy/backup.py backup "/backups/$backup_name"
  git rev-parse HEAD > "backups/$backup_name/APP_COMMIT"
  cp .env "backups/$backup_name/docker.env"
  chmod 0600 "backups/$backup_name/docker.env"
  echo "Sicherung: $PWD/backups/$backup_name"
)
```

Zusätzlich die verwendete Compose-Datei und ggf. eigene Overrides gesichert halten. Das Sicherungsprogramm verbindet sich über die Umgebungsvariablen des App-Dienstes; bei externer Variante wird deshalb die externe Datenbank gesichert.

Die Datenbank selbst braucht dafür keinen veröffentlichten Hostport. Nicht das live beschriebene MongoDB-Volume unkoordiniert kopieren. Kein `down --volumes` zur Sicherung ausführen.

## Docker-Update

1. Obige Sicherung erstellen und bisherigen Commit/Tag notieren.
2. In das bestehende Projektverzeichnis wechseln.
3. Tags laden und Zielstand auschecken.

```bash
git status --short
git describe --tags --always
git fetch --tags
git checkout v2.4.0
```

`v2.4.0` ist der aktuelle dokumentierte Stand; bei späterem Update dessen neuen Tag verwenden. Eigene Änderungen vor dem Checkout prüfen und sichern, nicht mit `reset --hard` verwerfen. Detached HEAD nach Tag-Checkout ist für diesen Betrieb normal.

4. In `.env` `ENERGIEBOARD_VERSION=2.4.0` passend zum gewählten Tag setzen. Die Variable benennt nur das lokale Image; der Git-Stand bestimmt den Inhalt.
5. **Denselben Projektnamen und dieselbe Datenbank/Volume-Zuordnung beibehalten.**
6. Neubau und Prüfung:

```bash
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
docker compose logs --tail=80 energieboard
```

Bei externer MongoDB in allen drei Befehlen `docker compose -f compose.external.yaml ...` verwenden. Vorhandenes `.env` nicht durch `cp docker.env.example .env` überschreiben.

Das benannte Datenvolume bleibt erhalten, Migrationen laufen beim Appstart. **`docker compose down --volumes` löscht es.** Keine LXC-Skripte im Docker-Container ausführen. Ein bloßes `docker compose pull` aktualisiert kein lokal gebautes Projektimage. MongoDB-Hauptversionswechsel sind eine eigene Migration und kein Bestandteil des App-Updaters.

Bei Updatefehlern Logs sichern. Ein bereits migriertes Datenbankschema darf nicht einfach mit einer älteren App weiterverwendet werden; passenden Datenstand gemeinsam mit der App wiederherstellen.

## Wiederherstellung

**Restore ersetzt den gesamten Inhalt der ausgewählten Datenbank.** Vorher Ziel-URI, Datenbanknamen, Sicherungsstand und passende Anwendungsversion kontrollieren. Auch vor einem Restore möglichst den jetzigen Zustand separat sichern. Eine CSV-Datei ist kein Ersatz für diesen Vorgang.

### Datenbank im LXC wiederherstellen

Die Anwendungsversion muss zum Sicherungsstand passen. Im folgenden Block den tatsächlich vorhandenen Sicherungspfad einsetzen:

```bash
systemctl stop energieboard
/opt/energieboard/.venv/bin/python /opt/energieboard/deploy/backup.py restore /var/backups/energieboard/TATSAECHLICHE-SICHERUNG/database
```

Nur nach erfolgreichem Restore starten:

```bash
systemctl start energieboard
systemctl status energieboard --no-pager
```

Nach einem erfolgreichen Update zurück auf eine ältere App: ebenfalls alte Anwendung aus `application.tar.gz`, passende Umgebungs-/Dienstdatei und Datenbank derselben Sicherung wiederherstellen. Vorher die aktuelle Anwendung zur Diagnose an einem freien separaten Pfad aufbewahren. Falls die alte Version kein passendes `backup.py` besitzt, das Werkzeug aus der neueren Version vor dem Austausch separat sichern und mit kompatibler Python-Umgebung ausführen. Nicht nur das Schema-Versionsfeld manuell zurücksetzen.

### Datenbank in Docker wiederherstellen

App-Image und `.env` müssen zum gewünschten Ziel passen, MongoDB muss laufen. Die Sicherung liege unter `backups/20261121T120000` und enthalte direkt `manifest.json`; Namen durch den echten Ordner ersetzen:

```bash
(
  set -e
  compose=(docker compose)
  # Bei externer MongoDB stattdessen: compose=(docker compose -f compose.external.yaml)
  backup_name=20261121T120000
  test -f "backups/$backup_name/manifest.json"
  "${compose[@]}" stop energieboard
  "${compose[@]}" run --rm --no-deps --user "$(id -u):$(id -g)" \
    -v "$PWD/backups:/backups:ro" energieboard \
    python /opt/energieboard/deploy/backup.py restore "/backups/$backup_name"
  "${compose[@]}" up -d --wait --wait-timeout 180 energieboard
)
```

Hier gibt es bewusst keinen automatischen Appstart bei fehlgeschlagenem Restore. Fehler beheben, bevor weiter aufgezeichnet wird. Bei lokaler Variante nötigenfalls MongoDB vorab mit `docker compose up -d --wait mongo` starten; bei externer Variante deren Erreichbarkeit prüfen.

## Umzug zwischen LXC und Docker

Das Datenbankformat ist identisch. Für einen LXC→Docker-Umzug:

1. Quellversion feststellen; Ziel mit derselben Version vorbereiten oder einen ausdrücklich kompatiblen Upgradepfad wählen.
2. Quell-App stoppen und vollständige Datenbanksicherung erstellen. LXC-Sicherung enthält die Daten unter `database/`.
3. Ziel installieren, Ziel-App stoppen und richtige eigene Datenbank prüfen.
4. Den Inhalt dieses `database/`-Ordners als kompletten Sicherungsordner auf den Docker-Host übertragen, z. B. `backups/lxc-umzug/manifest.json` plus alle zugehörigen Streams.
5. Mit dem Docker-Restore wiederherstellen, App starten und die [Abnahme](ERSTE-SCHRITTE.md#10-abnahme-vor-dem-dauerbetrieb) durchführen.
6. Quell-App ausgeschaltet lassen, bis die Entscheidung für das Ziel gefallen ist. Zwei Recorder gegen dieselbe Datenbank sind nicht vorgesehen.

Rückweg Docker→LXC analog mit den jeweiligen Restore-Befehlen. Die Python-`.venv` wird nicht zwischen Plattformen kopiert; die Zielinstallation erstellt ihre eigene Laufzeit. Nur CSV-Import überträgt keine Historie und keine vollständigen Zugangsdaten.

## Regelmäßiger Betrieb

- Recorderstatus und letzte Messwerte prüfen; beim Quellenwechsel die ursprüngliche Messgrenze beibehalten oder Änderung dokumentieren.
- Zeitzone korrekt halten. Betriebssystemzeit und Quellzeit sollten synchron sein.
- Speicherplatz und Sicherungsziel überwachen. Es gibt derzeit **keine automatische Historien-Löschfrist**.
- Beispiel zur Größenplanung: 100 Kanäle alle 15 s erzeugen etwa 576.000 Rohsamples pro Tag, zuzüglich abgeleiteter Kanäle. Bytebedarf hängt von Kompression und Indizes ab.
- Sicherungen regelmäßig auf einem separaten Testziel wiederherstellen. Wiederherstellbarkeit nicht allein aus einer vorhandenen Datei ableiten.
- Zugriff auf API/Dashboard und Zugangsdaten beschränken. Automatische OS-/MongoDB-Updates entsprechend der eigenen Betriebsstrategie planen; App-Updater aktualisiert nicht den ganzen Host.

LXC-Status: `systemctl status energieboard` und `journalctl -u energieboard`. Docker-Status: `docker compose ps` und `docker compose logs`. [Gezielte Fehlersuche](FEHLERSUCHE.md).
