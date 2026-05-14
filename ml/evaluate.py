"""
Быстрая CLI-оценка для контейнера ml-train.
Подробная оценка и абляции выполняются в ноутбуке 03.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score

from dataset_io import CLASSES, load_dataset
from models.cnn_resbigru import CnnResBiGRU


def _predict(model: CnnResBiGRU, x: np.ndarray) -> np.ndarray:
    if len(x) == 0:
        return np.empty((0,), dtype=np.int64)
    with torch.no_grad():
        logits = model(torch.from_numpy(x))
        pred = torch.argmax(logits, dim=1)
    return pred.cpu().numpy().astype(np.int64)


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    if len(y_true) == 0:
        return {"samples": 0, "accuracy": None, "macro_f1": None}
    return {
        "samples": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
    }


def main() -> None:
    model_path = Path("experiments/best_model.pt")
    report_path = Path("experiments/eval_report.json")
    if not model_path.exists():
        print("Модель не найдена, сначала запустите train.py")
        return

    synthetic_test_path = Path("data/synthetic/test_synthetic.jsonl")
    real_test_path = Path("data/real/camera_real_test.jsonl")

    synthetic = load_dataset(synthetic_test_path)
    real = load_dataset(real_test_path)

    model = CnnResBiGRU(in_features=99, num_classes=len(CLASSES))
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()

    synthetic_pred = _predict(model, synthetic.x)
    real_pred = _predict(model, real.x)
    synthetic_metrics = _metrics(synthetic.y, synthetic_pred)
    real_metrics = _metrics(real.y, real_pred)

    evaluated_at = datetime.now(timezone.utc).isoformat()
    report = {
        "evaluated_at": evaluated_at,
        "model_path": str(model_path),
        "synthetic_test_dataset": str(synthetic_test_path),
        "real_test_dataset": str(real_test_path),
        "synthetic_metrics": synthetic_metrics,
        "real_metrics": real_metrics,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Дата тестирования: {evaluated_at}")
    print(f"Синтетика: {synthetic_metrics}")
    print(f"Реальные данные с камеры: {real_metrics}")
    print(f"Отчет оценки сохранен: {report_path}")


if __name__ == "__main__":
    main()
