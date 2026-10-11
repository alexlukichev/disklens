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
macOS integration utilities: Full Disk Access check, Finder reveal, Terminal open.
All operations are strictly non-destructive.
"""

import subprocess
from pathlib import Path


def check_full_disk_access() -> bool:
    """
    Probes access to a known TCC-protected location (e.g. ~/Library/Safari or ~/Library/Mail).
    Returns True if accessible, False if restricted.
    """
    probe_path = Path.home() / "Library" / "Safari"
    try:
        if not probe_path.exists():
            return True
        # Try reading directory entries
        list(probe_path.iterdir())
        return True
    except (PermissionError, OSError):
        return False


def open_fda_settings():
    """Opens macOS System Settings at Full Disk Access."""
    subprocess.run([
        "open",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles"
    ], check=False)


def reveal_in_finder(path: str):
    """Reveals the target item in Finder without modifying it."""
    subprocess.run(["open", "-R", path], check=False)


def open_in_terminal(path: str):
    """Opens terminal at directory path."""
    target = Path(path)
    if not target.is_dir():
        target = target.parent
    subprocess.run(["open", "-a", "Terminal", str(target)], check=False)
