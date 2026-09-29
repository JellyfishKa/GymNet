"""
Быстрый CLI-тренировщик для контейнера ml-train.
Полноценный сценарий обучения остается в ноутбуке 02.
"""

import argparse
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from dataset_io import CLASSES, load_dataset
from models.cnn_resbigru import CnnResBiGRU

ROOT = Path(__file__).resolve().parent


def _maybe_seed() -> None:
    seed_raw = os.getenv("GYMNET_TRAIN_SEED")
    if not seed_raw:
        return
    seed = int(seed_raw)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-merge", action="store_true", help="Не вызывать merge_datasets.py повторно")
    args = parser.parse_args()

    _maybe_seed()

    model_path = ROOT / "experiments" / "best_model.pt"
    model_path.parent.mkdir(parents=True, exist_ok=True)
    report_path = ROOT / "experiments" / "train_report.json"

    combined_path = ROOT / "data" / "combined" / "train_combined.jsonl"
    synthetic_path = ROOT / "data" / "synthetic" / "train_synthetic.jsonl"
    if not synthetic_path.exists():
        raise FileNotFoundError(
            "Не найден data/synthetic/train_synthetic.jsonl. "
            "Сначала запустите: python generate_synthetic_dataset.py"
        )

    if not args.skip_merge:
        subprocess.run([sys.executable, str(ROOT / "merge_datasets.py")], cwd=str(ROOT), check=True)
    train_dataset_path = combined_path if combined_path.exists() else synthetic_path

    bundle = load_dataset(train_dataset_path)
    if len(bundle.x) == 0:
        raise ValueError("Train-датасет пустой")

    forced = os.getenv("GYMNET_TRAIN_DEVICE", "").strip().lower()
    if forced == "cpu":
        device = "cpu"
    elif forced == "cuda" and torch.cuda.is_available():
        device = "cuda"
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Выбранное устройство обучения: {device}")
    model = CnnResBiGRU(in_features=99, num_classes=len(CLASSES)).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()

    x_tensor = torch.from_numpy(bundle.x)
    y_tensor = torch.from_numpy(bundle.y)
    loader = DataLoader(TensorDataset(x_tensor, y_tensor), batch_size=32, shuffle=True)

    trained_at = datetime.now(timezone.utc).isoformat()
    model.train()
    epoch_losses: list[float] = []
    for epoch in range(3):
        total_loss = 0.0
        for batch_x, batch_y in loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        avg_loss = total_loss / len(loader)
        epoch_losses.append(avg_loss)
        print(f"Эпоха {epoch + 1}: потери={avg_loss:.4f}")

    torch.save(
        {"model_state": model.state_dict(), "num_classes": len(CLASSES), "classes": CLASSES},
        model_path,
    )
    print(f"Модель сохранена: {model_path}")

    report = {
        "trained_at": trained_at,
        "train_dataset": str(train_dataset_path.relative_to(ROOT)),
        "synthetic_dataset": str(synthetic_path.relative_to(ROOT)),
        "train_samples": int(len(bundle.x)),
        "classes": CLASSES,
        "epoch_losses": epoch_losses,
        "model_path": str(model_path.relative_to(ROOT)),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Отчет обучения сохранен: {report_path}")


if __name__ == "__main__":
    main()
