"""
Сбор реального датасета с веб-камеры.

Сценарий:
1) Пользователь выбирает метку упражнения.
2) Скрипт записывает 13 кадров landmarks через MediaPipe.
3) Сохраняет один образец в ml/data/real/camera_real_test.jsonl
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

CLASSES = ["PushUps", "Squats", "RunInPlace"]
LANDMARK_DIM = 33 * 3
WINDOW = 13
OUT_PATH = Path("ml/data/real/camera_real_test.jsonl")


def _choose_label() -> str:
    print("Выберите класс для записи:")
    for idx, label in enumerate(CLASSES, start=1):
        print(f"{idx}. {label}")
    value = input("Номер класса: ").strip()
    idx = int(value) - 1
    if idx < 0 or idx >= len(CLASSES):
        raise ValueError("Некорректный номер класса")
    return CLASSES[idx]


def _extract_frame_features(results) -> np.ndarray | None:
    if not results.pose_landmarks:
        return None
    features: list[float] = []
    for lm in results.pose_landmarks.landmark:
        features.extend([float(lm.x), float(lm.y), float(lm.z)])
    return np.asarray(features, dtype=np.float32)


def collect_sequence() -> np.ndarray:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Не удалось открыть камеру")

    pose = mp.solutions.pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    frames: list[np.ndarray] = []

    print("Сбор данных начался. Удерживайте упражнение/движение в кадре...")
    try:
        while len(frames) < WINDOW:
            ok, frame = cap.read()
            if not ok:
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)
            feats = _extract_frame_features(results)
            if feats is None or feats.shape[0] != LANDMARK_DIM:
                continue
            frames.append(feats)
            print(f"Кадр {len(frames)}/{WINDOW}")
    finally:
        cap.release()
        pose.close()

    return np.stack(frames).astype(np.float32)


def append_sample(label: str, sequence: np.ndarray) -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": "camera_real",
        "label": label,
        "sequence": sequence.tolist(),
    }
    with OUT_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    label = _choose_label()
    sequence = collect_sequence()
    append_sample(label, sequence)
    print(f"Образец сохранен в {OUT_PATH}")


if __name__ == "__main__":
    main()
