from uuid import UUID, uuid4

import pytest

from app.domain.value_objects import FileId


class TestFileIdCreation:
    def test_from_none_generates_uuid(self) -> None:
        fid = FileId()
        assert isinstance(fid.value, UUID)

    def test_from_uuid(self) -> None:
        uuid = uuid4()
        fid = FileId(uuid)
        assert fid.value == uuid

    def test_from_str(self) -> None:
        uuid = uuid4()
        fid = FileId(str(uuid))
        assert fid.value == uuid

    def test_from_invalid_str_raises(self) -> None:
        with pytest.raises(ValueError):
            FileId("not-a-uuid")


class TestFileIdEquality:
    def test_equal(self) -> None:
        uuid = uuid4()
        assert FileId(uuid) == FileId(uuid)

    def test_not_equal(self) -> None:
        assert FileId() != FileId()

    def test_equal_to_string(self) -> None:
        uuid = uuid4()
        assert FileId(uuid) == FileId(str(uuid))


class TestFileIdHashing:
    def test_hashable(self) -> None:
        u = uuid4()
        s = {FileId(u), FileId(u)}
        assert len(s) == 1


class TestFileIdStr:
    def test_str(self) -> None:
        uuid = uuid4()
        assert str(FileId(uuid)) == str(uuid)

    def test_repr(self) -> None:
        uuid = uuid4()
        assert repr(FileId(uuid)) == f"FileId({uuid})"
