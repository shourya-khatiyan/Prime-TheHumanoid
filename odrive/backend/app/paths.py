"""Filesystem locations used by the backend (works from source and from a PyInstaller bundle)."""

from __future__ import annotations

import sys
from pathlib import Path

# bundled read-only files live next to the code (or in the pyinstaller temp dir)
BUNDLE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
METADATA_DIR = BUNDLE / "metadata"
PROFILES_DIR = BUNDLE / "profiles"
FRONTEND_DIST = BUNDLE / "frontend_dist" if hasattr(sys, "_MEIPASS") else BUNDLE.parent / "frontend" / "dist"

# writable runtime data lives next to the exe (or in backend/data when run from source)
DATA_DIR = (Path(sys.executable).parent if hasattr(sys, "_MEIPASS") else BUNDLE) / "data"
RECORDINGS_DIR = DATA_DIR / "recordings"
BACKUPS_DIR = DATA_DIR / "backups"
REPORTS_DIR = DATA_DIR / "reports"
FIRMWARE_DIR = DATA_DIR / "firmware"
AUDIT_DB = DATA_DIR / "audit.db"
TOKEN_FILE = DATA_DIR / ".session-token"
USER_PROFILE = DATA_DIR / "profile.yaml"


def ensure_dirs() -> None:
    """Create all writable data folders if they are missing."""
    for d in (DATA_DIR, RECORDINGS_DIR, BACKUPS_DIR, REPORTS_DIR, FIRMWARE_DIR):
        d.mkdir(parents=True, exist_ok=True)
