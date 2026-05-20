# GymNet

Каркас курсового проекта для интеллектуального мониторинга спортзала.

## Текущий статус

- Backend: `FastAPI` + `WebSocket` для обновлений в реальном времени.
- HTTP-эндпоинт ingest: `/api/live/ingest` (`landmarks -> presence/exercise/phase/penalty`).
- Frontend: `React`-дашборд для сценариев `ResistanceBand`, `PushUps`, `Squats`, `RunInPlace`.
- В интерфейсе есть кнопки `Включить камеру` / `Выключить камеру` для live-потока с браузерной камеры.
- ML: notebook-first пайплайн в `ml/notebooks`.
- Infra: запуск в контейнерах `postgres + backend + frontend` через Docker Compose.
- ML-конвейер автоматически выполняется контейнером `ml-pipeline` при обычном `docker compose up`.
- ML-конвейер автоматически выбирает `GPU`, если доступен, иначе запускается на `CPU`.
- В `docker-compose` для `ml-pipeline` включен `gpus: all`, чтобы CUDA была доступна внутри контейнера.
- Персист завершенных сессий в БД (`zone_sessions`).

## Быстрый старт (Docker)

Самый быстрый вариант одной командой:

- `powershell -ExecutionPolicy Bypass -File scripts/start_stack.ps1`
- без пересборки контейнеров: `powershell -ExecutionPolicy Bypass -File scripts/start_stack.ps1 -NoBuild`
- без запуска ML-конвейера: `powershell -ExecutionPolicy Bypass -File scripts/start_stack.ps1 -NoML`

Скрипт автоматически:
- поднимает `postgres + backend + frontend`,
- проверяет доступность NVIDIA runtime,
- запускает `ml-pipeline-gpu` при наличии GPU, иначе `ml-pipeline`.

1. Собрать и запустить контейнеры:
   - `docker compose -f infra/docker-compose.yml up --build -d`
2. Открыть приложение:
   - `http://localhost:8080`
3. Проверить API:
   - `http://localhost:8000/api/health`
4. Проверить статус ML-конвейера:
   - `docker compose -f infra/docker-compose.yml logs ml-pipeline`
5. Остановить окружение:
   - `docker compose -f infra/docker-compose.yml down`

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

По умолчанию ML-конвейер `generate -> train -> eval` запускается автоматически сервисом `ml-pipeline`.
При наличии доступного CUDA-устройства будет выбран GPU, иначе выполнение продолжится на CPU.

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
  - `docker compose -f infra/docker-compose.yml run --rm ml-pipeline`

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
