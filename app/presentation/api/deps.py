from collections.abc import AsyncGenerator

from fastapi import Depends

from app.application.handlers import (
    CalculateStatsHandler,
    StartDownloadHandler,
    StatisticsHandler,
)
from app.infrastructure.database.session import session_factory
from app.infrastructure.database.sqlalchemy_uow import SQLAlchemyUnitOfWork
from app.infrastructure.storage.s3_storage import S3Storage

storage = S3Storage()


async def get_storage() -> S3Storage:
    return storage


async def get_uow() -> AsyncGenerator[SQLAlchemyUnitOfWork, None]:
    """FastAPI dependency that provides a UnitOfWork."""
    session = session_factory()
    uow = SQLAlchemyUnitOfWork(session)
    try:
        yield uow
    finally:
        await session.close()


async def get_start_download_handler(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> StartDownloadHandler:
    return StartDownloadHandler(uow)


async def get_statistics_handler(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
) -> StatisticsHandler:
    return StatisticsHandler(uow)


async def get_calculate_stats_handler(
    uow: SQLAlchemyUnitOfWork = Depends(get_uow),
    storage: S3Storage = Depends(get_storage),
) -> CalculateStatsHandler:
    return CalculateStatsHandler(uow, storage)
