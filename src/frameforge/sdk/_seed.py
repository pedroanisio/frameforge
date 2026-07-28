"""Internal process-independent seed derivation shared by SDK randomness."""
from __future__ import annotations

from hashlib import sha256
from typing import Any

__all__ = ["stable_seed"]


def stable_seed(*parts: Any) -> int:
    """Return a process-independent 64-bit integer derived from ``parts``.

    Python's :func:`hash` salts strings and bytes per process.  Stringifying
    parts and hashing their unit-separator-delimited representation preserves
    the established humanize seed contract while remaining stable across
    processes and supported Python versions.
    """
    key = "\x1f".join(str(part) for part in parts)
    return int.from_bytes(sha256(key.encode("utf-8")).digest()[:8], "big")
