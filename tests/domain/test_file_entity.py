import pytest

from app.domain.entities.file import File
from app.domain.exceptions import FileAlreadyUploadedError, InvalidStatusTransitionError
from app.domain.value_objects import FileHash, FileId, FileSize, FileStatus, StorageKey


@pytest.fixture
def file() -> File:
    return File(
        file_id=FileId(),
        filename="test.txt",
        size=FileSize(100),
    )


class TestFileCreation:
    def test_default_status(self, file: File) -> None:
        assert file.status == FileStatus.CREATED
        assert file.hash is None
        assert file.storage_key is None
        assert file.uploaded_at is None


class TestFileUploadFlow:
    def test_full_lifecycle(self, file: File) -> None:
        file.start_upload()
        assert file.status == FileStatus.UPLOADING

        sk = StorageKey("files/hash.txt")
        fh = FileHash("a" * 64)
        file.complete_upload(sk, fh)
        assert file.status == FileStatus.UPLOADED
        assert file.storage_key == sk
        assert file.hash == fh
        assert file.uploaded_at is not None

    def test_cannot_upload_from_uploaded(self, file: File) -> None:
        file.start_upload()
        sk = StorageKey("k")
        fh = FileHash("a" * 64)
        file.complete_upload(sk, fh)
        with pytest.raises(FileAlreadyUploadedError):
            file.start_upload()


class TestFileFail:
    def test_fail_from_created(self, file: File) -> None:
        file.fail_upload()
        assert file.status == FileStatus.FAILED

    def test_fail_from_uploading(self, file: File) -> None:
        file.start_upload()
        file.fail_upload()
        assert file.status == FileStatus.FAILED

    def test_cannot_fail_from_uploaded(self, file: File) -> None:
        file.start_upload()
        file.complete_upload(StorageKey("k"), FileHash("a" * 64))
        with pytest.raises(InvalidStatusTransitionError):
            file.fail_upload()

    def test_cannot_fail_from_failed(self, file: File) -> None:
        file.fail_upload()
        with pytest.raises(InvalidStatusTransitionError):
            file.fail_upload()
