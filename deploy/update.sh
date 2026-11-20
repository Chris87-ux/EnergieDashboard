#!/usr/bin/env bash
# Run as root. Uses a single immutable GitHub commit for package and checksum.
set -euo pipefail
umask 077
[[ $EUID == 0 ]] || { echo 'Als root im LXC ausführen.' >&2; exit 1; }
[[ -x /opt/energieboard/.venv/bin/python ]] || { echo 'Bestehende Installation fehlt.' >&2; exit 1; }
exec 9>/var/lock/energieboard-update.lock
flock -n 9 || { echo 'Ein Update läuft bereits.' >&2; exit 1; }
ref="${1:-main}"
[[ "$ref" =~ ^[A-Za-z0-9._-]+$ ]] || { echo 'Ungültige Version.' >&2; exit 1; }
stage="$(mktemp -d /tmp/energieboard-update.XXXXXXXX)"
backup="/var/backups/energieboard/$(date -u +%Y%m%dT%H%M%S)-$$"
repo=https://api.github.com/repos/Chris87-ux/EnergieDashboard
curl -fsSL --retry 3 "$repo/commits/$ref" -o "$stage/commit.json"
commit="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["sha"])' "$stage/commit.json")"
[[ "$commit" =~ ^[a-f0-9]{40}$ ]] || exit 1
base="https://raw.githubusercontent.com/Chris87-ux/EnergieDashboard/$commit/outputs"
curl -fsSL --retry 3 "$base/Energieboard-LXC.tar.gz" -o "$stage/Energieboard-LXC.tar.gz"
curl -fsSL --retry 3 "$base/SHA256SUMS" -o "$stage/SHA256SUMS"
(cd "$stage" && sha256sum -c SHA256SUMS)
python3 - "$stage" <<'PY'
import sys,tarfile
from pathlib import Path
folder=Path(sys.argv[1])
with tarfile.open(folder/'Energieboard-LXC.tar.gz') as archive:
    for item in archive.getmembers():
        parts=Path(item.name).parts
        if not parts or parts[0]!='energieboard' or '..' in parts or item.issym() or item.islnk() or not (item.isfile() or item.isdir()):
            raise ValueError('Ungültiger Archivinhalt')
    archive.extractall(folder)
PY
install -d -m 0700 "$backup"
cp "$stage/energieboard/deploy/backup.py" "$stage/backup.py"
modified=false
stopped=false
rollback() {
  status=$?
  trap - EXIT INT TERM
  set +e
  if $modified; then
    systemctl stop energieboard.service
    mv /opt/energieboard "$backup/failed-app"
    tar -xzf "$backup/application.tar.gz" -C /opt
    if ! /opt/energieboard/.venv/bin/python "$stage/backup.py" restore "$backup/database"; then
      echo "Datenwiederherstellung fehlgeschlagen. Dienst bleibt angehalten. Sicherung: $backup" >&2
      exit "$status"
    fi
    install -m 0644 "$backup/energieboard.service" /etc/systemd/system/energieboard.service
    systemctl daemon-reload
  fi
  if $stopped; then systemctl start energieboard.service; fi
  echo "Update abgebrochen. Sicherung: $backup. Diagnose: journalctl -u energieboard -n 80 --no-pager" >&2
  exit "$status"
}
trap rollback EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
systemctl stop energieboard.service
stopped=true
/opt/energieboard/.venv/bin/python "$stage/energieboard/deploy/backup.py" backup "$backup/database"
tar -czf "$backup/application.tar.gz" -C /opt energieboard
cp /etc/energieboard/energieboard.env "$backup/energieboard.env"
cp /etc/systemd/system/energieboard.service "$backup/energieboard.service"
modified=true
# Preserve external Mongo configuration; update never installs a new database.
mv /opt/energieboard "$backup/previous-app"
mv "$stage/energieboard" /opt/energieboard
# Existing virtual environment remains usable at the same absolute path.
mv "$backup/previous-app/.venv" /opt/energieboard/.venv
bash /opt/energieboard/deploy/install.sh --external-mongo
printf '%s\n' "$commit" > /opt/energieboard/INSTALLED_COMMIT
curl -fsS http://127.0.0.1:8000/api/ >/dev/null
trap - EXIT INT TERM
echo "Update auf $commit erfolgreich. Konfiguration und Historie wurden übernommen. Sicherung: $backup"
