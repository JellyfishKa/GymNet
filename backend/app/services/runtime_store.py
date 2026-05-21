from collections import deque

from app.services.sadla import SadlaState
from app.services.state import ZoneState


zone_store: dict[str, ZoneState] = {}
sadla_store: dict[str, SadlaState] = {}
history_store: dict[str, deque[int]] = {}
