"""Загрузка чекпоинта best_model.pt (обёртка train.py или сырой state_dict)."""

from __future__ import annotations

from pathlib import Path

import torch

from dataset_io import CLASSES
from models.cnn_resbigru import CnnResBiGRU


def load_cnn_resbigru(model_path: Path, *, in_features: int = 99) -> CnnResBiGRU:
    if not model_path.exists():
        raise FileNotFoundError(f"Модель не найдена: {model_path}")

    checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
    if isinstance(checkpoint, dict) and "model_state" in checkpoint:
        state = checkpoint["model_state"]
        num_classes = int(checkpoint.get("num_classes", len(CLASSES)))
    else:
        state = checkpoint
        num_classes = len(CLASSES)

    model = CnnResBiGRU(in_features=in_features, num_classes=num_classes)
    model.load_state_dict(state)
    model.eval()
    return model
