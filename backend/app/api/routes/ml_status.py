import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter

from app.services.exercise_classifier import (
    cuda_available,
    inference_device,
    ml_available,
    ml_unavailable_reason,
)

router = APIRouter(prefix="/ml", tags=["ml"])
logger = logging.getLogger(__name__)


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    try:
        with path.open("r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except OSError:
        logger.exception("Не удалось прочитать файл: %s", path.name)
        return 0


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("Не удалось разобрать JSON: %s", path.name)
        return {}


@router.get("/status")
def get_ml_status() -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    status_path = Path(
        os.getenv(
            "GYMNET_AUTORETRAIN_SHARED_STATUS_PATH",
            str(repo_root / "ml" / "experiments" / "auto_retrain_status.json"),
        )
    )
    live_train_path = Path(
        os.getenv(
            "GYMNET_LIVE_TRAIN_PATH",
            str(repo_root / "ml" / "data" / "real" / "live_train.jsonl"),
        )
    )
    model_path = Path(
        os.getenv(
            "GYMNET_SHARED_MODEL_PATH",
            str(repo_root / "ml" / "experiments" / "best_model.pt"),
        )
    )
    eval_path = Path(
        os.getenv(
            "GYMNET_SHARED_EVAL_PATH",
            str(repo_root / "ml" / "experiments" / "eval_report.json"),
        )
    )

    status = _read_json(status_path)
    eval_report = _read_json(eval_path)

    return {
        "autotrain": status,
        "live_train_samples": _line_count(live_train_path),
        "live_classification": "ml" if ml_available() else "heuristic",
        "inference_device": inference_device(),
        "cuda_available": cuda_available(),
        "ml_unavailable_reason": ml_unavailable_reason(),
        "model_exists": model_path.exists(),
        "autotrain_last_error": status.get("last_error"),
        "evaluated_at": eval_report.get("evaluated_at"),
        "synthetic_macro_f1": (eval_report.get("synthetic_metrics") or {}).get("macro_f1"),
        "real_macro_f1": (eval_report.get("real_metrics") or {}).get("macro_f1"),
    }
