from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from loguru import logger

from app.application.exceptions import (
    ExternalAPIRateLimitedError,
    ExternalAPIServerError,
)

F = TypeVar("F", bound=Callable[..., Any])
R = TypeVar("R")


def _calculate_retry_delay(retry_after: int) -> float:
    base = retry_after * 1.1
    jitter = min(retry_after * 0.05, 10)
    return base + random.uniform(0, jitter)


class AsyncRetryExecutor:
    def __init__(
        self,
        max_retries: int = 3,
        rate_limit_retries: int = 5,
        retryable_exceptions: tuple[type[Exception], ...] = (TimeoutError,),
    ) -> None:
        self._max_retries = max_retries
        self._rate_limit_retries = rate_limit_retries
        self._retryable_exceptions = retryable_exceptions

    async def execute(
        self,
        fn: Callable[[], Awaitable[R]],
        operation_name: str,
    ) -> R:
        attempt = 0
        rate_attempt = 0

        while True:
            try:
                return await fn()

            except ExternalAPIRateLimitedError as e:
                rate_attempt += 1

                if self._retry_exhausted(rate_attempt, self._rate_limit_retries):
                    logger.error(
                        f"{operation_name}_rate_limit_exhausted",
                        attempt=rate_attempt,
                    )
                    raise

                await self._sleep_rate_limit(
                    operation_name,
                    rate_attempt,
                    e.retry_after,
                )

            except (*self._retryable_exceptions, ExternalAPIServerError) as e:  # type: ignore[misc]
                attempt += 1

                if attempt > self._max_retries:
                    logger.error(
                        f"{operation_name}_failed",
                        error=str(e),
                    )
                    raise

                wait = 2**attempt

                logger.warning(
                    f"{operation_name}_retry",
                    attempt=attempt,
                    wait=wait,
                    error=str(e),
                )

                await asyncio.sleep(wait)

    async def _sleep_rate_limit(
        self,
        operation_name: str,
        attempt: int,
        retry_after: int,
    ) -> None:
        delay = _calculate_retry_delay(retry_after)

        logger.warning(
            f"{operation_name}_rate_limited",
            attempt=attempt,
            retry_after=retry_after,
            sleep=delay,
        )

        await asyncio.sleep(delay)

    @staticmethod
    def _retry_exhausted(attempt: int, limit: int) -> bool:
        return limit >= 0 and attempt > limit


def with_retry(operation_name: str | None = None) -> Callable[[F], F]:
    def decorator(func: F) -> F:
        async def wrapper(self: object, *args: Any, **kwargs: Any) -> Any:
            executor: AsyncRetryExecutor = self._retry  # type: ignore[attr-defined]
            return await executor.execute(
                lambda: func(self, *args, **kwargs),
                operation_name or func.__name__,
            )

        return wrapper  # type: ignore[return-value]

    return decorator
