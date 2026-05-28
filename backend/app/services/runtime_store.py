from collections import deque

from app.services.sadla import SadlaState
from app.services.state import ZoneState


zone_store: dict[str, ZoneState] = {}
sadla_store: dict[str, SadlaState] = {}
history_store: dict[str, deque[int]] = {}


def history_as_list(zone_id: str) -> list[int]:
    """deque не сериализуется в JSON — для API всегда отдаём list."""
    bucket = history_store.get(zone_id)
    if bucket is None:
        return []
    return list(bucket)
