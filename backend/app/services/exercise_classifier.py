"""Классификация упражнения: CNN-ResBiGRU + эвристики + сглаживание."""

from __future__ import annotations

import logging
import os
from collections import defaultdict, deque
from pathlib import Path

import numpy as np

from app.models.cnn_resbigru import CnnResBiGRU

logger = logging.getLogger(__name__)

EXERCISES = ["PushUps", "Squats", "RunInPlace"]
SMOOTHING_WINDOW = 5
IN_FEATURES = 99
NUM_CLASSES = 3

_model: CnnResBiGRU | None = None
_model_loaded = False
_prediction_buffers: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=SMOOTHING_WINDOW))


def _model_path() -> Path | None:
    env_path = os.environ.get("GYMNET_SHARED_MODEL_PATH")
    if env_path:
        candidate = Path(env_path)
        if candidate.exists():
            return candidate
    repo_root = Path(__file__).resolve().parents[3]
    for rel in ("ml/experiments/best_model.pt", "experiments/best_model.pt"):
        candidate = repo_root / rel
        if candidate.exists():
            return candidate
    return None


def _load_model() -> CnnResBiGRU | None:
    global _model, _model_loaded
    if _model_loaded:
        return _model
    _model_loaded = True
    path = _model_path()
    if path is None:
        logger.info("ML-модель не найдена, используются эвристики")
        return None
    try:
        import torch

        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
        state = checkpoint.get("model_state", checkpoint)
        num_classes = int(checkpoint.get("num_classes", NUM_CLASSES))
        if num_classes != NUM_CLASSES:
            logger.warning(
                "Модель с %s классами несовместима с %s, эвристики",
                num_classes,
                NUM_CLASSES,
            )
            return None
        model = CnnResBiGRU(in_features=IN_FEATURES, num_classes=num_classes)
        model.load_state_dict(state)
        model.eval()
        _model = model
        logger.info("Загружена ML-модель: %s", path)
        return _model
    except Exception:
        logger.exception("Не удалось загрузить ML-модель")
        return None


def ml_available() -> bool:
    return _load_model() is not None


def _predict_ml(window: np.ndarray) -> tuple[str, float]:
    import torch

    model = _load_model()
    if model is None:
        raise RuntimeError("ML недоступен")
    tensor = torch.from_numpy(window.astype(np.float32)).unsqueeze(0)
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)[0]
        idx = int(torch.argmax(probs).item())
        confidence = float(probs[idx].item())
    return EXERCISES[idx], confidence


def _point_in_roi(point: tuple[float, float] | None, roi_bounds: tuple[float, float, float, float]) -> bool:
    if point is None:
        return False
    x_min, y_min, x_max, y_max = roi_bounds
    x, y = point
    return x_min <= x <= x_max and y_min <= y <= y_max


from app.services.exercise_profiles import classify_heuristic_detailed


def classify_heuristic(
    landmarks: dict[str, tuple[float, float]],
    window: list[list[float]] | None = None,
) -> str:
    label, _, _ = classify_heuristic_detailed(landmarks, window)
    return label


def _smooth(zone_id: str, label: str) -> str:
    buf = _prediction_buffers[zone_id]
    buf.append(label)
    counts: dict[str, int] = {}
    for item in buf:
        counts[item] = counts.get(item, 0) + 1
    return max(counts, key=counts.get)


def _window_array(window: np.ndarray | list[list[float]] | None) -> np.ndarray | None:
    if window is None:
        return None
    arr = np.asarray(window, dtype=np.float32)
    if arr.ndim == 2 and arr.shape == (13, 99):
        return arr
    return None


def classify_exercise(
    zone_id: str,
    *,
    window: np.ndarray | list[list[float]] | None,
    landmarks: dict[str, tuple[float, float]],
) -> tuple[str, str, float | None, dict[str, float], dict[str, float | None]]:
    """
    Возвращает (exercise, source, confidence, scores, debug_metrics).
    source: "ml" | "heuristic" | "heuristic_override"
    """
    window_list = None
    window_arr = _window_array(window)
    if window_arr is not None:
        window_list = window_arr.tolist()

    heur_label, scores, debug = classify_heuristic_detailed(landmarks, window_list)
    raw_label = heur_label
    confidence: float | None = None
    source = "heuristic"

    override_margin = float(os.environ.get("GYMNET_HEURISTIC_OVERRIDE_MARGIN", "0.22"))
    if window_arr is not None and _load_model() is not None:
        try:
            ml_label, confidence = _predict_ml(window_arr)
            raw_label = ml_label
            source = "ml"
            heur_best = scores.get(heur_label, 0.0)
            ml_score = scores.get(ml_label, 0.0)
            if (
                heur_label != ml_label
                and heur_best >= ml_score + override_margin
                and heur_best >= 0.45
            ):
                raw_label = heur_label
                source = "heuristic_override"
                confidence = heur_best
        except Exception:
            logger.exception("Ошибка ML-inference, fallback на эвристики")

    exercise = _smooth(zone_id, raw_label)
    if confidence is None and source.startswith("heuristic"):
        confidence = scores.get(exercise, scores.get(heur_label))
    return exercise, source, confidence, scores, debug


def clear_classifier_state(zone_id: str) -> None:
    _prediction_buffers.pop(zone_id, None)
