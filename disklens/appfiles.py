"""
The ONLY module in DiskLens allowed to create and write application data.
Enforces read-only safety policy.
"""

import os
from pathlib import Path

APP_DATA_DIR = Path.home() / "Library" / "Application Support" / "DiskLens"
LOGS_DIR = Path.home() / "Library" / "Logs" / "DiskLens"


def ensure_dirs():
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def get_snapshot_path(volume_uuid: str) -> Path:
    ensure_dirs()
    return APP_DATA_DIR / f"{volume_uuid}.dlsnap"


def get_log_file_path(name: str = "disklens.log") -> Path:
    ensure_dirs()
    return LOGS_DIR / name
