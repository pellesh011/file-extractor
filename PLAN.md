# План разработки File Extractor

## Архитектура

Проект построен на Clean Architecture + DDD + Hexagonal Architecture.

```
Presentation
    ↓
Application (handlers, ports, CQRS)
    ↓
Domain (entities, value objects, events)
    ↑
Infrastructure (DB, S3, HTTP, ZIP, outbox)
```

**Правило зависимостей:** зависимости направлены только внутрь. Domain не знает о FastAPI, SQLAlchemy, S3, HTTP.

---

## Модули и итерации

### Iter 0 — Проектный каркас
**Файлы:** pyproject.toml, docker-compose.yml, Dockerfile, __init__.py

**Проверка:** poetry install, docker compose build

---

### Iter 1 — Core
**Файлы:** config.py, logging.py, exceptions.py
**Тесты:** env, lint

---

### Iter 2 — Domain (изолирован, чистый Python)
**Подмодули:** value_objects, entities, events, repositories (interfaces), exceptions
**Тесты:** чистые unit-тесты, без внешних зависимостей

| Компонент | Файлы | Тестируется |
|---|---|---|
| Value Objects | file_id.py, file_hash.py, storage_key.py, file_size.py, statuses | валидация, создание, ошибки |
| Entities | file.py, download_task.py | все статусные переходы |
| Events | file_uploaded.py, task_completed.py | создание, payload |
| Repository interfaces | file_repository.py, task_repository.py | только контракты |

---

### Iter 3 — Application (зависит только от Domain)
**Подмодули:** ports, commands, queries, handlers, unit_of_work
**Тесты:** mock-based (мокаем ports и репозитории)

| Компонент | Файлы | Тестируется |
|---|---|---|
| Ports | object_storage.py, external_api.py, file_processor.py | интерфейсы |
| Commands | start_download.py, process_files.py | создание команд |
| Queries | get_files.py, get_statistics.py, get_task_status.py | создание запросов |
| Handlers | download_handler.py, statistics_handler.py | бизнес-сценарии |
| UoW | unit_of_work.py | контракт commit/rollback |

---

### Iter 4a — Infrastructure Database
**Файлы:** models.py, session.py, sqlalchemy_uow.py, repositories.py
**Тесты:** testcontainers PostgreSQL

Реализует интерфейсы репозиториев и UoW из Domain/Application через SQLAlchemy 2.0 async.

---

### Iter 4b — Infrastructure S3
**Файл:** s3_storage.py
**Тесты:** testcontainers MinIO

Потоковая multipart загрузка, удаление. Реализует ObjectStorage port.

---

### Iter 4c — Infrastructure ZIP
**Файл:** zip_processor.py
**Тесты:** unit (с реальными zip-архивами)

Потоковое извлечение файлов из ZIP без загрузки всего архива в память.

---

### Iter 4d — Infrastructure External API
**Файл:** catalog_client.py
**Тесты:** мок HTTP-сервера (pytest-httpx)

HTTP клиент с retry, exponential backoff, обработкой 429/403/5xx.

---

### Iter 5 — Presentation
**Файлы:** routes.py, deps.py, schemas/requests.py, schemas/responses.py
**Тесты:** FastAPI TestClient (мокаем handler'ы)

| Endpoint | Описание |
|---|---|
| POST /api/download/start | Создать задачу скачивания |
| GET /api/download/{id} | Статус задачи |
| GET /api/files | Пагинация файлов |
| POST /api/statistics | Статистика по файлам |

---

### Iter 6 — Worker
**Файлы:** celery_app.py, celery_tasks.py, outbox_worker.py
**Тесты:** Celery test worker

Фоновые задачи через Celery. Outbox pattern для доменных событий.

---

### Iter 7 — Assembly
**Файл:** main.py
**Тесты:** сквозной интеграционный тест (testcontainers full stack)

FastAPI приложение, lifespan, Celery worker, Beat.

---

## Граф зависимостей между модулями

```
Iter 0 (каркас)
  └── Iter 1 (Core) ────────────────────────────────┐
       └── Iter 2 (Domain) ─────────────────────────┐│
            └── Iter 3 (Application) ───────────────┐┤│
                 ├── Iter 4a (Infra DB) ◄───────────┘││
                 ├── Iter 4b (Infra S3) ◄────────────┘│
                 ├── Iter 4c (Infra ZIP) ◄────────────┘
                 ├── Iter 4d (Infra HTTP) ◄───────────┘
                 └── Iter 5 (Presentation) ───────────┐
                      └── Iter 6 (Worker) ◄──────────┐│
                           └── Iter 7 (Assembly) ◄───┘│
                                └─────────────────────┘
```

Каждый модуль можно разрабатывать и тестировать изолированно, заменяя зависимости нижележащих слоёв моками.

---

## Статус

- [ ] Iter 0 — Каркас
- [ ] Iter 1 — Core
- [ ] Iter 2 — Domain
- [ ] Iter 3 — Application
- [ ] Iter 4a — Infra DB
- [ ] Iter 4b — Infra S3
- [ ] Iter 4c — Infra ZIP
- [ ] Iter 4d — Infra HTTP
- [ ] Iter 5 — Presentation
- [ ] Iter 6 — Worker
- [ ] Iter 7 — Assembly
