"""Start the VAYN ODrive terminal backend.

Usage:
    python run.py                 # uses backend/.env, then built-in defaults
    ODRV_MODE=mock python run.py  # a shell value overrides the .env file
Env:
    ODRV_PORT (default 8765), ODRV_MODE (auto|usb|ascii|mock), ODRV_NO_BROWSER=1
"""

from __future__ import annotations

import logging
import os
import threading
import webbrowser
from pathlib import Path

import uvicorn


def load_env(path: Path) -> None:
    """Set missing environment variables from a KEY=VALUE file.

    Inputs: path to a .env file. Outputs: none. A variable already set in the
    shell is left as-is. Blank lines and lines starting with # are skipped.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def main() -> None:
    """Run uvicorn on localhost only and optionally open the browser."""
    load_env(Path(__file__).resolve().parent / ".env")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from app.main import FRONTEND_DIST, PORT, app

    if FRONTEND_DIST.exists() and not os.environ.get("ODRV_NO_BROWSER"):
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}/")).start()
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning", ws_ping_interval=None)


if __name__ == "__main__":
    main()
