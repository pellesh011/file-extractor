from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from celery import shared_task
from loguru import logger
from sqlalchemy import select

from app.application.commands import ProcessFilesCommand
from app.application.handlers import ProcessFilesHandler
from app.core.celery_app import celery_app
from app.core.config import settings
from app.infrastructure.database.models import OutboxEventModel
from app.infrastructure.database.session import session_factory
from app.infrastructure.database.sqlalchemy_uow import SQLAlchemyUnitOfWork
from app.infrastructure.external_api.catalog_client import CatalogClient
from app.infrastructure.processors.zip_processor import ZipProcessor
from app.infrastructure.storage.s3_storage import S3Storage


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def process_files_task(
    self,
    task_id: str,
    candidate_id: str | None = None,
) -> None:
    command = ProcessFilesCommand(task_id=task_id, candidate_id=candidate_id)
    session = session_factory()
    uow = SQLAlchemyUnitOfWork(session)
    api_client = CatalogClient()
    storage = S3Storage()
    processor = ZipProcessor()

    handler = ProcessFilesHandler(
        uow=uow,
        api_client=api_client,
        storage=storage,
        processor=processor,
    )

    asyncio.run(handler.execute(command))


@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs) -> None:
    sender.add_periodic_task(
        settings.outbox_poll_interval_seconds,
        dispatch_outbox_events.s(),
        name="dispatch-outbox-events",
    )


@shared_task
def dispatch_outbox_events() -> None:
    async def _dispatch() -> None:
        session = session_factory()
        async with session:
            result = await session.execute(
                select(OutboxEventModel)
                .where(OutboxEventModel.processed_at.is_(None))
                .limit(settings.outbox_max_events_per_batch)
            )
            events = result.scalars().all()

            for event in events:
                try:
                    payload = json.loads(event.payload)
                    logger.info(
                        "dispatching_outbox_event",
                        event_type=event.event_type,
                        event_id=event.id,
                        payload=payload,
                    )
                except Exception as e:
                    logger.error(
                        "outbox_dispatch_failed",
                        event_id=event.id,
                        event_type=event.event_type,
                        error=str(e),
                    )
                finally:
                    event.processed_at = datetime.now(UTC)

            await session.commit()

    asyncio.run(_dispatch())
