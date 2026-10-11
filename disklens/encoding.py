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
String decoding helpers for robust handling of arbitrary macOS filesystem paths.
"""

import os


def safe_decode(data: bytes | str) -> str:
    """
    Decodes bytes to string safely.
    Uses UTF-8 with surrogateescape (standard POSIX filesystem decoding)
    and falls back to replace so UI never crashes on arbitrary binary filenames.
    """
    if isinstance(data, str):
        return data
    if not isinstance(data, (bytes, bytearray)):
        return str(data)

    try:
        return os.fsdecode(data)
    except Exception:
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return str(data)
