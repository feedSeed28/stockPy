"""Cache-first live data fetcher — DB → AKShare → save → return.

Provides transparent real-time data fallback for API endpoints.
When local DB has no data (sync hasn't run yet), fetches from AKShare
live, saves to DB for next request, and returns immediately.

Anti-abuse measures:
- Per-key deduplication (concurrent requests share one AKShare call)
- Global semaphore (max 3 concurrent AKShare calls)
- Timeout (8s per fetch, 5s per save)
- Graceful degradation (returns empty on failure, never 500)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class LiveFetcher:
    """Cache-first proxy: queries local DB, falls back to live AKShare."""

    def __init__(self, timeout: float = 8.0, max_concurrency: int = 3):
        self._timeout = timeout
        self._in_flight: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def fetch_or_live(
        self,
        db: AsyncSession,
        *,
        cache_key: str,
        db_query_fn: Callable[[AsyncSession], Awaitable[Any]],
        live_fetch_fn: Callable[[], Awaitable[Any]],
        save_fn: Callable[[AsyncSession, Any], Awaitable[None]] | None = None,
        is_empty: Callable[[Any], bool] | None = None,
    ) -> tuple[Any, bool]:
        """Check DB first; if empty, fetch from AKShare and cache.

        Args:
            cache_key: Unique dedup key (e.g. "financial:000001")
            db_query_fn: async fn(db) → data — re-queries DB (used both
                         for initial check and after saving live data)
            live_fetch_fn: async fn() → raw AKShare result
            save_fn: async fn(db, raw_data) → persist live-fetched data
            is_empty: predicate, default treats None/empty-list as empty

        Returns:
            (data, from_live) — from_live=True means data was live-fetched
        """
        _empty = is_empty or _default_is_empty

        # Step 1: Try DB
        db_data = await db_query_fn(db)
        if not _empty(db_data):
            return db_data, False

        # Step 2: Dedup — reuse in-flight task for same cache_key
        async with self._lock:
            if cache_key in self._in_flight:
                task = self._in_flight[cache_key]
            else:
                task = asyncio.create_task(
                    self._do_live_fetch(db, cache_key, live_fetch_fn, save_fn)
                )
                self._in_flight[cache_key] = task

        try:
            raw_data = await asyncio.wait_for(task, timeout=self._timeout)
        except asyncio.TimeoutError:
            logger.warning("Live fetch timeout for key=%s (%.1fs)", cache_key, self._timeout)
            return None, False
        except Exception as e:
            logger.error("Live fetch failed for key=%s: %s", cache_key, e)
            return None, False

        # Step 3: Data saved — re-query DB to return properly typed result
        if raw_data is not None:
            try:
                db_data = await db_query_fn(db)
                if not _empty(db_data):
                    return db_data, True
            except Exception as e:
                logger.warning("DB re-query after live fetch failed: %s", e)

        return raw_data, True

    async def _do_live_fetch(self, db, cache_key, live_fetch_fn, save_fn):
        """Execute the live fetch (inside semaphore), then save."""
        try:
            async with self._semaphore:
                data = await live_fetch_fn()

            # Best-effort save (separate timeout so slow DB doesn't block response)
            if save_fn and data is not None:
                try:
                    await asyncio.wait_for(save_fn(db, data), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("Save timeout for key=%s", cache_key)
                except Exception as e:
                    logger.warning("Save failed for key=%s: %s", cache_key, e)

            return data
        finally:
            async with self._lock:
                self._in_flight.pop(cache_key, None)


def _default_is_empty(data: Any) -> bool:
    """Treat None, empty list, empty dict, or PaginatedData with total=0 as empty."""
    if data is None:
        return True
    if isinstance(data, (list, tuple)):
        return len(data) == 0
    if isinstance(data, dict):
        if "total" in data and data["total"] == 0:
            return True
        return len(data) == 0
    return False


# Global singleton — import this in route files
live_fetcher = LiveFetcher(timeout=8.0, max_concurrency=3)
