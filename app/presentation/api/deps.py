from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.handlers import StartDownloadHandler, StatisticsHandler
from app.infrastructure.database.session import session_factory
from app.infrastructure.database.sqlalchemy_uow import SQLAlchemyUnitOfWork


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    session = session_factory()
    try:
        yield session
    finally:
        await session.close()


async def get_uow() -> SQLAlchemyUnitOfWork:
    session = session_factory()
    return SQLAlchemyUnitOfWork(session)


async def get_start_download_handler() -> StartDownloadHandler:
    uow = await get_uow()
    return StartDownloadHandler(uow)


async def get_statistics_handler() -> StatisticsHandler:
    uow = await get_uow()
    return StatisticsHandler(uow)
