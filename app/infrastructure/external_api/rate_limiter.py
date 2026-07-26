from __future__ import annotations

import asyncio

from loguru import logger


class AdaptiveRateLimiter:
    def __init__(
        self,
        initial_delay: float = 1,
        min_delay: float = 0.1,
        max_delay: float = 10.0,
    ) -> None:
        self._delay = initial_delay
        self._min_delay = min_delay
        self._max_delay = max_delay

    async def wait(self) -> None:
        await asyncio.sleep(self._delay)

    def on_success(self) -> None:
        old = self._delay
        self._delay = max(self._min_delay, self._delay * 0.5)
        if self._delay != old:
            logger.debug("adaptive_limiter_decreased", delay=self._delay)

    def on_failure(self) -> None:
        old = self._delay
        self._delay = min(self._max_delay, self._delay * 2.5)
        if self._delay != old:
            logger.debug("adaptive_limiter_increased", delay=self._delay)
