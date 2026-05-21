from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from dataset_io import CLASSES

RNG = np.random.default_rng(42)
WINDOW = 13
FEATURE_DIM = 99

# Индексы MediaPipe в плоском векторе [x,y,z] * 33
_IDX = {
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
}


def _set_xy(frame: np.ndarray, name: str, x: float, y: float) -> None:
    i = _IDX[name] * 3
    frame[i] = x
    frame[i + 1] = y


def _base_pattern(label: str) -> np.ndarray:
    """Анатомически различимые паттерны под 3 класса (не одинаковый sin на все 99)."""
    t = np.linspace(0.0, 1.0, WINDOW, dtype=np.float32)
    pattern = np.full((WINDOW, FEATURE_DIM), 0.5, dtype=np.float32)

    if label == "PushUps":
        for k, phase in enumerate(t):
            elbow_y = 0.52 + 0.12 * np.sin(4 * np.pi * phase)
            wrist_y = elbow_y + 0.06
            _set_xy(pattern[k], "left_shoulder", 0.35, 0.50)
            _set_xy(pattern[k], "right_shoulder", 0.65, 0.50)
            _set_xy(pattern[k], "left_hip", 0.40, 0.54)
            _set_xy(pattern[k], "right_hip", 0.60, 0.54)
            _set_xy(pattern[k], "left_elbow", 0.36, elbow_y)
            _set_xy(pattern[k], "right_elbow", 0.64, elbow_y)
            _set_xy(pattern[k], "left_wrist", 0.37, wrist_y)
            _set_xy(pattern[k], "right_wrist", 0.63, wrist_y)
            _set_xy(pattern[k], "left_knee", 0.45, 0.68)
            _set_xy(pattern[k], "right_knee", 0.55, 0.68)

    elif label == "Squats":
        for k, phase in enumerate(t):
            knee_y = 0.50 + 0.14 * (1.0 - np.cos(2 * np.pi * phase)) * 0.5
            _set_xy(pattern[k], "left_shoulder", 0.50, 0.30)
            _set_xy(pattern[k], "right_shoulder", 0.50, 0.30)
            _set_xy(pattern[k], "left_hip", 0.50, 0.44)
            _set_xy(pattern[k], "right_hip", 0.50, 0.44)
            _set_xy(pattern[k], "left_knee", 0.56, knee_y)
            _set_xy(pattern[k], "right_knee", 0.44, knee_y)
            _set_xy(pattern[k], "left_ankle", 0.50, 0.72)
            _set_xy(pattern[k], "right_ankle", 0.50, 0.72)
            _set_xy(pattern[k], "left_elbow", 0.48, 0.38)
            _set_xy(pattern[k], "right_elbow", 0.52, 0.38)

    elif label == "RunInPlace":
        for k, phase in enumerate(t):
            step = np.sin(8 * np.pi * phase)
            left_ankle_y = 0.72 + 0.05 * step
            right_ankle_y = 0.72 - 0.05 * step
            _set_xy(pattern[k], "left_shoulder", 0.48, 0.28)
            _set_xy(pattern[k], "right_shoulder", 0.52, 0.28)
            _set_xy(pattern[k], "left_hip", 0.48, 0.42)
            _set_xy(pattern[k], "right_hip", 0.52, 0.42)
            _set_xy(pattern[k], "left_knee", 0.50, 0.56)
            _set_xy(pattern[k], "right_knee", 0.50, 0.56)
            _set_xy(pattern[k], "left_ankle", 0.48, left_ankle_y)
            _set_xy(pattern[k], "right_ankle", 0.52, right_ankle_y)
            _set_xy(pattern[k], "left_elbow", 0.47, 0.36)
            _set_xy(pattern[k], "right_elbow", 0.53, 0.36)

    return np.clip(pattern, 0.0, 1.0)


def _make_sample(label: str, source: str) -> dict:
    base = _base_pattern(label)
    noise = RNG.normal(0.0, 0.02, size=(WINDOW, FEATURE_DIM)).astype(np.float32)
    sequence = np.clip(base + noise, 0.0, 1.0)
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "label": label,
        "sequence": sequence.tolist(),
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    now = datetime.now(timezone.utc).isoformat()
    train_rows: list[dict] = []
    test_rows: list[dict] = []

    for label in CLASSES:
        for _ in range(180):
            train_rows.append(_make_sample(label, source="synthetic_train"))
        for _ in range(40):
            test_rows.append(_make_sample(label, source="synthetic_test"))

    out_dir = Path("data/synthetic")
    train_path = out_dir / "train_synthetic.jsonl"
    test_path = out_dir / "test_synthetic.jsonl"
    meta_path = out_dir / "metadata.json"

    _write_jsonl(train_path, train_rows)
    _write_jsonl(test_path, test_rows)
    meta_path.write_text(
        json.dumps(
            {
                "generated_at": now,
                "train_samples": len(train_rows),
                "test_samples": len(test_rows),
                "classes": CLASSES,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Синтетический датасет создан")
    print(f"Дата генерации: {now}")
    print(f"Train: {train_path} ({len(train_rows)} образцов)")
    print(f"Test:  {test_path} ({len(test_rows)} образцов)")


if __name__ == "__main__":
    main()
