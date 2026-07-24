import pytest

from app.domain.exceptions import NegativeFileSizeError
from app.domain.value_objects import FileSize


class TestFileSize:
    def test_zero(self) -> None:
        fs = FileSize(0)
        assert fs.value == 0

    def test_positive(self) -> None:
        fs = FileSize(1024)
        assert fs.value == 1024

    def test_negative_raises(self) -> None:
        with pytest.raises(NegativeFileSizeError):
            FileSize(-1)

    def test_equality(self) -> None:
        assert FileSize(100) == FileSize(100)
        assert FileSize(100) != FileSize(200)
