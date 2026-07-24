from __future__ import annotations

from app.application.queries.get_statistics import GetStatisticsQuery, StatisticsResult
from app.application.unit_of_work import UnitOfWork
from app.domain.value_objects import FileStatus


class StatisticsHandler:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: GetStatisticsQuery) -> StatisticsResult:
        async with self._uow:
            total = await self._uow.file_repo.count_by_status("")
            uploaded = await self._uow.file_repo.count_by_status(FileStatus.UPLOADED.name)
            failed = await self._uow.file_repo.count_by_status(FileStatus.FAILED.name)

        result = StatisticsResult(
            total_files=total + uploaded + failed,
            uploaded_files=uploaded,
            failed_files=failed,
        )

        if result.total_files > 0:
            result.average_file_size = result.total_size / result.total_files

        return result
