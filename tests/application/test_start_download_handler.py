from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.commands import StartDownloadCommand
from app.application.handlers import StartDownloadHandler


class TestStartDownloadHandler:
    @pytest.mark.asyncio
    async def test_execute_returns_task_id(self, mock_uow: MagicMock) -> None:
        mock_uow.task_repo.add = AsyncMock()
        handler = StartDownloadHandler(uow=mock_uow)
        command = StartDownloadCommand(candidate_id="candidate-1")

        task_id = await handler.execute(command)

        assert isinstance(task_id, str)
        assert len(task_id) == 36
        mock_uow.task_repo.add.assert_awaited_once()
        mock_uow.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_execute_without_candidate(self, mock_uow: MagicMock) -> None:
        handler = StartDownloadHandler(uow=mock_uow)
        task_id = await handler.execute(StartDownloadCommand())
        assert isinstance(task_id, str)

    @pytest.mark.asyncio
    async def test_execute_creates_running_task(self, mock_uow: MagicMock) -> None:
        handler = StartDownloadHandler(uow=mock_uow)
        command = StartDownloadCommand(candidate_id="test")

        task_id = await handler.execute(command)

        added = mock_uow.task_repo.add.call_args[0][0]
        assert added.id == task_id
        assert added.candidate_id == "test"
        assert added.status.name == "RUNNING"
        assert added.started_at is not None
