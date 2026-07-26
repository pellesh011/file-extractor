# File Extractor

Сервис для загрузки ZIP-архивов из внешнего API, извлечения файлов и сохранения их в S3-совместимое объектное хранилище.

## Архитектура

Проект построен на принципах **Clean Architecture** + **DDD** + **CQRS**:

- **domain** — чистая бизнес-логика, сущности (`File`, `DownloadTask`), value objects, события
- **application** — варианты использования (команды и запросы), порты для внешних систем
- **infrastructure** — реализация портов (SQLAlchemy, S3, HTTP-клиент, ZIP-процессор)
- **presentation** — FastAPI-эндпоинты и Pydantic-схемы
- **worker** — Celery-задачи для асинхронной обработки

## Технологии

| Компонент | Технология |
|---|---|
| Язык | Python 3.12 |
| API | FastAPI |
| Асинхронные задачи | Celery + Redis |
| База данных | PostgreSQL 16 (SQLAlchemy 2.0 + asyncpg) |
| Объектное хранилище | MinIO (S3, aiobotocore) |
| HTTP-клиент | httpx (с retry и rate limiting) |
| Миграции | Alembic |
| Линтеры | Ruff, Black, MyPy |
| Тесты | pytest, testcontainers |
| Фронтенд | React 18 + TypeScript + Vite |
| Контейнеризация | Docker, docker-compose |

## Быстрый старт

```bash
docker compose up --build
```

Поднимаются 6 сервисов:

- **postgres** (5432) — PostgreSQL 16
- **redis** (6379) — Redis 7
- **minio** (9000, console 9001) — S3-хранилище
- **api** (8000) — FastAPI
- **worker** — Celery worker
- **frontend** (5173) — React SPA

> **Важно:** после первого запуска создайте bucket в MinIO. Откройте консоль MinIO (http://localhost:9001), войдите (`minioadmin` / `minioadmin`) и создайте bucket с именем, указанным в `S3_BUCKET_NAME` (по умолчанию `files`).

## API-эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/download/start` | Создать задачу на скачивание |
| `GET` | `/api/download/{task_id}` | Статус задачи |
| `GET` | `/api/files` | Список файлов (с пагинацией) |
| `POST` | `/api/statistics` | Статистика по файлам |
| `POST` | `/api/files/calculate` | Расчёт статистики для выбранных файлов |

## Разработка

### Зависимости

```bash
pip install -e ".[dev]"
```

### Миграции

```bash
alembic upgrade head
```

### Локальный запуск

```bash
# API
uvicorn app.main:app --reload --port 8000

# Worker
celery -A app.core.celery_app worker --loglevel=info --pool=solo

# Фронтенд
cd frontend && npm install && npm run dev
```

### Docker Compose (режим разработки)

`docker-compose.override.yml` подключает hot-reload и debugpy для API и worker.

## Конфигурация

Настройки через переменные окружения (см. `.env.example`):

| Переменная | По умолчанию | Описание |
|---|---|---|
| `DATABASE_URL` | — | PostgreSQL DSN (async) |
| `REDIS_URL` | — | Redis connection string |
| `S3_ENDPOINT_URL` | `http://minio:9000` | S3 endpoint |
| `S3_BUCKET_NAME` | `files` | S3 bucket |
| `EXTERNAL_API_BASE_URL` | — | URL внешнего API |
| `EXTERNAL_API_TIMEOUT_SECONDS` | `30` | Таймаут HTTP-клиента |
| `EXTERNAL_API_MAX_RETRIES` | `5` | Повторные попытки при ошибках |
| `EXTERNAL_API_RATE_LIMIT_RETRIES` | `50` | Повторные попытки при rate limit |
| `LOG_LEVEL` | `INFO` | Уровень логирования |
