import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


LIVE_SESSIONS_PATH = Path(__file__).resolve().parents[3] / "ml" / "data" / "real" / "live_sessions.jsonl"
_lock = Lock()


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
