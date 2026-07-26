from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "file_extractor",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.celery_tasks", "app.worker.watchdog"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "reclaim-stuck-every-minute": {
            "task": "app.worker.watchdog.reclaim_stuck_tasks",
            "schedule": 60.0,
        },
        "reclaim-blocked-every-minute": {
            "task": "app.worker.watchdog.reclaim_blocked_tasks",
            "schedule": 60.0,
        },
    },
)
