from __future__ import annotations

import asyncio
import json
import os
import random
import tempfile
from collections.abc import AsyncIterator
from typing import Any

import aiofiles
import httpx
from loguru import logger

from app.application.ports.external_api import ExternalAPIClient, FileNamesResult
from app.core.config import settings


def calculate_retry_delay(retry_after: int) -> float:
    base = retry_after * 1.1
    jitter = min(retry_after * 0.05, 10)
    return base + random.uniform(0, jitter)


class CatalogClient(ExternalAPIClient):
    def __init__(self) -> None:
        self._base_url = settings.external_api_base_url.rstrip("/")
        self._timeout = settings.external_api_timeout_seconds
        self._max_retries = settings.external_api_max_retries
        self._rate_limit_retries = settings.external_api_rate_limit_retries
        self._client = httpx.AsyncClient(timeout=self._timeout)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> CatalogClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def get_file_names(self, candidate_id: str | None = None) -> FileNamesResult:
        headers = self._build_headers(candidate_id)
        return await self._with_retry(
            request_fn=lambda: self._request_get_file_names(headers),
            operation_name="get_file_names",
        )

    async def download_files_stream(self, file_names: list[str]) -> AsyncIterator[bytes]:
        headers = {"Content-Type": "application/json"}
        path = await self._with_retry(
            request_fn=lambda: self._request_download_stream(file_names, headers),
            operation_name="download_stream",
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

    async def mark_downloaded(
        self, file_names: list[str], candidate_id: str | None = None
    ) -> tuple[int, int]:
        headers = self._build_headers(candidate_id)
        return await self._with_retry(
            request_fn=lambda: self._request_mark_downloaded(headers, file_names),
            operation_name="mark_downloaded",
        )

    async def _request_get_file_names(self, headers: dict[str, str]) -> FileNamesResult:
        response = await self._client.get(
            f"{self._base_url}/api/files/names",
            headers=headers,
        )
        await self._handle_errors(response)
        data = _safe_json(response, "get_file_names")
        return FileNamesResult(file_names=data.get("file_names", []))

    async def _request_download_stream(
        self, file_names: list[str], headers: dict[str, str]
    ) -> str:
        tmp = tempfile.NamedTemporaryFile(delete=False)  # noqa: SIM115 — need name before aiofiles.open
        name = tmp.name
        tmp.close()
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
            return name
        except Exception:
            os.unlink(name)
            raise

    async def _request_mark_downloaded(
        self, headers: dict[str, str], file_names: list[str]
    ) -> tuple[int, int]:
        response = await self._client.post(
            f"{self._base_url}/api/files/downloaded",
            json={"file_names": file_names},
            headers=headers,
        )
        await self._handle_errors(response)
        data = _safe_json(response, "mark_downloaded")
        return data.get("marked_now", 0), data.get("already_marked", 0)

    async def _with_retry(self, request_fn, operation_name: str):
        attempt = 0
        rate_attempt = 0

        while True:
            try:
                return await request_fn()
            except ExternalAPIRateLimitedError as e:
                rate_attempt += 1
                if self._rate_limit_retries >= 0 and rate_attempt > self._rate_limit_retries:
                    logger.error(
                        f"{operation_name}_rate_limit_exhausted retry_after={e.retry_after}s",
                        attempt=rate_attempt,
                    )
                    raise
                logger.warning(
                    f"{operation_name}_rate_limited retry_after={e.retry_after}s",
                    attempt=rate_attempt,
                )
                await asyncio.sleep(calculate_retry_delay(e.retry_after))
            except ExternalAPIBlockedError as e:
                rate_attempt += 1
                if self._rate_limit_retries >= 0 and rate_attempt > self._rate_limit_retries:
                    logger.error(
                        f"{operation_name}_blocked_exhausted retry_after={e.retry_after}s",
                        attempt=rate_attempt,
                    )
                    raise
                logger.warning(
                    f"{operation_name}_blocked retry_after={e.retry_after}s",
                    attempt=rate_attempt,
                )
                await asyncio.sleep(calculate_retry_delay(e.retry_after))
            except (TimeoutError, httpx.HTTPError, ExternalAPIServerError) as e:
                attempt += 1
                if attempt > self._max_retries:
                    logger.error(f"{operation_name}_failed", error=str(e))
                    raise
                wait = 2 ** attempt
                logger.warning(
                    f"{operation_name}_retry",
                    attempt=attempt,
                    error=str(e),
                    wait=wait,
                )
                await asyncio.sleep(wait)

    async def _handle_errors(self, response: httpx.Response) -> None:
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "60")
            logger.warning(f"rate_limited retry_after={retry_after}s", status=429)
            raise ExternalAPIRateLimitedError(int(retry_after))

        if response.status_code == 403:
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
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
        return response.json()
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        raise ExternalAPIParseError(f"Invalid JSON in {context}: {e}") from e


class ExternalAPIRateLimitedError(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s")


class ExternalAPIBlockedError(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__(f"Blocked. Retry after {retry_after}s")


class ExternalAPIForbiddenError(Exception):
    pass


class ExternalAPINotFoundError(Exception):
    pass


class ExternalAPIServerError(Exception):
    pass


class ExternalAPIParseError(Exception):
    pass
