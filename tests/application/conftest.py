from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.unit_of_work import UnitOfWork


@pytest.fixture
def mock_uow() -> MagicMock:
    uow = MagicMock(spec=UnitOfWork)
    uow.file_repo = AsyncMock()
    uow.task_repo = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    uow.flush = AsyncMock()
    return uow
