from __future__ import annotations

from dataclasses import dataclass

from app.application.ports import ObjectStorage
from app.application.unit_of_work import UnitOfWork
from app.domain.value_objects import FileId


@dataclass
class CalculateStatsQuery:
    file_ids: list[str]


@dataclass
class CalculateStatsResult:
    total: dict[str, int]
    by_file: dict[str, dict[str, int]]


class CalculateStatsHandler:
    def __init__(self, uow: UnitOfWork, storage: ObjectStorage) -> None:
        self._uow = uow
        self._storage = storage

    async def execute(self, query: CalculateStatsQuery) -> CalculateStatsResult:
        files = []
        async with self._uow:
            for file_id in query.file_ids:
                file = await self._uow.file_repo.get_by_id(FileId(file_id))
                if file and file.hash and file.storage_key:
                    files.append((str(file.id), file.filename, file.storage_key.value))

        total: dict[str, int] = {}
        by_file: dict[str, dict[str, int]] = {}

        for _file_id, filename, storage_key in files:
            if not storage_key:
                continue
            content = await self._storage.download(storage_key)
            if not content:
                continue

            by_file[filename] = {}
            for char in content:
                if "0" <= char <= "9":
                    total[char] = total.get(char, 0) + 1
                    by_file[filename][char] = by_file[filename].get(char, 0) + 1

        for i in range(10):
            d = str(i)
            if d not in total:
                total[d] = 0
            for fname in by_file:
                if d not in by_file[fname]:
                    by_file[fname][d] = 0

        return CalculateStatsResult(total=total, by_file=by_file)
