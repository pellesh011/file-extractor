from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

from loguru import logger

from app.application.commands import ProcessFilesCommand, StartDownloadCommand
from app.application.ports import ExternalAPIClient, FileProcessor, ObjectStorage
from app.application.unit_of_work import UnitOfWork
from app.core.celery_app import celery_app
from app.domain.entities.download_task import DownloadTask
from app.domain.entities.file import File
from app.domain.value_objects import FileHash, FileId, FileSize, StorageKey
from app.infrastructure.external_api.exceptions import ExternalAPIBlockedError


class StartDownloadHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: StartDownloadCommand) -> str:
        task_id = str(uuid4())

        task = DownloadTask(
            task_id=task_id,
            candidate_id=command.candidate_id or "",
        )

        async with self._uow:
            await self._uow.task_repo.add(task)
            await self._uow.commit()

        logger.info(
            "download_task_created",
            task_id=task_id,
            candidate_id=command.candidate_id,
            status=task.status.name,
        )

        celery_app.send_task(
            "app.worker.celery_tasks.process_files_task",
            args=[task_id, command.candidate_id],
        )

        return task_id


class ProcessFilesHandler:
    HEARTBEAT_INTERVAL = 30
    BLOCK_THRESHOLD_SECONDS = 60

    def __init__(
        self,
        uow: UnitOfWork,
        api_client: ExternalAPIClient,
        storage: ObjectStorage,
        processor: FileProcessor,
    ) -> None:
        self._uow = uow
        self._api = api_client
        self._storage = storage
        self._processor = processor

    async def execute(self, command: ProcessFilesCommand) -> None:
        task = await self._get_task(command.task_id)
        if not task:
            logger.error("task_not_found", task_id=command.task_id)
            return

        try:
            await self._run(task, command)
        except Exception as e:
            logger.exception("process_files_failed", task_id=task.id, error=str(e))
            await self._fail_task(task, str(e))

    async def _get_task(self, task_id: str) -> DownloadTask | None:
        async with self._uow:
            return await self._uow.task_repo.get_by_id(task_id)

    async def _run(self, task: DownloadTask, command: ProcessFilesCommand) -> None:
        pending: list[str] = []
        heartbeat_counter = 0

        while True:
            if len(pending) < 3:
                names_result = await self._api.get_file_names(command.candidate_id)
                if not names_result.file_names:
                    if not pending:
                        break
                else:
                    pending.extend(names_result.file_names)
                    task.increase_received(len(names_result.file_names))
                    async with self._uow:
                        await self._uow.task_repo.update(task)
                        await self._uow.commit()

            batch = pending[:3]
            pending = pending[3:]

            try:
                zip_stream = self._api.download_files_stream(batch)
            except ExternalAPIBlockedError as block_err:
                if await self._handle_block(task, block_err):
                    return
                raise
            except Exception:
                raise

            batch_file_entities: list[File] = []
            async for extracted in self._processor.extract_stream(zip_stream):
                await self._maybe_heartbeat(task, heartbeat_counter)
                heartbeat_counter += 1

                if await self._uow.task_repo.downloaded_file_exists(task.id, extracted.filename):
                    logger.info(
                        "file_already_downloaded_skipping",
                        task_id=task.id,
                        filename=extracted.filename,
                    )
                    continue

                file_hash = FileHash.compute(extracted.content)
                storage_key = StorageKey(f"files/{extracted.filename}")

                async def content_stream(data: bytes) -> AsyncIterator[bytes]:
                    yield data

                await self._storage.upload_stream(
                    content_stream(extracted.content),
                    key=storage_key.value,
                    length=extracted.size,
                )

                file_entity = File(
                    file_id=FileId(),
                    filename=extracted.filename,
                    size=FileSize(extracted.size),
                    hash=file_hash,
                )
                file_entity.start_upload()
                file_entity.complete_upload(storage_key, file_hash)

                async with self._uow:
                    await self._uow.file_repo.add(file_entity)
                    await self._uow.task_repo.record_downloaded_file(
                        task.id, extracted.filename, file_hash
                    )
                    await self._uow.commit()

                batch_file_entities.append(file_entity)

                logger.info(
                    "file_uploaded",
                    file_id=str(file_entity.id),
                    filename=extracted.filename,
                    size=extracted.size,
                )

            try:
                await self._api.mark_downloaded(batch, command.candidate_id)
            except ExternalAPIBlockedError as block_err:
                await self._cleanup_batch_files(batch_file_entities)
                if await self._handle_block(task, block_err):
                    return
                raise
            except Exception:
                await self._cleanup_batch_files(batch_file_entities)
                raise

            task.increase_processed(len(batch))

            async with self._uow:
                await self._uow.task_repo.update(task)
                await self._uow.commit()

        task.complete()
        async with self._uow:
            await self._uow.task_repo.update(task)
            await self._uow.commit()

        logger.info(
            "download_task_completed",
            task_id=task.id,
            received=task.received_files,
            processed=task.processed_files,
        )

    async def _maybe_heartbeat(self, task: DownloadTask, counter: int) -> None:
        if counter % self.HEARTBEAT_INTERVAL == 0:
            task.heartbeat()
            async with self._uow:
                await self._uow.task_repo.update(task)
                await self._uow.commit()

    async def _handle_block(self, task: DownloadTask, exc: ExternalAPIBlockedError) -> bool:
        retry_after = exc.retry_after
        if retry_after <= self.BLOCK_THRESHOLD_SECONDS:
            return False

        task.block(retry_after, reason=str(exc))
        async with self._uow:
            await self._uow.task_repo.update(task)
            await self._uow.commit()

        logger.warning(
            "task_blocked",
            task_id=task.id,
            blocked_until=str(task.blocked_until),
            retry_after=retry_after,
        )
        return True

    async def _cleanup_batch_files(self, files: list[File]) -> None:
        for file_entity in files:
            if file_entity.storage_key is None:
                continue
            try:
                await self._storage.delete(file_entity.storage_key.value)
            except Exception as e:
                logger.warning(
                    "failed_to_delete_file_from_storage",
                    file_id=str(file_entity.id),
                    error=str(e),
                )
            try:
                async with self._uow:
                    await self._uow.file_repo.delete(file_entity.id)
                    await self._uow.commit()
            except Exception as e:
                logger.warning(
                    "failed_to_delete_file_from_db",
                    file_id=str(file_entity.id),
                    error=str(e),
                )

    async def _fail_task(self, task: DownloadTask, error: str) -> None:
        task.fail(error)
        async with self._uow:
            await self._uow.task_repo.update(task)
            await self._uow.commit()
