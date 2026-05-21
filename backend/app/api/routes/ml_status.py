import json
import os
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/ml", tags=["ml"])


def _line_count(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


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

    status = {}
    if status_path.exists():
        status = json.loads(status_path.read_text(encoding="utf-8"))

    eval_report: dict = {}
    if eval_path.exists():
        eval_report = json.loads(eval_path.read_text(encoding="utf-8"))

    return {
        "autotrain": status,
        "live_train_samples": _line_count(live_train_path),
        "model_exists": model_path.exists(),
        "model_path": str(model_path),
        "evaluated_at": eval_report.get("evaluated_at"),
        "synthetic_macro_f1": (eval_report.get("synthetic_metrics") or {}).get("macro_f1"),
        "real_macro_f1": (eval_report.get("real_metrics") or {}).get("macro_f1"),
    }
