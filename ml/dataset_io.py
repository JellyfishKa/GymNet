from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

CLASSES = ["ResistanceBand", "PushUps", "Squats", "RunInPlace"]
CLASS_TO_ID = {name: idx for idx, name in enumerate(CLASSES)}


@dataclass(slots=True)
class DatasetBundle:
    x: np.ndarray
    y: np.ndarray
    records: list[dict]


def _sample_to_array(sample: dict) -> np.ndarray:
    label = sample.get("label")
    if label not in CLASS_TO_ID:
        raise ValueError(f"Неизвестная метка: {label!r}, ожидается одна из {CLASSES}")

    sequence = np.asarray(sample["sequence"], dtype=np.float32)
    if sequence.ndim != 2 or sequence.shape != (13, 99):
        raise ValueError(f"Ожидается sequence формы (13, 99), получено {sequence.shape}")
    return sequence


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def load_dataset(path: Path) -> DatasetBundle:
    records = read_jsonl(path)
    if not records:
        return DatasetBundle(
            x=np.empty((0, 13, 99), dtype=np.float32),
            y=np.empty((0,), dtype=np.int64),
            records=[],
        )

    x = np.stack([_sample_to_array(item) for item in records]).astype(np.float32)
    y = np.asarray([CLASS_TO_ID[item["label"]] for item in records], dtype=np.int64)
    return DatasetBundle(x=x, y=y, records=records)
