from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from dataset_io import CLASSES

RNG = np.random.default_rng(42)


def _base_pattern(label: str) -> np.ndarray:
    t = np.linspace(0.0, 1.0, 13, dtype=np.float32)
    pattern = np.zeros((13, 99), dtype=np.float32)
    if label == "ResistanceBand":
        pattern[:, :] = 0.4 + 0.2 * np.sin(2 * np.pi * t)[:, None]
    elif label == "PushUps":
        pattern[:, :] = 0.5 + 0.25 * np.sin(4 * np.pi * t)[:, None]
    elif label == "Squats":
        pattern[:, :] = 0.55 + 0.3 * np.abs(np.sin(2 * np.pi * t))[:, None]
    elif label == "RunInPlace":
        pattern[:, :] = 0.45 + 0.2 * np.sin(8 * np.pi * t)[:, None]
    return np.clip(pattern, 0.0, 1.0)


def _make_sample(label: str, source: str) -> dict:
    base = _base_pattern(label)
    noise = RNG.normal(0.0, 0.03, size=(13, 99)).astype(np.float32)
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
