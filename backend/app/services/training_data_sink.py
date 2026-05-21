import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


LIVE_SESSIONS_PATH = Path(
    os.getenv(
        "GYMNET_LIVE_SESSIONS_PATH",
        str(Path(__file__).resolve().parents[3] / "ml" / "data" / "real" / "live_sessions.jsonl"),
    )
)
LIVE_TRAIN_PATH = Path(
    os.getenv(
        "GYMNET_LIVE_TRAIN_PATH",
        str(Path(__file__).resolve().parents[3] / "ml" / "data" / "real" / "live_train.jsonl"),
    )
)
SAMPLE_THROTTLE_SECONDS = float(os.getenv("GYMNET_LIVE_TRAIN_THROTTLE_SECONDS", "3.0"))

_lock = Lock()
_last_train_sample_at: dict[str, float] = {}


def append_completed_session_sample(
    *,
    zone_id: str,
    exercise: str,
    dwell_seconds: int,
    total_exercise_seconds: int,
    total_rep_count: int,
    form_score: float,
) -> None:
    sample = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "zone_id": zone_id,
        "exercise": exercise,
        "dwell_seconds": dwell_seconds,
        "total_exercise_seconds": total_exercise_seconds,
        "total_rep_count": total_rep_count,
        "form_score": round(form_score, 2),
    }
    LIVE_SESSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        with LIVE_SESSIONS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")


def append_live_training_window(
    *,
    zone_id: str,
    exercise: str,
    window: list[list[float]],
    force: bool = False,
) -> bool:
    """Сохраняет окно [13, 99] для дообучения CNN-ResBiGRU."""
    if len(window) != 13 or any(len(frame) != 99 for frame in window):
        return False

    now = time.time()
    with _lock:
        last_at = _last_train_sample_at.get(zone_id, 0.0)
        if not force and (now - last_at) < SAMPLE_THROTTLE_SECONDS:
            return False

        row = {
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source": "camera_live",
            "zone_id": zone_id,
            "label": exercise,
            "sequence": window,
        }
        LIVE_TRAIN_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LIVE_TRAIN_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        _last_train_sample_at[zone_id] = now
    return True
