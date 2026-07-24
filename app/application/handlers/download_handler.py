from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

from loguru import logger

from app.application.commands import ProcessFilesCommand, StartDownloadCommand
from app.application.ports import ExternalAPIClient, FileProcessor, ObjectStorage
from app.application.unit_of_work import UnitOfWork
from app.domain.entities.download_task import DownloadTask
from app.domain.entities.file import File
from app.domain.value_objects import FileHash, FileId, FileSize, StorageKey


class StartDownloadHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, command: StartDownloadCommand) -> str:
        task_id = str(uuid4())

        task = DownloadTask(
            task_id=task_id,
            candidate_id=command.candidate_id or "",
        )
        task.start()

        async with self._uow:
            await self._uow.task_repo.add(task)
            await self._uow.commit()

        logger.info(
            "download_task_created",
            task_id=task_id,
            candidate_id=command.candidate_id,
        )
        return task_id


class ProcessFilesHandler:
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
        while True:
            names_result = await self._api.get_file_names(command.candidate_id)
            if not names_result.file_names:
                break

            batch = names_result.file_names[:3]
            task.increase_received(len(names_result.file_names))

            zip_stream = await self._api.download_files_stream(batch)

            async for extracted in self._processor.extract_stream(zip_stream):
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
                    await self._uow.commit()

                logger.info(
                    "file_uploaded",
                    file_id=str(file_entity.id),
                    filename=extracted.filename,
                    size=extracted.size,
                )

            await self._api.mark_downloaded(batch, command.candidate_id)
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

    async def _fail_task(self, task: DownloadTask, error: str) -> None:
        task.fail(error)
        async with self._uow:
            await self._uow.task_repo.update(task)
            await self._uow.commit()
