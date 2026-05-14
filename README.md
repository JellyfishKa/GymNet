# GymNet

Каркас курсового проекта для интеллектуального мониторинга спортзала.

## Текущий статус

- Backend: `FastAPI` + `WebSocket` для обновлений в реальном времени.
- HTTP-эндпоинт ingest: `/api/live/ingest` (`landmarks -> presence/exercise/phase/penalty`).
- Frontend: `React`-дашборд для сценариев `ResistanceBand`, `PushUps`, `Squats`, `RunInPlace`.
- ML: notebook-first пайплайн в `ml/notebooks`.
- Infra: локальный `PostgreSQL` через Docker Compose.
- Персист завершенных сессий в БД (`zone_sessions`).

## Быстрый старт

1. Поднять Postgres:
   - `docker compose -f infra/docker-compose.yml up -d`
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

## ML ноутбуки

- `ml/notebooks/01_data_prep.ipynb`
- `ml/notebooks/02_train_cnn_resbigru.ipynb`
- `ml/notebooks/03_eval_and_ablation.ipynb`
