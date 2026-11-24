# Backups, restore, updates and moving installations

[Documentation](README.md) · [LXC installation](INSTALLATION.md) · [Docker installation](DOCKER.md)

## Persistent identity

Configuration and history live in MongoDB. IDs link measurements, devices, groups and recorded channels. Keep the same database URI/name and, in Docker, project/volume identity. Application updates run idempotent additive migrations. Schema 6 is unchanged in 2.6.0; language preferences live in each browser and require no database migration.

A CSV export contains configuration without secrets or history. Full backups include credentials and history. Protect them and test restoration on an isolated target. The local recorder has no automatic history retention limit; monitor disk space and backup size.

## LXC backup

Run as root inside the direct LXC installation. The command stops the app for a consistent snapshot and restarts it on exit:

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
  echo "Backup: $backup_root"
)
```

Store a copy outside the LXC. Proxmox snapshots/backups are useful but an application/database backup is still valuable, especially with an external MongoDB. `deploy/backup.py` uses Extended JSON to preserve BSON values and index definitions; no mongodump installation is required.

## LXC update

After backup, run **inside the LXC**:

```bash
bash /opt/energieboard/deploy/update.sh v2.6.0
```

For an installation whose old updater cannot handle the target release, fetch the target updater first:

```bash
curl -fL --retry 3 https://raw.githubusercontent.com/Chris87-ux/EnergieDashboard/v2.6.0/deploy/update.sh -o /tmp/energieboard-update.sh
bash /tmp/energieboard-update.sh v2.6.0
```

The updater resolves the ref, verifies archive/checksum, saves the previous application, database and environment, replaces code and runs installation checks. Configuration, stable IDs, groups and history are preserved. Success names the backup directory. A failure attempts rollback to the previous application/database. Do not run the direct LXC updater for Docker.

The readiness helper retries up to 30 times by default, checking the local API and active service. Expected initial connection refusals are quiet; a persistent failure reports the last error and service diagnostics. The next update should no longer show the misleading transient curl error immediately before a successful result.

Check afterwards:

```bash
systemctl status energieboard --no-pager
curl -fsS http://127.0.0.1:8000/api/
journalctl -u energieboard -n 60 --no-pager
```

Verify the application version, grid, live readings, recording and selected historical interval.

## Docker backup

Run in the existing project directory, using the same Compose variant throughout. For external MongoDB, replace the compose array as indicated:

```bash
(
  set -e
  compose=(docker compose)
  # For external MongoDB use instead: compose=(docker compose -f compose.external.yaml)
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
  echo "Backup: $PWD/backups/$backup_name"
)
```

The backup container uses the existing app image and mounted backup directory while the app is stopped. Keep MongoDB reachable. This backs up the database used by the configured URI; verify the target before proceeding. Preserve `.env`, Compose settings and the saved APP_COMMIT along with the backup.

## Docker update

Check and save any local changes before changing tags; do not discard them with reset --hard. Then:

```bash
git status --short
git describe --tags --always
git fetch --tags
git checkout v2.6.0
```

Set `ENERGIEBOARD_VERSION=2.6.0` in `.env` to match the chosen tag. This variable names the local image; Git determines the source. Rebuild/recreate:

```bash
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
docker compose ps
docker compose logs --tail=80 energieboard
```

For external MongoDB consistently add `-f compose.external.yaml` to these commands. Keep the same project name, volume and DB_NAME. No data is copied automatically between local and external databases. Do not use `down --volumes` during an update.

## Restore and downgrade

Restore replaces the target database's collections. Select a verified backup and correct URI/DB_NAME first. Stop the app and pair restored data with its matching application version, particularly when downgrading a schema. Do not simply start old code against a newer schema.

LXC example, replacing ACTUAL-BACKUP with the real backup directory:

```bash
systemctl stop energieboard
/opt/energieboard/.venv/bin/python /opt/energieboard/deploy/backup.py restore /var/backups/energieboard/ACTUAL-BACKUP/database
```

Restore the matching application/environment as needed before restarting:

```bash
systemctl start energieboard
systemctl status energieboard --no-pager
```

Docker example: replace the backup name, check the recorded APP_COMMIT, check out/build the matching code first, and keep the same Compose variant:

```bash
(
  set -e
  compose=(docker compose)
  # For external MongoDB use instead: compose=(docker compose -f compose.external.yaml)
  backup_name=20261121T120000
  test -f "backups/$backup_name/manifest.json"
  "${compose[@]}" stop energieboard
  "${compose[@]}" run --rm --no-deps --user "$(id -u):$(id -g)" \
    -v "$PWD/backups:/backups:ro" energieboard \
    python /opt/energieboard/deploy/backup.py restore "/backups/$backup_name"
  "${compose[@]}" up -d --wait --wait-timeout 180 energieboard
)
```

The restore utility verifies all backup streams before changing collections. A database failure during restoration still requires administrator recovery from the saved backup; no procedure can guarantee rollback while storage is unavailable.

## Moving installations

Prepare the target without creating conflicting live writers, stop the source app, take a full backup, transfer code/environment and restore into the dedicated target database. Retain IDs and database identity where appropriate. Verify network reachability from the new host, source ACLs, time zone and recording. Start only the intended writer. Changing a URI to an empty database creates the appearance of an empty installation; do not reconfigure everything before checking the connection.
