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
