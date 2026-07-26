from __future__ import annotations

import json
import os
import tempfile
from collections.abc import AsyncIterator
from typing import Any, cast

import aiofiles
import httpx
from loguru import logger

from app.application.exceptions import ExternalAPIBlockedError
from app.application.ports.external_api import ExternalAPIClient, FileNamesResult
from app.core.config import settings
from app.infrastructure.external_api.exceptions import (
    ExternalAPIForbiddenError,
    ExternalAPINotFoundError,
    ExternalAPIParseError,
    ExternalAPIRateLimitedError,
    ExternalAPIServerError,
)
from app.infrastructure.external_api.rate_limiter import AdaptiveRateLimiter
from app.infrastructure.external_api.retry import AsyncRetryExecutor, with_retry


class CatalogClient(ExternalAPIClient):
    def __init__(self) -> None:
        self._base_url = settings.external_api_base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=settings.external_api_timeout_seconds)
        self._rate_limiter = AdaptiveRateLimiter()
        self._retry = AsyncRetryExecutor(
            max_retries=settings.external_api_max_retries,
            rate_limit_retries=settings.external_api_rate_limit_retries,
            retryable_exceptions=(TimeoutError, httpx.HTTPError),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> CatalogClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    @with_retry()
    async def get_file_names(self, candidate_id: str | None = None) -> FileNamesResult:
        headers = self._build_headers(candidate_id)
        return await self._request_get_file_names(headers)

    async def download_files_stream(self, file_names: list[str]) -> AsyncIterator[bytes]:
        headers = {"Content-Type": "application/json"}
        path = await self._retry.execute(
            lambda: self._request_download_stream(file_names, headers),
            "download_stream",
        )
        try:
            async with aiofiles.open(path, "rb") as f:
                while True:
                    chunk = await f.read(65536)
                    if not chunk:
                        break
                    yield chunk
        finally:
            os.unlink(path)

    @with_retry()
    async def mark_downloaded(
        self, file_names: list[str], candidate_id: str | None = None
    ) -> tuple[int, int]:
        headers = self._build_headers(candidate_id)
        return await self._request_mark_downloaded(headers, file_names)

    async def _request_get_file_names(self, headers: dict[str, str]) -> FileNamesResult:
        await self._rate_limiter.wait()
        response = await self._client.get(
            f"{self._base_url}/api/files/names",
            headers=headers,
        )
        await self._handle_errors(response)
        data = _safe_json(response, "get_file_names")
        self._rate_limiter.on_success()
        return FileNamesResult(file_names=data.get("file_names", []))

    async def _request_download_stream(self, file_names: list[str], headers: dict[str, str]) -> str:
        await self._rate_limiter.wait()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            name = tmp.name

        try:
            async with aiofiles.open(name, "wb") as f:
                async with self._client.stream(
                    "POST",
                    f"{self._base_url}/api/files/download",
                    json={"file_names": file_names},
                    headers=headers,
                ) as response:
                    await self._handle_errors(response)
                    async for chunk in response.aiter_bytes():
                        await f.write(chunk)
                await f.flush()
            self._rate_limiter.on_success()
            return name
        except Exception:
            os.unlink(name)
            raise

    async def _request_mark_downloaded(
        self, headers: dict[str, str], file_names: list[str]
    ) -> tuple[int, int]:
        await self._rate_limiter.wait()
        logger.info(f"mark_downloaded request: file_names={file_names}")
        response = await self._client.post(
            f"{self._base_url}/api/files/downloaded",
            json={"file_names": file_names},
            headers=headers,
        )
        await self._handle_errors(response)
        data = _safe_json(response, "mark_downloaded")
        self._rate_limiter.on_success()
        logger.info(f"mark_downloaded response: {data}")
        return data.get("marked_now", 0), data.get("already_marked", 0)

    async def _handle_errors(self, response: httpx.Response) -> None:
        if response.status_code == 429:
            self._rate_limiter.on_failure()
            retry_after = response.headers.get("Retry-After", "60")
            logger.warning(f"rate_limited retry_after={retry_after}s", status=429)
            raise ExternalAPIRateLimitedError(int(retry_after))

        if response.status_code == 403:
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                self._rate_limiter.on_failure()
                logger.warning(f"blocked retry_after={retry_after}s", status=403)
                raise ExternalAPIBlockedError(int(retry_after))
            logger.warning("forbidden", status=403)
            raise ExternalAPIForbiddenError()

        if response.status_code == 404:
            data = _safe_json(response, "handle_errors")
            raise ExternalAPINotFoundError(data.get("detail", "Resource not found"))

        if response.status_code >= 500:
            raise ExternalAPIServerError(f"Server error: {response.status_code}")

        response.raise_for_status()

    @staticmethod
    def _build_headers(candidate_id: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {}
        cid = candidate_id or settings.candidate_id
        if cid:
            headers["X-Candidate-Id"] = cid
        return headers


def _safe_json(response: httpx.Response, context: str = "") -> dict[str, Any]:
    try:
        return cast("dict[str, Any]", response.json())
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        raise ExternalAPIParseError(f"Invalid JSON in {context}: {e}") from e
