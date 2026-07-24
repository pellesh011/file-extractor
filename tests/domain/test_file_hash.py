import hashlib

import pytest

from app.domain.exceptions import InvalidFileHashError
from app.domain.value_objects import FileHash


class TestFileHashCreation:
    def test_valid_sha256(self) -> None:
        h = "a" * 64
        fh = FileHash(h)
        assert fh.value == h

    def test_invalid_sha256_raises(self) -> None:
        with pytest.raises(InvalidFileHashError):
            FileHash("too-short")

    def test_invalid_characters_raises(self) -> None:
        with pytest.raises(InvalidFileHashError):
            FileHash("z" + "a" * 63)


class TestFileHashCompute:
    def test_compute_from_bytes(self) -> None:
        data = b"hello world"
        expected = hashlib.sha256(data).hexdigest()
        assert FileHash.compute(data).value == expected

    def test_compute_empty(self) -> None:
        expected = hashlib.sha256(b"").hexdigest()
        assert FileHash.compute(b"").value == expected


class TestFileHashEquality:
    def test_equal(self) -> None:
        h = "b" * 64
        assert FileHash(h) == FileHash(h)

    def test_not_equal(self) -> None:
        assert FileHash("a" * 64) != FileHash("b" * 64)
