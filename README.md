# GymNet

Каркас курсового проекта для интеллектуального мониторинга спортзала.

## Текущий статус

- Backend: `FastAPI` + `WebSocket` для обновлений в реальном времени.
- HTTP-эндпоинт ingest: `/api/live/ingest` (`landmarks -> presence/exercise/phase/penalty`).
- Frontend: `React`-дашборд для сценариев `PushUps`, `Squats`, `RunInPlace` (данные только с камеры через ingest).
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
5. (Опционально) Запустить полный ML-конвейер (3 класса, обязательно после смены меток):
   - `docker compose -f infra/docker-compose.yml --profile ml run --rm ml-pipeline`
6. Пересобрать backend после добавления `torch` для live-классификации:
   - `docker compose -f infra/docker-compose.yml up --build -d backend`
7. Остановить окружение:
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

## Тонкая настройка углов и чёткости

Готовый шаблон переменных: [`infra/tuning.env.example`](infra/tuning.env.example).  
Скопируйте нужные строки в `environment` сервиса `backend` в [`infra/docker-compose.yml`](infra/docker-compose.yml) и перезапустите:  
`docker compose -f infra/docker-compose.yml up --build -d backend`

### Как настраивать на практике

1. Откройте дашборд, включите камеру, разверните **«Отладка распознавания»** на карточке зоны.
2. Выполните **одно** упражнение 3–5 повторов и смотрите live-метрики (в т.ч. **Ракурс**: в лицо / боком):
   - **Отжимания**: `torso_vertical_span` обычно **0.08–0.15** (корпус почти горизонтален). Вверху: `elbow_drop` маленький, `arm_extension` большой. Внизу: `elbow_drop` ≥ `GYMNET_PUSHUP_BOTTOM_MIN_ELBOW_DROP`.
   - **Приседания**: `torso_vertical_span` обычно **≥ 0.12** (корпус вертикальнее, в т.ч. боком — по видимой стороне). Вверху: `knee_angle_max` ≥ **168°**. Внизу: `knee_angle_min` ≤ **95°**.
   - **Боком к камере**: система сама переключается на профиль; углы считаются по **видимой** руке/ноге (не усредняют скрытую сторону).
3. Если **путает отжимания с приседаниями** — сначала разведите корпус:
   - уменьшите `GYMNET_PUSHUP_MAX_TORSO_SPAN` (например `0.13`);
   - увеличьте `GYMNET_SQUAT_MIN_TORSO_SPAN` (например `0.14`);
   - увеличьте `GYMNET_CLASSIFY_MIN_MARGIN` (например `0.18`).
4. Если **не засчитывает полное выпрямление** — уменьшите `STANDING_MIN_ANGLE` на 3–5° (например `165`).
5. Если **считает повтор раньше lockout** — увеличьте `STANDING_MIN_ANGLE` или `PUSHUP_STANDING_MIN_ARM_EXTENSION`.

Повтор засчитывается только в фазе `Standing` при выполнении lockout; иначе растёт штраф к «Оценке техники».

### Почему путало отжимания и приседания

Частые причины: камера сбоку/сверху (корпус кажется вертикальным в отжимании), ML-модель обучена на синтетике.  
В коде добавлено: жёсткий tie-break по `torso_vertical_span`, штраф «чужой» позы и при споре ML vs эвристика победа эвристики (`heuristic_override` в UI).

| Упражнение | Ключевые env | Смысл |
|------------|--------------|--------|
| Отжимания | `GYMNET_PUSHUP_MAX_TORSO_SPAN`, `GYMNET_PUSHUP_STANDING_MIN_ANGLE`, `GYMNET_PUSHUP_BOTTOM_MIN_ELBOW_DROP` | Горизонталь корпуса, lockout рук, низ |
| Приседания | `GYMNET_SQUAT_MIN_TORSO_SPAN`, `GYMNET_SQUAT_STANDING_MIN_ANGLE`, `GYMNET_SQUAT_BOTTOM_MAX_ANGLE` | Вертикаль корпуса, lockout ног, глубина |
| Разделение классов | `GYMNET_CLASSIFY_MIN_MARGIN`, `GYMNET_HEURISTIC_OVERRIDE_MARGIN` | Меньше путаницы PushUps/Squats |
| Бег | `GYMNET_RUN_MIN_ANKLE_Y_STD`, `GYMNET_RUN_MIN_STEP_DELTA_Y` | Шаг на месте |

## Live-классификация с камеры

- Дашборд обновляется только через `POST /api/live/ingest` (блок «Управление потоком» удалён).
- Классификация: CNN-ResBiGRU при наличии `best_model.pt`, иначе эвристики по позе.
- После смены числа классов старый четырёхклассовый `best_model.pt` несовместим — перезапустите `ml-pipeline`.

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
