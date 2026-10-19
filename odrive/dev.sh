#!/usr/bin/env bash
# start the backend and the vite dev server together.
#   ./dev.sh        mode from backend/.env
#   ./dev.sh mock   override .env for this run
set -euo pipefail
root="$(cd "$(dirname "$0")" && pwd)"
py="$root/backend/.venv/bin/python"
[ -x "$py" ] || py="$root/backend/.venv/Scripts/python.exe"
# a mode argument overrides backend/.env; otherwise run.py reads the file
if [ -n "${1:-}" ]; then
  export ODRV_MODE="$1"
fi
# vite is the ui in dev, so do not also open the backend page
export ODRV_NO_BROWSER=1
(cd "$root/backend" && "$py" run.py) &
backend=$!
trap 'kill $backend 2>/dev/null || true' EXIT
sleep 2
cd "$root/frontend" && npm run dev
