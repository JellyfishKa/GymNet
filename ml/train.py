"""
Быстрый CLI-тренировщик для контейнера ml-train.
Полноценный сценарий обучения остается в ноутбуке 02.
"""

from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from models.cnn_resbigru import CnnResBiGRU


def main() -> None:
    model_path = Path("experiments/best_model.pt")
    model_path.parent.mkdir(parents=True, exist_ok=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CnnResBiGRU(in_features=99, num_classes=4).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()

    x = torch.randn(256, 13, 99)
    y = torch.randint(0, 4, (256,))
    loader = DataLoader(TensorDataset(x, y), batch_size=32, shuffle=True)

    model.train()
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
        print(f"Эпоха {epoch + 1}: потери={total_loss / len(loader):.4f}")

    torch.save(model.state_dict(), model_path)
    print(f"Модель сохранена: {model_path}")


if __name__ == "__main__":
    main()
