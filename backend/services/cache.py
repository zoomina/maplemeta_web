from __future__ import annotations

import time
from typing import Any, Callable

_store: dict[str, tuple[float, Any]] = {}


def ttl_cached(key: str, ttl: float, fn: Callable[[], Any]) -> Any:
    """Return cached value for *key* if not older than *ttl* seconds; call *fn* otherwise."""
    now = time.monotonic()
    entry = _store.get(key)
    if entry is not None:
        ts, val = entry
        if now - ts < ttl:
            return val
    val = fn()
    _store[key] = (now, val)
    return val


def invalidate(prefix: str = "") -> None:
    """Remove entries whose key starts with *prefix* (or all entries if empty)."""
    if not prefix:
        _store.clear()
        return
    for key in list(_store.keys()):
        if key.startswith(prefix):
            del _store[key]
