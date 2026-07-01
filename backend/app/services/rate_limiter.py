"""Rate limiter and retry utilities for AKShare sync."""

import asyncio
import functools
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# ── Rate Limiter ─────────────────────────────────────────────────────────


class TokenBucket:
    """Simple token-bucket rate limiter for sync call pacing."""

    def __init__(self, calls_per_second: float = 3.0, burst: int = 5):
        self.rate = calls_per_second
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()

    async def acquire(self):
        """Block until a token is available."""
        while True:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return
            wait = (1.0 - self.tokens) / self.rate
            await asyncio.sleep(wait)


# Global rate limiter instance (3 calls/sec, burst 5)
_bucket = TokenBucket(calls_per_second=2.0, burst=3)


async def throttle():
    """Acquire a rate-limit token before making an AKShare call."""
    await _bucket.acquire()


# ── Retry Decorators ─────────────────────────────────────────────────────


def async_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 4.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
):
    """Async decorator: retry with exponential backoff.

    Delays: base_delay, base_delay * backoff_factor, base_delay * backoff_factor^2, ...
    Each delay is capped at max_delay.
    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_retries:
                        delay = min(base_delay * (backoff_factor**attempt), max_delay)
                        logger.warning(
                            "%s attempt %d/%d failed: %s. Retrying in %.1fs...",
                            func.__name__,
                            attempt + 1,
                            max_retries + 1,
                            e,
                            delay,
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "%s failed after %d retries: %s",
                            func.__name__,
                            max_retries + 1,
                            e,
                        )
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


def sync_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 4.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
):
    """Sync decorator: retry with exponential backoff."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_retries:
                        delay = min(base_delay * (backoff_factor**attempt), max_delay)
                        logger.warning(
                            "%s attempt %d/%d failed: %s. Retrying in %.1fs...",
                            func.__name__,
                            attempt + 1,
                            max_retries + 1,
                            e,
                            delay,
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            "%s failed after %d retries: %s",
                            func.__name__,
                            max_retries + 1,
                            e,
                        )
            raise last_exc

        return wrapper

    return decorator
