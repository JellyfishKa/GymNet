# GymNet

Каркас курсового проекта для интеллектуального мониторинга спортзала.

## Текущий статус

- Backend: `FastAPI` + `WebSocket` для обновлений в реальном времени.
- HTTP-эндпоинт ingest: `/api/live/ingest` (`landmarks -> presence/exercise/phase/penalty`).
- Frontend: `React`-дашборд для сценариев `ResistanceBand`, `PushUps`, `Squats`, `RunInPlace`.
- В интерфейсе есть кнопки `Включить камеру` / `Выключить камеру` для live-потока с браузерной камеры.
- ML: notebook-first пайплайн в `ml/notebooks`.
- Infra: запуск в контейнерах `postgres + backend + frontend + ml-autotrain` через Docker Compose.
- ML-конвейер `generate -> train -> eval` доступен через профиль `ml` (сервис `ml-pipeline`).
- Персист завершенных сессий в БД (`zone_sessions`).

## Быстрый старт (Docker)

Самый быстрый вариант одной командой:

- `powershell -ExecutionPolicy Bypass -File scripts/start_stack.ps1`
- без пересборки контейнеров: `powershell -ExecutionPolicy Bypass -File scripts/start_stack.ps1 -NoBuild`
- без запуска ML-конвейера: `powershell -ExecutionPolicy Bypass -File scripts/start_stack.ps1 -NoML`

Скрипт автоматически:
- поднимает `postgres + backend + frontend + ml-autotrain`,
- при `-NoML` не запускает одноразовый ML-pipeline,
- иначе выполняет `ml-pipeline` через профиль `ml`.

1. Собрать и запустить контейнеры:
   - `docker compose -f infra/docker-compose.yml up --build -d`
2. Открыть приложение:
   - `http://localhost:8080`
3. Проверить API:
   - `http://localhost:8000/api/health`
4. Проверить авто-retrain (фоновый сервис):
   - `docker compose -f infra/docker-compose.yml logs ml-autotrain`
   - статус в UI: блок `ML: автообучение` на дашборде
   - API: `http://localhost:8000/api/ml/status`
5. (Опционально) Запустить полный ML-конвейер:
   - `docker compose -f infra/docker-compose.yml --profile ml run --rm ml-pipeline`
6. Остановить окружение:
   - `docker compose -f infra/docker-compose.yml down`

## Авто-retrain во время работы камеры

Поток данных:
1. Камера отправляет landmarks в `/api/live/ingest`.
2. Backend накапливает окна `[13, 99]` и пишет их в `live_train.jsonl`.
3. При завершении сессии сохраняются метрики в `live_sessions.jsonl` и обновляется online-профиль прогноза.
4. Сервис `ml-autotrain` по порогу новых live-образцов запускает `merge_datasets -> train -> evaluate`.
5. При успехе модель и отчет публикуются в shared volume; при просадке `macro_f1` выполняется safe-rollback.

Пороги (env):
- `GYMNET_AUTORETRAIN_MIN_NEW_TRAIN_SAMPLES` (по умолчанию `8`)
- `GYMNET_AUTORETRAIN_MIN_NEW_SESSIONS` (по умолчанию `10`)
- `GYMNET_AUTORETRAIN_COOLDOWN_SECONDS` (по умолчанию `900`)

## Локальный запуск без Docker

1. Поднять только Postgres:
   - `docker compose -f infra/docker-compose.yml up -d postgres`
2. Запустить backend:
   - `cd backend`
   - `pip install -r requirements.txt`
   - `uvicorn app.main:app --reload --port 8000`
3. Запустить frontend:
   - `cd frontend`
   - `npm install`
   - `npm run dev`
4. (Опционально) Подключить веб-камеру в live-поток:
   - `pip install -r backend/requirements.txt`
   - `python scripts/camera_ws_client.py`

## ML в Docker

Для ручных сценариев и ноутбука используйте профиль `ml`:

- Сгенерировать синтетический датасет:
  - `docker compose -f infra/docker-compose.yml --profile ml run --rm ml-generate`
- Поднять ноутбук Jupyter:
  - `docker compose -f infra/docker-compose.yml --profile ml up --build -d ml-notebook`
- Запустить быструю тренировку в контейнере:
  - `docker compose -f infra/docker-compose.yml --profile ml run --rm ml-train`
- Запустить быструю оценку:
  - `docker compose -f infra/docker-compose.yml --profile ml run --rm ml-eval`
- Повторно запустить полный конвейер одной командой:
  - `docker compose -f infra/docker-compose.yml --profile ml run --rm ml-pipeline`

## Датасеты и даты экспериментов

- Синтетический train/test датасет хранится в `ml/data/synthetic/`.
- Реальный тестовый датасет с камеры хранится в `ml/data/real/camera_real_test.jsonl`.
- Сбор реальных данных:
  - `python scripts/collect_camera_dataset.py`
- Дата обучения на синтетике записывается в:
  - `ml/experiments/train_report.json` (`trained_at`)
- Дата тестирования (синтетика + реальные данные) записывается в:
  - `ml/experiments/eval_report.json` (`evaluated_at`)

## Диагностика камеры

- Проверить работу камеры через OpenCV:
  - `python scripts/check_opencv_camera.py`
- Если в интерфейсе камера включается и сразу отключается:
  - проверьте разрешение камеры для браузера,
  - закройте приложения, которые могут удерживать камеру,
  - повторно проверьте OpenCV-диагностику командой выше.

## ML ноутбуки

- `ml/notebooks/01_data_prep.ipynb`
- `ml/notebooks/02_train_cnn_resbigru.ipynb`
- `ml/notebooks/03_eval_and_ablation.ipynb`
