"""
CLI entrypoint kept minimal because evaluation pipeline is notebook-first.
Use ml/notebooks/03_eval_and_ablation.ipynb for full control during coursework.
"""

from pathlib import Path


def main() -> None:
    notebook_path = Path("ml/notebooks/03_eval_and_ablation.ipynb")
    print(f"Evaluation flow is implemented in: {notebook_path}")


if __name__ == "__main__":
    main()
