# Формат датасетов

В проекте используются два типа датасетов:

- `data/synthetic/*` — синтетические данные для обучения/базовой проверки.
- `data/real/*` — реальные данные, собранные с камеры.

## Структура образца (`jsonl`)

Каждая строка — отдельный JSON-объект:

- `captured_at` — дата и время записи образца (UTC ISO-8601).
- `source` — источник (`synthetic_train`, `synthetic_test`, `camera_real`).
- `label` — класс упражнения (`ResistanceBand`, `PushUps`, `Squats`, `RunInPlace`).
- `sequence` — массив формы `[13, 99]` (13 кадров, 33 точки по `x,y,z`).

## Использование дат

- Дата генерации синтетики фиксируется в `data/synthetic/metadata.json`.
- Дата обучения модели фиксируется в `experiments/train_report.json` (`trained_at`).
- Дата тестирования модели фиксируется в `experiments/eval_report.json` (`evaluated_at`).
