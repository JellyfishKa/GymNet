"""Классификация упражнения: CNN-ResBiGRU + эвристики + сглаживание."""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
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
_model_device: str | None = None
_ml_unavailable_reason: str | None = None
_prediction_buffers: dict[str, deque[str]] = defaultdict(lambda: deque(maxlen=SMOOTHING_WINDOW))
# Кэш ML-inference для live ingest (CPU в Docker иначе >8 с на кадр).
_ml_live_cache: dict[
    str, tuple[float, dict[str, float] | None, dict[str, float], str, float | None, str]
] = {}
LIVE_ML_INTERVAL_SEC = float(os.getenv("GYMNET_LIVE_ML_INTERVAL_SEC", "2.5"))
LIVE_ML_TIMEOUT_SEC = float(os.getenv("GYMNET_LIVE_ML_TIMEOUT_SEC", "3.0"))
_ml_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gymnet-ml")


def _live_ml_disabled() -> bool:
    return os.getenv("GYMNET_DISABLE_LIVE_ML", "").lower() in ("1", "true", "yes")


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


def ml_unavailable_reason() -> str | None:
    _load_model()
    return _ml_unavailable_reason


def inference_device() -> str:
    """cuda при доступности GPU (Docker: compose.gpu.yml + gpus: all)."""
    forced = os.getenv("GYMNET_DEVICE", "").strip().lower()
    if forced in ("cuda", "cpu"):
        return forced
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def cuda_available() -> bool:
    import torch

    return torch.cuda.is_available()


def _load_model() -> CnnResBiGRU | None:
    global _model, _model_loaded, _model_device, _ml_unavailable_reason
    if _model_loaded:
        return _model
    _model_loaded = True
    path = _model_path()
    if path is None:
        _ml_unavailable_reason = "файл модели не найден"
        logger.info("ML-модель не найдена, используются эвристики")
        return None
    try:
        import torch

        device = inference_device()
        checkpoint = torch.load(path, map_location=device, weights_only=False)
        state = checkpoint.get("model_state", checkpoint)
        num_classes = int(checkpoint.get("num_classes", NUM_CLASSES))
        if num_classes != NUM_CLASSES:
            _ml_unavailable_reason = f"модель на {num_classes} классов, ожидается {NUM_CLASSES}"
            logger.warning(
                "Модель с %s классами несовместима с %s, эвристики",
                num_classes,
                NUM_CLASSES,
            )
            return None
        model = CnnResBiGRU(in_features=IN_FEATURES, num_classes=num_classes)
        model.load_state_dict(state)
        model.to(device)
        model.eval()
        _model = model
        _model_device = device
        _ml_unavailable_reason = None
        logger.info("Загружена ML-модель: %s (device=%s)", path, device)
        return _model
    except Exception as exc:
        _ml_unavailable_reason = f"ошибка загрузки: {exc}"
        logger.exception("Не удалось загрузить ML-модель")
        return None


def ml_available() -> bool:
    return _load_model() is not None


def _predict_ml_probs(window: np.ndarray) -> dict[str, float]:
    import torch

    model = _load_model()
    if model is None:
        raise RuntimeError("ML недоступен")
    device = inference_device()
    tensor = torch.from_numpy(window.astype(np.float32)).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)[0]
    return {EXERCISES[i]: float(probs[i].item()) for i in range(len(EXERCISES))}


def _predict_ml_probs_bounded(window: np.ndarray) -> dict[str, float] | None:
    """На CPU — таймаут; на CUDA — прямой вызов (ингест не упирается в nginx 504)."""
    if inference_device() == "cuda":
        try:
            return _predict_ml_probs(window)
        except Exception:
            logger.exception("Ошибка ML-inference на CUDA")
            return None
    future = _ml_executor.submit(_predict_ml_probs, window)
    try:
        return future.result(timeout=LIVE_ML_TIMEOUT_SEC)
    except FuturesTimeoutError:
        logger.warning("ML-inference timeout (%.1fs), эвристики", LIVE_ML_TIMEOUT_SEC)
        future.cancel()
        return None


def _fuse_ml_and_heuristic(
    ml_probs: dict[str, float],
    heur_scores: dict[str, float],
    landmarks: dict[str, tuple[float, float]],
    window_list: list[list[float]] | None,
) -> tuple[str, float, str, dict[str, float]]:
    """Слияние ML + эвристики с общими pose-gates (те же правила, что у эвристик)."""
    weight = float(os.environ.get("GYMNET_ML_FUSION_WEIGHT", "0.55"))
    fused: dict[str, float] = {}
    for name in EXERCISES:
        fused[name] = weight * ml_probs.get(name, 0.0) + (1.0 - weight) * heur_scores.get(name, 0.0)
    gated = apply_discrimination_gates(landmarks, fused, window=window_list)
    ranked = sorted(gated.items(), key=lambda item: item[1], reverse=True)
    label, score = ranked[0]
    ml_label = max(ml_probs, key=ml_probs.get)
    heur_label = max(heur_scores, key=heur_scores.get)
    if label == ml_label and label != heur_label:
        source = "ml"
    elif label == heur_label and label != ml_label:
        source = "heuristic_override"
    else:
        source = "ml"
    return label, score, source, gated


def _point_in_roi(point: tuple[float, float] | None, roi_bounds: tuple[float, float, float, float]) -> bool:
    if point is None:
        return False
    x_min, y_min, x_max, y_max = roi_bounds
    x, y = point
    return x_min <= x <= x_max and y_min <= y <= y_max


from app.services.exercise_profiles import apply_discrimination_gates, classify_heuristic_detailed


def classify_heuristic(
    landmarks: dict[str, tuple[float, float]],
    window: list[list[float]] | None = None,
) -> str:
    label, _, _, _ = classify_heuristic_detailed(landmarks, window)
    return label


def _smooth(zone_id: str, label: str) -> str:
    buf = _prediction_buffers[zone_id]
    buf.append(label)
    counts: dict[str, int] = {}
    for item in buf:
        counts[item] = counts.get(item, 0) + 1
    if not counts:
        return label
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
) -> tuple[
    str,
    str,
    float | None,
    dict[str, float],
    dict[str, float | None],
    str,
    dict[str, float] | None,
    dict[str, float],
]:
    """
    Возвращает (exercise, source, confidence, classification_scores, debug, orientation,
    ml_probs, heuristic_scores).
    """
    window_list = None
    window_arr = _window_array(window)
    if window_arr is not None:
        window_list = window_arr.tolist()

    heur_label, heuristic_scores, debug, body_orientation = classify_heuristic_detailed(
        landmarks, window_list
    )
    raw_label = heur_label
    confidence: float | None = None
    source = "heuristic"
    classification_scores = heuristic_scores
    ml_probs: dict[str, float] | None = None

    if window_arr is not None and _load_model() is not None and not _live_ml_disabled():
        now = time.monotonic()
        cached = _ml_live_cache.get(zone_id)
        use_cache = cached is not None and (now - cached[0]) < LIVE_ML_INTERVAL_SEC
        try:
            if use_cache:
                _, ml_probs, classification_scores, raw_label, confidence, source = cached
            else:
                ml_probs = _predict_ml_probs_bounded(window_arr)
                if ml_probs is not None:
                    raw_label, confidence, source, classification_scores = _fuse_ml_and_heuristic(
                        ml_probs, heuristic_scores, landmarks, window_list
                    )
                    _ml_live_cache[zone_id] = (
                        now, ml_probs, classification_scores, raw_label, confidence, source
                    )
        except Exception:
            logger.exception("Ошибка ML-inference, fallback на эвристики")

    exercise = _smooth(zone_id, raw_label)
    if confidence is None and source.startswith("heuristic"):
        confidence = classification_scores.get(exercise, classification_scores.get(heur_label))
    return (
        exercise,
        source,
        confidence,
        classification_scores,
        debug,
        body_orientation,
        ml_probs,
        heuristic_scores,
    )


def clear_classifier_state(zone_id: str) -> None:
    _prediction_buffers.pop(zone_id, None)
    _ml_live_cache.pop(zone_id, None)
