"""
Аблационное исследование архитектур: CNN-only, BiGRU-only, CNN-ResBiGRU.
Обучает все три варианта на combined dataset, оценивает на synthetic test.
Результаты сохраняет в experiments/ablation_report.json.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import accuracy_score, f1_score

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from dataset_io import CLASSES, load_dataset


# ---------------------------------------------------------------------------
# Ablation model variants
# ---------------------------------------------------------------------------

class CnnOnly(nn.Module):
    """Только свёрточный блок без рекуррентной части."""

    def __init__(self, in_features: int = 99, num_classes: int = 3, conv_channels: int = 64) -> None:
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv1d(in_features, conv_channels, kernel_size=3, padding=1),
            nn.BatchNorm1d(conv_channels),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2),
            nn.Dropout(0.2),
        )
        self.head = nn.Sequential(
            nn.Linear(conv_channels, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x.transpose(1, 2)
        x = self.conv(x)
        x = x.mean(dim=2)  # global average pooling по времени
        return self.head(x)


class BiGRUOnly(nn.Module):
    """Только BiGRU без свёрточного блока и residual-связей."""

    def __init__(self, in_features: int = 99, num_classes: int = 3, hidden: int = 64) -> None:
        super().__init__()
        self.bigru = nn.GRU(
            input_size=in_features,
            hidden_size=hidden,
            batch_first=True,
            bidirectional=True,
        )
        self.head = nn.Sequential(
            nn.Linear(hidden * 2, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.bigru(x)
        return self.head(out[:, -1, :])


# ---------------------------------------------------------------------------
# Training / evaluation helpers
# ---------------------------------------------------------------------------

def _train(model: nn.Module, x: np.ndarray, y: np.ndarray, epochs: int = 3) -> list[float]:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()
    loader = DataLoader(
        TensorDataset(torch.from_numpy(x), torch.from_numpy(y)),
        batch_size=32, shuffle=True,
    )
    losses: list[float] = []
    model.train()
    for _ in range(epochs):
        total = 0.0
        for bx, by in loader:
            bx, by = bx.to(device), by.to(device)
            optimizer.zero_grad()
            loss = criterion(model(bx), by)
            loss.backward()
            optimizer.step()
            total += loss.item()
        losses.append(round(total / len(loader), 4))
    return losses


def _evaluate(model: nn.Module, x: np.ndarray, y: np.ndarray) -> dict:
    if len(x) == 0:
        return {"samples": 0, "accuracy": None, "macro_f1": None}
    device = next(model.parameters()).device
    model.eval()
    with torch.no_grad():
        logits = model(torch.from_numpy(x).to(device))
        preds = torch.argmax(logits, dim=1).cpu().numpy()
    return {
        "samples": int(len(y)),
        "accuracy": round(float(accuracy_score(y, preds)), 4),
        "macro_f1": round(float(f1_score(y, preds, average="macro")), 4),
    }


def _count_params(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    train_path = ROOT / "data" / "combined" / "train_combined.jsonl"
    test_path = ROOT / "data" / "synthetic" / "test_synthetic.jsonl"

    if not train_path.exists():
        print("Не найден combined dataset — сначала запустите merge_datasets.py")
        sys.exit(1)
    if not test_path.exists():
        print("Не найден synthetic test dataset")
        sys.exit(1)

    train = load_dataset(train_path)
    test = load_dataset(test_path)
    num_classes = len(CLASSES)

    variants: list[tuple[str, nn.Module]] = [
        ("CNN-only", CnnOnly(in_features=99, num_classes=num_classes)),
        ("BiGRU-only", BiGRUOnly(in_features=99, num_classes=num_classes)),
    ]

    # Import full model for comparison
    from models.cnn_resbigru import CnnResBiGRU
    from checkpoint_io import load_cnn_resbigru
    model_path = ROOT / "experiments" / "best_model.pt"

    results: list[dict] = []

    for name, model in variants:
        print(f"\nОбучение {name}...")
        losses = _train(model, train.x, train.y, epochs=3)
        metrics = _evaluate(model, test.x, test.y)
        results.append({
            "name": name,
            "params": _count_params(model),
            "epoch_losses": losses,
            **metrics,
        })
        print(f"  {name}: accuracy={metrics['accuracy']}, macro_f1={metrics['macro_f1']}, params={_count_params(model)}")

    # Load existing CNN-ResBiGRU
    if model_path.exists():
        full_model = load_cnn_resbigru(model_path)
        metrics = _evaluate(full_model, test.x, test.y)
        results.append({
            "name": "CNN-ResBiGRU (GymNet)",
            "params": _count_params(full_model),
            **metrics,
        })
        print(f"\n  CNN-ResBiGRU: accuracy={metrics['accuracy']}, macro_f1={metrics['macro_f1']}, params={_count_params(full_model)}")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "train_samples": int(len(train.x)),
        "test_samples": int(len(test.x)),
        "classes": CLASSES,
        "results": results,
    }
    out_path = ROOT / "experiments" / "ablation_report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nОтчёт сохранён: {out_path}")


if __name__ == "__main__":
    main()
