# Energieboard

Dashboard für aktuelle ioBroker-Leistungswerte und Energiebilanzen. MongoDB speichert Konfiguration und lokal aufgezeichnete Messwerte. InfluxDB kann vorhandene Historie liefern.

Die ausführliche [Installationsanleitung](INSTALLATION.md) beschreibt Voraussetzungen, Container-Erstellung, Dateiübertragung, Einrichtung und Fehlersuche. Die Prüfergebnisse stehen im [Prüfbericht](PRUEFBERICHT.md).

## Auf Proxmox vorbereiten

Im Proxmox-Webinterface einen unprivilegierten LXC mit dem Debian-12-Template (Bookworm, amd64) anlegen. Für die geplanten 30–50 Geräte zunächst 2 vCPU, 4 GB RAM und 32 GB Speicher einplanen. Das Datenwachstum regelmäßig prüfen. Der Container braucht eine LAN-Adresse und Zugriff auf ioBroker, optional InfluxDB sowie die Paketquellen während der Installation.

Das Archiv `Energieboard-LXC.tar.gz` auf den Proxmox-Host übertragen, etwa per SCP nach `/root/`. Dann in der **Proxmox-Host-Shell** ausführen und `123` durch die eigene Container-ID ersetzen.

```sh
CTID=123
pct push "$CTID" /root/Energieboard-LXC.tar.gz /tmp/Energieboard-LXC.tar.gz
pct enter "$CTID"
```

## Im Debian-LXC installieren

In der **LXC-Konsole** als root ausführen.

```sh
tar -xzf /tmp/Energieboard-LXC.tar.gz -C /opt
bash /opt/energieboard/deploy/install.sh
```

Das Skript installiert die festgelegten Python-Abhängigkeiten und bei Bedarf lokale MongoDB 8.0. Dafür muss der Proxmox-Prozessor AVX unterstützen. Bei neu installierter MongoDB wird der Cache auf 0,5 GB begrenzt. Vor dem Dienststart werden Oberfläche, Datenbank und Indizes geprüft. FastAPI liefert die gebaute Oberfläche zusammen mit der API aus. Systemd startet `energieboard.service` und bei lokaler MongoDB auch `mongod.service` beim Hochfahren des Containers. In den Proxmox-Optionen lässt sich zusätzlich der Autostart des LXC beim Hoststart einschalten.

Öffne `http://LXC-IP:8000/system` mit der tatsächlichen Container-IP. Das Board hat keine eigene Anmeldung. TCP-Port 8000 per Proxmox-Firewall auf vertrauenswürdige Geräte begrenzen oder einen Reverse-Proxy mit Zugriffsschutz verwenden.

### Externe MongoDB verwenden

Wenn du eine bestehende MongoDB nutzt, die Konfigurationsdatei bei der ersten Installation anlegen und dort die Verbindungsdaten eintragen.

```sh
install -d -m 0700 /etc/energieboard
install -m 0600 /opt/energieboard/deploy/energieboard.env.example /etc/energieboard/energieboard.env
editor /etc/energieboard/energieboard.env
bash /opt/energieboard/deploy/install.sh --external-mongo
```

`MONGO_URL` enthält die URI, `DB_NAME` den Datenbanknamen. Bei einer Migration dieselbe Datenbank wie bisher angeben, um Konfiguration und Historie weiterzuverwenden.

## Verbindung einrichten

### Knoten und Geräte

Unter **Konfiguration** lassen sich Geräte, Knoten und Speicher anlegen. Ein Knoten bildet einen Abschnittszähler mit einstellbarer ein- oder dreiphasiger Anzeige ab. Geräte können der Hauptebene oder einem Knoten zugeordnet werden. Jeder Knoten kann gleichzeitig Verbraucher, Erzeuger und Speicher enthalten.

Die Übersicht bilanziert die Geräte. Der Abschnittszähler dient im Knoten zur Verrechnung. Positiv bedeutet Verbrauch, negativ Erzeugung. Die Differenz ergibt sich aus Zählerwert minus der vorzeichenrichtigen Summe der zugeordneten Geräte einschließlich Speicher. Fehlende Gerätewerte führen zu einer nicht verfügbaren Differenz. Ein deaktivierter Knoten deaktiviert seine zugeordneten Geräte in Anzeige und Bilanz.

Die Knoten bilden aktuell eine Ebene unter der Hauptebene. Geräte und Speicher vor Abschnittszählern werden der Hauptebene zugeordnet. Bevor ein Knoten gelöscht werden kann, müssen seine Geräte und Speicher verschoben werden.

### RUN-Geräte

Im Geräteeditor unter **Datenpunkte** die RUN-Schätzung einschalten, einen RUN-Datenpunkt und die feste Leistung in Watt hinterlegen. `true` beziehungsweise ein Wert ungleich `0` bedeutet Betrieb. `false` oder `0` bedeutet aus. Ein fehlender Datenpunkt gilt als unbekannt.

Live wird bei aktivem RUN die feste Leistung angezeigt. Die aufgezeichneten Betriebszeiten werden als **RUN-Schätzung** in kWh bilanziert. Änderungen der festen Leistung gelten für künftig aufgezeichnete Werte. Die Historie bewahrt die zuvor aufgezeichnete Leistung. Die Zeitauflösung entspricht dem Recorder-Intervall. Ein eingeschalteter Recorder ist für diese Historie erforderlich.

### Speicher

Speicher werden als eigener Typ mit einem vorzeichenbehafteten Leistungsdatenpunkt und einem SOC-Datenpunkt in Prozent angelegt. Das Lade-Vorzeichen wird pro Speicher eingestellt. Die Anschlusszuordnung gilt sowohl beim Laden als auch beim Entladen. Laden wird als Abfluss und Entladen als Zufluss bilanziert.

Die Energie wird ab Einrichtung aus getrennt aufgezeichneter Lade- und Entladeleistung integriert. Vorhandene historische Leistung aus InfluxDB wird für diese neuen Speicherkanäle aktuell nicht rückwirkend aufgeteilt. Der Recorder hält dazu zusätzlich die konfigurierten Messwerte lokal vor. Aufzeichnungslücken werden zeitlich begrenzt und als unvollständige Energie markiert.

Bei 30–50 Geräten kann die Übersicht nach Geräten und Knoten durchsucht werden. Gerätelisten lassen sich je Knoten aufklappen. Abschnittszähler werden innerhalb des Knotens angezeigt. Die separate Kreisdarstellung wird bei mehr als zwölf Leistungsflüssen ausgeblendet.

### Datenquellen anschließen

1. In ioBroker den Adapter **simple-api** bereitstellen. Der Energieboard-Server muss dessen Host und Port erreichen können. Der Standardport ist `8087`.
2. Im Board unter **System** Host, Protokoll und Port eintragen, Verbindung testen und speichern.
3. Unter **Konfiguration** einen Fluss pro Anlage oder Verbraucher mit den tatsächlichen ioBroker-Datenpunkt-IDs anlegen. Die Einheiten und bei Bedarf Vorzeichen und Phasen passend zum Gerät wählen.
4. Für vorhandene Historie normaler Messgeräte unter **System** optional InfluxDB aktivieren und testen. Die Datenpunkt-ID muss als Measurement vorliegen. Der Feldname ist standardmäßig `value`. Der Recorder sammelt zusätzlich die aktuellen Werte in MongoDB.

## Dienst prüfen und aktualisieren

In der LXC-Konsole.

```sh
systemctl status energieboard
journalctl -u energieboard -n 60 --no-pager
curl -fsS http://127.0.0.1:8000/api/
```

Für ein Update den Dienst mit `systemctl stop energieboard` anhalten, das neue Archiv wie bei der Erstinstallation nach `/opt` entpacken und das Installationsskript mit derselben MongoDB-Option erneut ausführen. Das Skript liest weiterhin `/etc/energieboard/energieboard.env`. Die lokale Datenbank liegt bei einer Standardinstallation unter `/var/lib/mongodb`.

Falls du die Oberfläche selbst änderst, in `app/frontend` mit Node.js ab 22.12 `npm ci` und `npm run build` ausführen, bevor das Paket auf den LXC kopiert wird.

## Referenzen

- [Proxmox VE Container-Verwaltung](https://pve.proxmox.com/pve-docs/pct.1.html)
- [MongoDB 8.0 auf Debian installieren](https://www.mongodb.com/docs/v8.0/tutorial/install-mongodb-on-debian/)
