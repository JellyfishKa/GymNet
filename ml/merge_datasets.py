"""
Собирает обучающий датасет:
- базовая синтетика
- live-окна с камеры (jsonl), без дубликатов по hash sequence
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dataset_io import CLASS_TO_ID, read_jsonl

ROOT = Path(__file__).resolve().parent
SYNTHETIC_TRAIN = ROOT / "data" / "synthetic" / "train_synthetic.jsonl"
LIVE_TRAIN = Path(os.getenv("GYMNET_LIVE_TRAIN_PATH", str(ROOT / "data" / "real" / "live_train.jsonl")))
OUT_PATH = ROOT / "data" / "combined" / "train_combined.jsonl"
META_PATH = ROOT / "data" / "combined" / "metadata.json"
# Ограничение live-окон: иначе шумные метки с камеры ломают synthetic macro-F1 при retrain.
LIVE_MERGE_MAX_SAMPLES = int(os.getenv("GYMNET_LIVE_MERGE_MAX_SAMPLES", "80"))
LIVE_MERGE_MAX_RATIO = float(os.getenv("GYMNET_LIVE_MERGE_MAX_RATIO", "0.25"))


def _sequence_hash(row: dict) -> str:
    sequence = row.get("sequence")
    payload = json.dumps(sequence, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _filter_known_labels(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row.get("label") in CLASS_TO_ID]


def _dedup_rows(rows: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for row in rows:
        key = _sequence_hash(row)
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _cap_live_rows(synthetic_count: int, live_rows: list[dict]) -> list[dict]:
    if not live_rows:
        return []
    by_ratio = int(synthetic_count * LIVE_MERGE_MAX_RATIO) if synthetic_count > 0 else LIVE_MERGE_MAX_SAMPLES
    cap = max(1, min(LIVE_MERGE_MAX_SAMPLES, by_ratio))
    if len(live_rows) <= cap:
        return live_rows
    # Берём последние N — обычно свежее и ближе к текущей установке.
    return live_rows[-cap:]


def main() -> None:
    synthetic_rows = _filter_known_labels(read_jsonl(SYNTHETIC_TRAIN))
    live_all = _dedup_rows(_filter_known_labels(read_jsonl(LIVE_TRAIN)))
    live_rows = _cap_live_rows(len(synthetic_rows), live_all)
    combined = _dedup_rows(synthetic_rows + live_rows)
    _write_jsonl(OUT_PATH, combined)

    meta = {
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "synthetic_samples": len(synthetic_rows),
        "live_samples": len(live_rows),
        "live_samples_total": len(live_all),
        "live_merge_cap": LIVE_MERGE_MAX_SAMPLES,
        "combined_samples": len(combined),
        "output_path": str(OUT_PATH.relative_to(ROOT)),
        "live_train_path": str(LIVE_TRAIN),
    }
    META_PATH.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Объединенный train-датасет готов")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
