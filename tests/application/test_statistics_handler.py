from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.handlers import StatisticsHandler
from app.application.queries.get_statistics import GetStatisticsQuery


class TestStatisticsHandler:
    @pytest.mark.asyncio
    async def test_execute_returns_zero_when_empty(self, mock_uow: MagicMock) -> None:
        mock_uow.file_repo.count_by_status = AsyncMock(return_value=0)
        handler = StatisticsHandler(uow=mock_uow)
        result = await handler.execute(GetStatisticsQuery())

        assert result.total_files == 0
        assert result.uploaded_files == 0
        assert result.failed_files == 0

    @pytest.mark.asyncio
    async def test_execute_counts_by_status(self, mock_uow: MagicMock) -> None:
        def count_side_effect(status: str) -> int:
            mapping = {"": 10, "UPLOADED": 15, "FAILED": 3}
            return mapping.get(status, 0)

        mock_uow.file_repo.count_by_status = AsyncMock(side_effect=count_side_effect)
        handler = StatisticsHandler(uow=mock_uow)
        result = await handler.execute(GetStatisticsQuery())

        assert result.total_files == 28
        assert result.uploaded_files == 15
        assert result.failed_files == 3
