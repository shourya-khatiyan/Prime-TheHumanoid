"""Start the VAYN ODrive terminal backend.

Usage:
    python run.py                 # auto transport (native usb, then ascii)
    ODRV_MODE=mock python run.py  # simulated device
Env:
    ODRV_PORT (default 8765), ODRV_MODE (auto|usb|ascii|mock), ODRV_NO_BROWSER=1
"""

from __future__ import annotations

import logging
import os
import threading
import webbrowser

import uvicorn


def main() -> None:
    """Run uvicorn on localhost only and optionally open the browser."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from app.main import FRONTEND_DIST, PORT, app

    if FRONTEND_DIST.exists() and not os.environ.get("ODRV_NO_BROWSER"):
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{PORT}/")).start()
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning", ws_ping_interval=None)


if __name__ == "__main__":
    main()
