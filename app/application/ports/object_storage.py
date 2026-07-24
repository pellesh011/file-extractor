from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class ObjectStorage(ABC):
    @abstractmethod
    async def upload_stream(
        self,
        stream: AsyncIterator[bytes],
        key: str,
        length: int,
    ) -> str: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    async def get_download_url(self, key: str, expires_in: int = 3600) -> str | None: ...

    @abstractmethod
    async def download(self, key: str) -> str | None: ...
