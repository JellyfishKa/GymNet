"""
Фоновый авто-retrain:
- мониторит новые завершенные сессии (live_sessions.jsonl)
- запускает train.py + evaluate.py по порогу новых сэмплов
- применяет safe-switch: откат модели при ошибке/просадке метрики
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LIVE_SESSIONS_PATH = Path(os.getenv("GYMNET_LIVE_SESSIONS_PATH", str(ROOT / "data" / "real" / "live_sessions.jsonl")))
LIVE_TRAIN_PATH = Path(os.getenv("GYMNET_LIVE_TRAIN_PATH", str(ROOT / "data" / "real" / "live_train.jsonl")))
STATE_PATH = Path(os.getenv("GYMNET_AUTORETRAIN_STATE_PATH", str(ROOT / "experiments" / "auto_retrain_status.json")))
SHARED_STATUS_PATH = Path(os.getenv("GYMNET_AUTORETRAIN_SHARED_STATUS_PATH", ""))
SHARED_MODEL_PATH = Path(os.getenv("GYMNET_SHARED_MODEL_PATH", ""))
SHARED_EVAL_PATH = Path(os.getenv("GYMNET_SHARED_EVAL_PATH", ""))
MODEL_PATH = ROOT / "experiments" / "best_model.pt"
TRAIN_REPORT_PATH = ROOT / "experiments" / "train_report.json"
EVAL_REPORT_PATH = ROOT / "experiments" / "eval_report.json"

MIN_NEW_SESSIONS = int(os.getenv("GYMNET_AUTORETRAIN_MIN_NEW_SESSIONS", "12"))
MIN_NEW_TRAIN_SAMPLES = int(os.getenv("GYMNET_AUTORETRAIN_MIN_NEW_TRAIN_SAMPLES", "8"))
COOLDOWN_SECONDS = int(os.getenv("GYMNET_AUTORETRAIN_COOLDOWN_SECONDS", "900"))
POLL_SECONDS = int(os.getenv("GYMNET_AUTORETRAIN_POLL_SECONDS", "20"))
MAX_ALLOWED_DROP = float(os.getenv("GYMNET_AUTORETRAIN_MAX_F1_DROP", "0.02"))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if SHARED_STATUS_PATH:
        SHARED_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SHARED_STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def _run_step(title: str, cmd: list[str]) -> None:
    print(f"\n[{_utc_now()}] {title}: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def _synthetic_f1(path: Path) -> float | None:
    payload = _read_json(path)
    metrics = payload.get("synthetic_metrics") if isinstance(payload, dict) else None
    if not isinstance(metrics, dict):
        return None
    value = metrics.get("macro_f1")
    return float(value) if value is not None else None


def _safe_retrain(py: str, state: dict) -> tuple[bool, str]:
    model_backup = MODEL_PATH.with_suffix(".pt.bak")
    eval_backup = EVAL_REPORT_PATH.with_suffix(".json.bak")
    train_backup = TRAIN_REPORT_PATH.with_suffix(".json.bak")

    prev_f1 = _synthetic_f1(EVAL_REPORT_PATH)
    if MODEL_PATH.exists():
        shutil.copy2(MODEL_PATH, model_backup)
    if EVAL_REPORT_PATH.exists():
        shutil.copy2(EVAL_REPORT_PATH, eval_backup)
    if TRAIN_REPORT_PATH.exists():
        shutil.copy2(TRAIN_REPORT_PATH, train_backup)

    try:
        _run_step("Auto-retrain: merge datasets", [py, "merge_datasets.py"])
        _run_step("Auto-retrain: train", [py, "train.py"])
        _run_step("Auto-retrain: evaluate", [py, "evaluate.py"])

        new_f1 = _synthetic_f1(EVAL_REPORT_PATH)
        if prev_f1 is not None and new_f1 is not None and new_f1 < prev_f1 - MAX_ALLOWED_DROP:
            raise RuntimeError(
                f"Откат: synthetic macro_f1 ухудшился ({prev_f1:.4f} -> {new_f1:.4f}, drop>{MAX_ALLOWED_DROP})"
            )

        for backup in (model_backup, eval_backup, train_backup):
            if backup.exists():
                backup.unlink()
        if SHARED_MODEL_PATH and MODEL_PATH.exists():
            SHARED_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(MODEL_PATH, SHARED_MODEL_PATH)
        if SHARED_EVAL_PATH and EVAL_REPORT_PATH.exists():
            SHARED_EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(EVAL_REPORT_PATH, SHARED_EVAL_PATH)
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        if model_backup.exists():
            shutil.copy2(model_backup, MODEL_PATH)
            model_backup.unlink()
        if eval_backup.exists():
            shutil.copy2(eval_backup, EVAL_REPORT_PATH)
            eval_backup.unlink()
        if train_backup.exists():
            shutil.copy2(train_backup, TRAIN_REPORT_PATH)
            train_backup.unlink()
        state["last_error"] = str(exc)
        return False, str(exc)


def main() -> None:
    py = sys.executable
    state = _read_json(STATE_PATH)
    state.setdefault("last_seen_sessions", 0)
    state.setdefault("last_seen_train_samples", 0)
    state.setdefault("last_retrain_at", None)
    state.setdefault("runs", 0)

    print(
        f"Auto-retrain watcher стартовал: min_new={MIN_NEW_SESSIONS}, "
        f"cooldown={COOLDOWN_SECONDS}s, poll={POLL_SECONDS}s, "
        f"live_sessions={LIVE_SESSIONS_PATH}, live_train={LIVE_TRAIN_PATH}"
    )

    while True:
        try:
            seen_sessions = int(state.get("last_seen_sessions", 0))
            current_sessions = _line_count(LIVE_SESSIONS_PATH)
            new_sessions = max(0, current_sessions - seen_sessions)

            seen_train = int(state.get("last_seen_train_samples", 0))
            current_train = _line_count(LIVE_TRAIN_PATH)
            new_train_samples = max(0, current_train - seen_train)

            last_retrain_raw = state.get("last_retrain_at")
            last_retrain_ts = (
                datetime.fromisoformat(last_retrain_raw).timestamp() if isinstance(last_retrain_raw, str) else 0.0
            )
            cooldown_passed = (time.time() - last_retrain_ts) >= COOLDOWN_SECONDS

            should_retrain = (
                new_train_samples >= MIN_NEW_TRAIN_SAMPLES or new_sessions >= MIN_NEW_SESSIONS
            ) and cooldown_passed

            if should_retrain:
                print(
                    f"[{_utc_now()}] Триггер retrain: train_samples={new_train_samples}, "
                    f"sessions={new_sessions}"
                )
                ok, details = _safe_retrain(py, state)
                state["runs"] = int(state.get("runs", 0)) + 1
                state["last_retrain_at"] = _utc_now()
                state["last_result"] = "success" if ok else "failed"
                state["last_details"] = details
                if ok:
                    state["last_seen_sessions"] = current_sessions
                    state["last_seen_train_samples"] = current_train
                    state.pop("last_error", None)

            state["current_seen_sessions"] = current_sessions
            state["current_seen_train_samples"] = current_train
            state["pending_sessions"] = max(0, current_sessions - int(state.get("last_seen_sessions", 0)))
            state["pending_train_samples"] = max(0, current_train - int(state.get("last_seen_train_samples", 0)))
            _write_json(STATE_PATH, state)
            time.sleep(POLL_SECONDS)
        except Exception as exc:  # noqa: BLE001
            state["last_result"] = "watcher_error"
            state["last_error"] = str(exc)
            _write_json(STATE_PATH, state)
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
