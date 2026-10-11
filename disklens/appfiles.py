# Copyright 2026 Alexander Lukichev
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
