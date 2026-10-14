#!/usr/bin/env bash
# start the backend and the vite dev server together.
#   ./dev.sh        real device
#   ./dev.sh mock   simulated device
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
py="$root/backend/.venv/bin/python"
[ -x "$py" ] || py="$root/backend/.venv/Scripts/python.exe"
(cd "$root/backend" && ODRV_MODE="${1:-auto}" ODRV_NO_BROWSER=1 "$py" run.py) &
backend=$!
trap 'kill $backend 2>/dev/null || true' EXIT
sleep 2
cd "$root/frontend" && npm run dev
