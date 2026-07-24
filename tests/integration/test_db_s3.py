from collections.abc import AsyncIterator

import pytest

from app.domain.value_objects import FileHash, FileId, FileSize, StorageKey
from app.infrastructure.database.sqlalchemy_uow import SQLAlchemyUnitOfWork
from app.infrastructure.storage.s3_storage import S3Storage


class TestFixturesWork:
    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_postgres_fixture(self, uow: SQLAlchemyUnitOfWork) -> None:
        from app.domain.entities.file import File
        from app.domain.value_objects import FileStatus

        file = File(
            file_id=FileId(),
            filename="test.txt",
            size=FileSize(100),
        )
        file.start_upload()
        file.complete_upload(StorageKey("test/key"), FileHash("a" * 64))

        await uow.file_repo.add(file)
        await uow.commit()

        found = await uow.file_repo.get_by_id(file.id)
        assert found is not None
        assert found.filename == "test.txt"
        assert found.status == FileStatus.UPLOADED


class TestS3Storage:
    @pytest.mark.asyncio  # type: ignore[untyped-decorator]
    async def test_upload_and_download(self, s3_storage: S3Storage) -> None:
        import hashlib

        content = b"hello world"
        key = f"test/{hashlib.md5(content).hexdigest()}.txt"

        async def stream(data: bytes) -> AsyncIterator[bytes]:
            yield data

        returned_key = await s3_storage.upload_stream(stream(content), key=key, length=len(content))
        assert returned_key == key

        download_url = await s3_storage.get_download_url(key)
        assert download_url is not None
        assert "presigned" in download_url or "minio" in download_url
