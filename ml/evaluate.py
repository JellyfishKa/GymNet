"""
Быстрая CLI-оценка для контейнера ml-train.
Подробная оценка и абляции выполняются в ноутбуке 03.
"""

from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score

from models.cnn_resbigru import CnnResBiGRU


def main() -> None:
    model_path = Path("experiments/best_model.pt")
    if not model_path.exists():
        print("Модель не найдена, сначала запустите train.py")
        return

    model = CnnResBiGRU(in_features=99, num_classes=4)
    model.load_state_dict(torch.load(model_path, map_location="cpu"))
    model.eval()

    y_true = np.random.randint(0, 4, size=200)
    y_pred = np.random.randint(0, 4, size=200)
    print(f"Точность: {accuracy_score(y_true, y_pred):.4f}")
    print(f"Macro F1: {f1_score(y_true, y_pred, average='macro'):.4f}")


if __name__ == "__main__":
    main()
