# File Extractor

Сервис для загрузки ZIP-архивов из внешнего API, извлечения файлов, вычисления статистики по цифрам в их названиях и сохранения в S3-совместимое объектное хранилище (MinIO).

## Содержание

- [Архитектура](#архитектура)
- [Технологии](#технологии)
- [State Machine задач](#state-machine-задач)
- [Быстрый старт](#быстрый-старт)
- [Конфигурация](#конфигурация)
- [API](#api)
- [Разработка](#разработка)
- [Тестирование](#тестирование)
- [Миграции БД](#миграции-бд)

---

## Архитектура

```
              PostgreSQL (state machine)
                  |
        +---------+---------+
        |                   |
   API service        Worker service (Celery)
   (FastAPI)               |
                      Redis (queue)
                           |
              +------------+------------+
              |            |            |
          worker-1     worker-2     worker-3
              |
         External API (ZIP files)
              |
           MinIO (S3)
              |
         ZIP → файлы

              ^
              |
          Watchdog
        (Celery Beat)
     reclaim_stuck_tasks()
     reclaim_blocked_tasks()
```

Проект построен на принципах **Clean Architecture** + **DDD** + **CQRS**:

| Слой | Назначение |
|---|---|
| `app/domain/` | Чистая бизнес-логика: сущности (`File`, `DownloadTask`), value objects, события, интерфейсы репозиториев |
| `app/application/` | Варианты использования (команды/запросы), хендлеры, порты для внешних систем, Unit of Work |
| `app/infrastructure/` | Реализация портов: SQLAlchemy (PostgreSQL), S3 (aiobotocore), HTTP-клиент (httpx с retry+rate limit), ZIP-процессор |
| `app/presentation/` | FastAPI-эндпоинты, Pydantic-схемы запросов/ответов, DI |
| `app/worker/` | Celery-задачи, Watchdog (reclaim stuck/blocked задач) |

---

## Технологии

| Компонент | Технология |
|---|---|
| Язык | Python 3.12 |
| API | FastAPI + Uvicorn |
| Асинхронные задачи | Celery 5 + Redis (broker/backend) |
| База данных | PostgreSQL 16, SQLAlchemy 2.0 (async), asyncpg |
| Миграции | Alembic |
| Объектное хранилище | MinIO (S3-совместимое), aiobotocore |
| HTTP-клиент | httpx (adaptive rate limiter, retry с экспоненциальной задержкой) |
| Линтеры/форматтеры | Ruff, Black, MyPy (strict) |
| Тесты | pytest, pytest-asyncio, testcontainers (PostgreSQL, Redis, MinIO) |
| Фронтенд | React 18 + TypeScript + Vite |
| Контейнеризация | Docker, docker-compose |

---

## State Machine задач

Celery — транспорт выполнения. **PostgreSQL — источник истины о состоянии задачи.**

### Статусы

```
               BLOCKED (API заблокировала запрос)
              /      \
PENDING ──→ RUNNING ──→ SUCCESS
  │            │
  └─────→ FAILED
```

| Статус | Описание |
|---|---|
| `PENDING` | Задача создана, ожидает воркера |
| `RUNNING` | Воркер захватил задачу, выполняется |
| `SUCCESS` | Все файлы скачаны, обработаны, сохранены |
| `FAILED` | Неустранимая ошибка |
| `BLOCKED` | Внешнее API вернуло 403 с `Retry-After > 60s`. Задача приостановлена |

### Атомарный claim

Воркер не получает задачу «из воздуха» — он делает атомарный `UPDATE ... RETURNING`:

```sql
UPDATE download_tasks
SET status='RUNNING', worker_id='worker-1', started_at=now(),
    last_heartbeat=now(), attempts=attempts+1
WHERE id=? AND status='PENDING'
RETURNING *
```

Только один воркер получит строку. Остальные увидят `None`.

### Heartbeat

Во время скачивания воркер обновляет `last_heartbeat` каждые 30 итераций цикла. Если воркер упал — heartbeat останавливается.

### Watchdog (Celery Beat)

Каждую минуту watchdog запускает две задачи:

1. **`reclaim_stuck_tasks`** — находит `RUNNING` задачи с `last_heartbeat` старше 5 минут и возвращает их в `PENDING`
2. **`reclaim_blocked_tasks`** — находит `BLOCKED` задачи с истекшим `blocked_until` и возвращает их в `PENDING`

После reclaim любой свободный воркер может забрать задачу через `claim`.

### BLOCKED-статус

При получении 403 с `Retry-After`:
- **≤ 60 секунд** — воркер ждёт на месте
- **> 60 секунд** — воркер переводит задачу в `BLOCKED`, сохраняет `blocked_until = now() + retry_after` и завершается. Watchdog вернёт её в `PENDING` после истечения таймера

### Идемпотентность

Таблица `downloaded_files` хранит `(task_id, file_name)` с `UNIQUE`-ограничением. При повторном запуске уже скачанные файлы пропускаются:

```sql
INSERT INTO downloaded_files (task_id, file_name, hash)
VALUES (?, ?, ?)
ON CONFLICT (task_id, file_name) DO NOTHING;
```

---

## Быстрый старт

### Через Docker Compose

```bash
# 1. Скопировать пример конфигурации
cp .env.example .env

# 2. Запустить все сервисы
docker compose up --build

# 3. Применить миграции в контейнере
alembic upgrade head
```

Поднимаются 7 сервисов:

| Сервис | Порт | Назначение |
|---|---|---|
| `postgres` | 5432 | PostgreSQL 16 |
| `redis` | 6379 | Redis (Celery broker/backend) |
| `minio` | 9000, 9001 (console) | S3-хранилище |
| `api` | 8000 | FastAPI |
| `worker` | — | Celery worker (--pool=solo) |
| `beat` | — | Celery beat (watchdog) |
| `frontend` | 5173 | React SPA |

> **Важно:** после первого запуска создайте bucket в MinIO. Откройте консоль http://localhost:9001, войдите (`minioadmin` / `minioadmin123`) и создайте bucket с именем из `S3_BUCKET_NAME` (по умолчанию `files`).

### Без Docker (локальная разработка)

Потребуются запущенные PostgreSQL, Redis и MinIO.

```bash
# 1. Установить зависимости
pip install -e ".[dev]"

# 2. Настроить .env (см. .env.example)
cp .env.example .env
# отредактировать DATABASE_URL, REDIS_URL, S3_*

# 3. Применить миграции
alembic upgrade head

# 4. Запустить API
uvicorn app.main:app --reload --port 8000

# 5. В другом терминале — Worker
celery -A app.core.celery_app worker --loglevel=info --pool=solo

# 6. В третьем — Beat (watchdog)
celery -A app.core.celery_app beat --loglevel=info

# 7. Фронтенд (опционально)
cd frontend && npm install && npm run dev
```

---

## Конфигурация

Все настройки задаются через переменные окружения. Файл `.env` автоматически загружается `docker-compose.yml` (через `env_file: .env`) и приложением (через `pydantic-settings`).

### Основные

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `DATABASE_URL` | да | — | PostgreSQL DSN (async). Пример: `postgresql+asyncpg://app:secret@localhost:5432/file_extractor` |
| `REDIS_URL` | да | — | Redis connection string. Пример: `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | да | — | Celery broker (обычно тот же Redis). Пример: `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | да | — | Celery result backend (обычно тот же Redis). Пример: `redis://localhost:6379/0` |

### S3 (MinIO)

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `S3_ENDPOINT_URL` | нет | `http://localhost:9000` | S3 endpoint |
| `S3_ACCESS_KEY_ID` | нет | `minioadmin` | Access key |
| `S3_SECRET_ACCESS_KEY` | нет | `minioadmin123` | Secret key |
| `S3_BUCKET_NAME` | нет | `files` | Bucket для хранения файлов |

### Внешнее API

| Переменная | Обязательная | По умолчанию | Описание |
|---|---|---|---|
| `EXTERNAL_API_BASE_URL` | да | — | Базовый URL внешнего API для скачивания ZIP |
| `EXTERNAL_API_TIMEOUT_SECONDS` | нет | `30` | Таймаут HTTP-запроса |
| `EXTERNAL_API_MAX_RETRIES` | нет | `5` | Максимум повторных попыток при ошибках |
| `EXTERNAL_API_RATE_LIMIT_RETRIES` | нет | `50` | Максимум повторных попыток при rate limit (429) |

### Логирование

| Переменная | По умолчанию | Описание |
|---|---|---|
| `LOG_LEVEL` | `INFO` | Уровень: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | `structured` | Формат: `structured` (JSON) или `console` (читаемый текст) |

### Прочее

| Переменная | Описание |
|---|---|
| `CANDIDATE_ID` | Идентификатор кандидата, передаётся в заголовке `X-Candidate-Id` внешнему API |

---

## API

### `POST /api/download/start`

Создаёт задачу на скачивание файлов. Статус — `PENDING`.

**Request:**
```json
{
  "candidate_id": "string (опционально)"
}
```

**Response (201):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### `GET /api/download/{task_id}`

Статус задачи.

**Response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "RUNNING",
  "received_files": 15,
  "processed_files": 9,
  "error": null,
  "started_at": "2026-07-26T12:00:00Z",
  "finished_at": null,
  "worker_id": "celery@worker-1",
  "attempts": 1,
  "blocked_until": null,
  "block_reason": null
}
```

### `GET /api/tasks`

Список последних задач (10 шт).

### `GET /api/files?page=1&per_page=20&status=UPLOADED`

Список файлов с пагинацией и фильтром по статусу.

### `POST /api/statistics`

Агрегированная статистика по всем файлам.

### `POST /api/files/calculate`

Расчёт статистики по цифрам в названиях файлов.

**Request:**
```json
{
  "file_ids": ["uuid-1", "uuid-2"]
}
```

---

## Разработка

### Форматирование и линтинг

```bash
ruff check app/
ruff format app/
mypy app/
```

### pre-commit

```bash
pre-commit install
```

### Docker Compose (режим разработки)

`docker-compose.override.yml` подключает hot-reload и debugpy для API и worker.

```bash
docker compose -f docker-compose.yml -f docker-compose.override.yml up --build
```

---

## Тестирование

```bash
# Все тесты (поднимает PostgreSQL, Redis и MinIO в testcontainers)
pytest

# С coverage
pytest --cov=app

# Выборочно
pytest tests/domain/
pytest tests/application/
pytest tests/integration/
```

---

## Миграции БД

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "description"

# Применить
alembic upgrade head

# Откатиться на одну
alembic downgrade -1

# Просмотр истории
alembic history
```
