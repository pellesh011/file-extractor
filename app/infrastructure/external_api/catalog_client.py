from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

import httpx
from loguru import logger

from app.application.ports.external_api import ExternalAPIClient, FileNamesResult
from app.core.config import settings


class CatalogClient(ExternalAPIClient):
    def __init__(self) -> None:
        self._base_url = settings.external_api_base_url.rstrip("/")
        self._timeout = settings.external_api_timeout_seconds
        self._max_retries = settings.external_api_max_retries

    async def get_file_names(self, candidate_id: str | None = None) -> FileNamesResult:
        headers = self._build_headers(candidate_id)

        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(
                        f"{self._base_url}/api/files/names",
                        headers=headers,
                    )
                    await self._handle_errors(response)
                    data = response.json()
                    return FileNamesResult(file_names=data.get("file_names", []))
            except (TimeoutError, httpx.HTTPError) as e:
                if attempt < self._max_retries:
                    wait = 2**attempt
                    logger.warning(
                        "get_file_names_retry",
                        attempt=attempt + 1,
                        error=str(e),
                        wait=wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("get_file_names_failed", error=str(e))
                    raise

        raise ExternalAPIServerError("All retries exhausted for get_file_names")

    async def download_files_stream(self, file_names: list[str]) -> AsyncIterator[bytes]:
        headers = {"Content-Type": "application/json"}

        async with (
            httpx.AsyncClient(timeout=self._timeout) as client,
            client.stream(
                "POST",
                f"{self._base_url}/api/files/download",
                json={"file_names": file_names},
                headers=headers,
            ) as response,
        ):
            await self._handle_errors(response)
            async for chunk in response.aiter_bytes():
                yield chunk

    async def mark_downloaded(
        self, file_names: list[str], candidate_id: str | None = None
    ) -> tuple[int, int]:
        headers = self._build_headers(candidate_id)

        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        f"{self._base_url}/api/files/downloaded",
                        json={"file_names": file_names},
                        headers=headers,
                    )
                    await self._handle_errors(response)
                    data = response.json()
                    return data.get("marked_now", 0), data.get("already_marked", 0)
            except (TimeoutError, httpx.HTTPError) as e:
                if attempt < self._max_retries:
                    wait = 2**attempt
                    logger.warning(
                        "mark_downloaded_retry",
                        attempt=attempt + 1,
                        error=str(e),
                        wait=wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error("mark_downloaded_failed", error=str(e))
                    raise

        raise ExternalAPIServerError("All retries exhausted for mark_downloaded")

    async def _handle_errors(self, response: httpx.Response) -> None:
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "60")
            logger.warning("rate_limited", retry_after=retry_after, status=429)
            raise ExternalAPIRateLimitedError(int(retry_after))

        if response.status_code == 403:
            retry_after = response.headers.get("Retry-After", "1800")
            logger.warning("blocked", retry_after=retry_after, status=403)
            raise ExternalAPIBlockedError(int(retry_after))

        if response.status_code == 404:
            data = response.json()
            raise ExternalAPINotFoundError(data.get("detail", "Resource not found"))

        if response.status_code >= 500:
            raise ExternalAPIServerError(f"Server error: {response.status_code}")

        response.raise_for_status()

    @staticmethod
    def _build_headers(candidate_id: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        if candidate_id:
            headers["X-Candidate-Id"] = candidate_id
        return headers


class ExternalAPIRateLimitedError(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s")


class ExternalAPIBlockedError(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Blocked. Retry after {retry_after}s")


class ExternalAPINotFoundError(Exception):
    pass


class ExternalAPIServerError(Exception):
    pass
