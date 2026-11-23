#!/usr/bin/env bash
# Expected connection refusals during startup stay quiet; final failures remain visible.
set -euo pipefail
attempts="${1:-30}"
delay="${2:-1}"
[[ "$attempts" =~ ^[0-9]+$ && "$delay" =~ ^[0-9]+$ ]] && (( attempts >= 1 && attempts <= 120 && delay <= 10 )) || exit 2
ready_error="$(mktemp)"
for (( attempt=1; attempt<=attempts; attempt++ )); do
  if curl --fail --silent --show-error --connect-timeout 1 --max-time 2 http://127.0.0.1:8000/api/ >/dev/null 2>"$ready_error" && systemctl is-active --quiet energieboard.service; then
    rm -f "$ready_error"
    exit 0
  fi
  if (( attempt == 1 )); then printf '%s\n' 'Warte auf Startbereitschaft von Energieboard ...'; fi
  if (( attempt < attempts )); then sleep "$delay"; fi
done
printf '%s\n' 'Energieboard wurde innerhalb der Startfrist nicht bereit.' >&2
cat "$ready_error" >&2
rm -f "$ready_error"
exit 1
