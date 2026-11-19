#!/usr/bin/env bash
set -euo pipefail
umask 022
trap 'printf "Installation bei Zeile %s abgebrochen. Details stehen in der vorigen Fehlermeldung.\n" "$LINENO" >&2' ERR

fail() {
  printf '%s\n' "$*" >&2
  exit 1
}

usage() {
  printf '%s\n' 'Aufruf im Debian-LXC: bash /opt/energieboard/deploy/install.sh [--external-mongo]'
}

install_local_mongo=true
case "${1:-}" in
  "") ;;
  --external-mongo) install_local_mongo=false ;;
  -h|--help) usage; exit 0 ;;
  *) usage >&2; exit 2 ;;
esac
(( $# <= 1 )) || fail "Nur eine Option ist zulässig."
(( EUID == 0 )) || fail "Das Skript in der LXC-Konsole als root ausführen."
# shellcheck source=/dev/null
source /etc/os-release
[[ "$ID" == debian && "${VERSION_CODENAME:-}" == bookworm && "$(dpkg --print-architecture)" == amd64 ]] \
  || fail "Dieser Installer ist für Debian 12 Bookworm amd64 vorbereitet."

app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
[[ "$app_dir" == /opt/energieboard ]] || fail "Das Archiv zuerst nach /opt entpacken, sodass /opt/energieboard existiert."
[[ -d /run/systemd/system ]] || fail "Die Installation benötigt einen gestarteten Container mit systemd."
[[ -f "$app_dir/app/frontend/dist/index.html" && -d "$app_dir/app/frontend/dist/assets" ]] \
  || fail "Die gebaute Oberfläche fehlt. Das LXC-Archiv verwenden oder das Frontend vorab mit npm run build bauen."

config_dir=/etc/energieboard
env_file="$config_dir/energieboard.env"
if ! $install_local_mongo && [[ ! -s "$env_file" ]]; then
  fail "Für externe MongoDB zuerst $env_file mit MONGO_URL und DB_NAME anlegen."
fi

if $install_local_mongo; then
  grep -qw avx /proc/cpuinfo \
    || fail "Lokale MongoDB benötigt AVX. Alternativ --external-mongo verwenden."
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl python3-venv

if $install_local_mongo; then
  if ! command -v mongod >/dev/null; then
    apt-get install -y gnupg
    keyring=/usr/share/keyrings/mongodb-server-8.0.gpg
    curl -fsSL https://pgp.mongodb.com/server-8.0.asc | gpg --batch --yes --dearmor -o "$keyring"
    chmod 644 "$keyring"
    printf '%s\n' 'deb [arch=amd64 signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg] https://repo.mongodb.org/apt/debian bookworm/mongodb-org/8.0 main' \
      > /etc/apt/sources.list.d/mongodb-org-8.0.list
    apt-get update
    apt-get install -y mongodb-org-server
    install -d -m 0755 /etc/systemd/system/mongod.service.d
    install -m 0644 "$app_dir/deploy/mongod-cache.conf" /etc/systemd/system/mongod.service.d/energieboard-cache.conf
    systemctl daemon-reload
    systemctl restart mongod.service
  fi
  systemctl daemon-reload
  systemctl enable --now mongod.service
fi

if ! getent group energieboard >/dev/null; then
  groupadd --system energieboard
fi
if ! id energieboard >/dev/null 2>&1; then
  useradd --system --gid energieboard --no-create-home --home-dir "$app_dir" --shell /usr/sbin/nologin energieboard
fi
install -d -m 0700 "$config_dir"
if [[ ! -e "$env_file" ]]; then
  install -m 0600 "$app_dir/deploy/energieboard.env.example" "$env_file"
fi
chown root:root "$env_file"
chmod 0600 "$env_file"

if systemctl is-active --quiet energieboard.service; then
  systemctl stop energieboard.service
fi
python3 -m venv "$app_dir/.venv"
"$app_dir/.venv/bin/python" -m pip install --disable-pip-version-check -r "$app_dir/app/backend/requirements.txt"
chmod a+rx "$app_dir" "$app_dir/app" "$app_dir/app/frontend"
find "$app_dir/app/backend" "$app_dir/app/frontend/dist" -type d -exec chmod a+rx {} +
find "$app_dir/app/backend" -type f -name '*.py' -exec chmod a+r {} +
find "$app_dir/app/frontend/dist" -type f -exec chmod a+r {} +
chmod -R a+rX "$app_dir/.venv"
"$app_dir/.venv/bin/python" "$app_dir/deploy/check.py"
install -m 0644 "$app_dir/deploy/energieboard.service" /etc/systemd/system/energieboard.service
systemctl daemon-reload
systemctl reset-failed energieboard.service || true
systemctl enable energieboard.service
systemctl restart energieboard.service

if ! curl --fail --silent --show-error --retry 15 --retry-all-errors --retry-delay 1 --max-time 2 \
    http://127.0.0.1:8000/api/ >/dev/null || ! systemctl is-active --quiet energieboard.service; then
  journalctl -u energieboard.service -n 30 --no-pager >&2
  fail "Energieboard ist noch nicht erreichbar. Details: journalctl -u energieboard -n 60 --no-pager"
fi
curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8000/system \
  | grep -q 'id="root"' || fail "Die API läuft, aber die Oberfläche ist nicht vollständig."
printf '%s\n' 'Energieboard läuft. Im Browser die IP des LXC mit Port 8000 und Pfad /system öffnen.'
