from __future__ import annotations

import asyncio

from loguru import logger

from app.application.commands import ProcessFilesCommand
from app.application.handlers import ProcessFilesHandler
from app.core.celery_app import celery_app
from app.infrastructure.database.repositories import SQLAlchemyTaskRepository
from app.infrastructure.database.session import create_session_factory
from app.infrastructure.database.sqlalchemy_uow import SQLAlchemyUnitOfWork
from app.infrastructure.external_api.catalog_client import CatalogClient
from app.infrastructure.processors.zip_processor import ZipProcessor
from app.infrastructure.storage.s3_storage import S3Storage


@celery_app.task(
    bind=True, acks_late=True, reject_on_worker_lost=True, max_retries=3, default_retry_delay=10
)
def process_files_task(
    self,
    task_id: str,
    candidate_id: str | None = None,
) -> None:
    worker_id = self.request.hostname or "unknown"

    async def _execute() -> None:
        async_session_maker, engine = create_session_factory()
        try:
            async with async_session_maker() as session:
                repo = SQLAlchemyTaskRepository(session)
                task = await repo.claim(task_id, worker_id)
                if not task:
                    logger.info(
                        "task_not_claimed",
                        task_id=task_id,
                        worker_id=worker_id,
                        reason="already claimed or not PENDING",
                    )
                    return

                await session.commit()

                command = ProcessFilesCommand(task_id=task_id, candidate_id=candidate_id)
                uow = SQLAlchemyUnitOfWork(session)
                async with CatalogClient() as api_client:
                    storage = S3Storage()
                    processor = ZipProcessor()

                    handler = ProcessFilesHandler(
                        uow=uow,
                        api_client=api_client,
                        storage=storage,
                        processor=processor,
                    )

                    await handler.execute(command)
        finally:
            await engine.dispose()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(_execute())
