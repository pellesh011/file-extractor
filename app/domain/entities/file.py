from __future__ import annotations

from datetime import UTC, datetime

from app.domain.exceptions import FileAlreadyUploadedError, InvalidStatusTransitionError
from app.domain.value_objects import FileHash, FileId, FileSize, FileStatus, StorageKey


class File:
    def __init__(
        self,
        file_id: FileId,
        filename: str,
        size: FileSize,
        hash: FileHash | None = None,
        storage_key: StorageKey | None = None,
        status: FileStatus = FileStatus.CREATED,
        created_at: datetime | None = None,
        uploaded_at: datetime | None = None,
    ) -> None:
        self._id = file_id
        self._filename = filename
        self._size = size
        self._hash = hash
        self._storage_key = storage_key
        self._status = status
        self._created_at = created_at or datetime.now(UTC)
        self._uploaded_at = uploaded_at

    @property
    def id(self) -> FileId:
        return self._id

    @property
    def filename(self) -> str:
        return self._filename

    @property
    def size(self) -> FileSize:
        return self._size

    @property
    def hash(self) -> FileHash | None:
        return self._hash

    @hash.setter
    def hash(self, value: FileHash) -> None:
        self._hash = value

    @property
    def storage_key(self) -> StorageKey | None:
        return self._storage_key

    @property
    def status(self) -> FileStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def uploaded_at(self) -> datetime | None:
        return self._uploaded_at

    def start_upload(self) -> None:
        if self._status == FileStatus.UPLOADED:
            raise FileAlreadyUploadedError(str(self._id))
        if self._status != FileStatus.CREATED:
            raise InvalidStatusTransitionError("File", self._status.name, FileStatus.UPLOADING.name)
        self._status = FileStatus.UPLOADING

    def complete_upload(self, storage_key: StorageKey, file_hash: FileHash) -> None:
        if self._status != FileStatus.UPLOADING:
            raise InvalidStatusTransitionError("File", self._status.name, FileStatus.UPLOADED.name)
        self._storage_key = storage_key
        self._hash = file_hash
        self._status = FileStatus.UPLOADED
        self._uploaded_at = datetime.now(UTC)

    def fail_upload(self) -> None:
        if self._status not in (FileStatus.CREATED, FileStatus.UPLOADING):
            raise InvalidStatusTransitionError("File", self._status.name, FileStatus.FAILED.name)
        self._status = FileStatus.FAILED

    def __repr__(self) -> str:
        return f"File(id={self._id}, filename={self._filename}, status={self._status.name})"
