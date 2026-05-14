"""
Единый ML-конвейер:
1) генерация синтетического датасета
2) обучение модели
3) оценка (синтетика + реальные данные, если доступны)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_step(title: str, command: list[str]) -> None:
    print(f"\n=== {title} ===")
    print("Команда:", " ".join(command))
    subprocess.run(command, check=True)


def main() -> None:
    root = Path(__file__).resolve().parent
    py = sys.executable

    run_step("Генерация синтетического датасета", [py, str(root / "generate_synthetic_dataset.py")])
    run_step("Обучение модели", [py, str(root / "train.py")])
    run_step("Оценка модели", [py, str(root / "evaluate.py")])

    print("\nML-конвейер завершен успешно.")
    print("Артефакты:")
    print("- ml/data/synthetic/*")
    print("- ml/experiments/train_report.json")
    print("- ml/experiments/eval_report.json")


if __name__ == "__main__":
    main()
