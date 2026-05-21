"""Блокировки по zone_id для потокобезопасного доступа к состоянию зоны."""

from __future__ import annotations

from threading import Lock

_locks: dict[str, Lock] = {}
_registry_lock = Lock()


def zone_lock(zone_id: str) -> Lock:
    with _registry_lock:
        if zone_id not in _locks:
            _locks[zone_id] = Lock()
        return _locks[zone_id]
