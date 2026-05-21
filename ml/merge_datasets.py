"""
Собирает обучающий датасет:
- базовая синтетика
- live-окна с камеры (jsonl)
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dataset_io import read_jsonl


ROOT = Path(__file__).resolve().parent
SYNTHETIC_TRAIN = ROOT / "data" / "synthetic" / "train_synthetic.jsonl"
LIVE_TRAIN = Path(os.getenv("GYMNET_LIVE_TRAIN_PATH", str(ROOT / "data" / "real" / "live_train.jsonl")))
OUT_PATH = ROOT / "data" / "combined" / "train_combined.jsonl"
META_PATH = ROOT / "data" / "combined" / "metadata.json"


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    synthetic_rows = read_jsonl(SYNTHETIC_TRAIN)
    live_rows = read_jsonl(LIVE_TRAIN)
    combined = synthetic_rows + live_rows
    _write_jsonl(OUT_PATH, combined)

    meta = {
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "synthetic_samples": len(synthetic_rows),
        "live_samples": len(live_rows),
        "combined_samples": len(combined),
        "output_path": str(OUT_PATH),
        "live_train_path": str(LIVE_TRAIN),
    }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Объединенный train-датасет готов")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
