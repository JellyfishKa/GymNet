"""
CLI entrypoint kept minimal because training pipeline is notebook-first.
Use ml/notebooks/02_train_cnn_resbigru.ipynb for full control during coursework.
"""

from pathlib import Path


def main() -> None:
    notebook_path = Path("ml/notebooks/02_train_cnn_resbigru.ipynb")
    print(f"Training flow is implemented in: {notebook_path}")


if __name__ == "__main__":
    main()
