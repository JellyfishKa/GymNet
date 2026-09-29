"""Гистерезис присутствия в ROI по кадрам."""

from __future__ import annotations

from collections import defaultdict

ENTER_FRAMES = 3
EXIT_FRAMES = 3

_present_streak: dict[str, int] = defaultdict(int)
_absent_streak: dict[str, int] = defaultdict(int)
_stable_present: dict[str, bool] = defaultdict(bool)


def update_zone_presence(zone_id: str, raw_in_roi: bool) -> bool:
    """Стабильное is_present: 3 кадра вход, 3 кадра выход."""
    if raw_in_roi:
        _present_streak[zone_id] += 1
        _absent_streak[zone_id] = 0
        if not _stable_present[zone_id] and _present_streak[zone_id] >= ENTER_FRAMES:
            _stable_present[zone_id] = True
    else:
        _absent_streak[zone_id] += 1
        _present_streak[zone_id] = 0
        if _stable_present[zone_id] and _absent_streak[zone_id] >= EXIT_FRAMES:
            _stable_present[zone_id] = False

    return _stable_present[zone_id]


def reset_zone_presence(zone_id: str) -> None:
    _present_streak.pop(zone_id, None)
    _absent_streak.pop(zone_id, None)
    _stable_present.pop(zone_id, None)


def cleanup_zone_presence(zone_id: str) -> None:
    """Remove all tracking state for a zone to prevent unbounded dict growth."""
    _present_streak.pop(zone_id, None)
    _absent_streak.pop(zone_id, None)
    _stable_present.pop(zone_id, None)
