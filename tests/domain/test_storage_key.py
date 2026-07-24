from app.domain.value_objects import StorageKey


class TestStorageKey:
    def test_creation(self) -> None:
        sk = StorageKey("some/path/file.txt")
        assert sk.value == "some/path/file.txt"

    def test_empty(self) -> None:
        sk = StorageKey("")
        assert sk.value == ""

    def test_equality(self) -> None:
        assert StorageKey("a") == StorageKey("a")
        assert StorageKey("a") != StorageKey("b")
