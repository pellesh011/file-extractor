from __future__ import annotations

from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.minio import MinioContainer
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from app.core import config as config_module
from app.infrastructure.database.models import Base
from app.infrastructure.database.sqlalchemy_uow import SQLAlchemyUnitOfWork
from app.infrastructure.storage.s3_storage import S3Storage


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer(
        "postgres:16-alpine", username="app", password="secret", dbname="file_extractor"
    ) as c:
        yield c


@pytest.fixture(scope="session")
def redis_container() -> Iterator[RedisContainer]:
    with RedisContainer("redis:7-alpine") as c:
        yield c


@pytest.fixture(scope="session")
def minio_container() -> Iterator[MinioContainer]:
    with MinioContainer(
        "minio/minio:latest", access_key="minioadmin", secret_key="minioadmin123"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def db_engine(postgres_container: PostgresContainer) -> AsyncIterator:
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session_factory(db_engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def uow(db_session_factory) -> AsyncIterator[SQLAlchemyUnitOfWork]:
    async with db_session_factory() as session:
        uow = SQLAlchemyUnitOfWork(session)
        yield uow


@pytest_asyncio.fixture
async def s3_storage(minio_container: MinioContainer) -> AsyncIterator[S3Storage]:
    import aiobotocore.session

    s3_url = (
        f"http://{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}"
    )
    session = aiobotocore.session.AioSession()

    async with session.create_client(
        "s3",
        endpoint_url=s3_url,
        aws_access_key_id="minioadmin",
        aws_secret_access_key="minioadmin123",
    ) as client:
        await client.create_bucket(Bucket="files")

    storage = S3Storage()
    yield storage


@pytest.fixture(autouse=True)
def override_settings(
    monkeypatch: pytest.MonkeyPatch,
    postgres_container: PostgresContainer,
    redis_container: RedisContainer,
    minio_container: MinioContainer,
) -> None:
    pg_url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    redis_url = f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}/0"
    s3_url = (
        f"http://{minio_container.get_container_host_ip()}:{minio_container.get_exposed_port(9000)}"
    )

    settings = config_module.settings
    settings.database_url = pg_url
    settings.redis_url = redis_url
    settings.s3_endpoint_url = s3_url
    settings.s3_access_key_id = "minioadmin"
    settings.s3_secret_access_key = "minioadmin123"
    settings.s3_bucket_name = "files"
    settings.log_level = "DEBUG"
    settings.celery_broker_url = redis_url
    settings.celery_result_backend = redis_url
