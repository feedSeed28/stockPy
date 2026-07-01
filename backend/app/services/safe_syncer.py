"""Safe sync utilities — random delays, browser headers, batch pauses.

Makes AKShare requests look like human browsing to avoid IP bans.
"""

import asyncio
import random
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Browser-like User-Agent pool ──────────────────────────────────────────

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]


def random_ua() -> str:
    return random.choice(_USER_AGENTS)


# ── Human-like delay ──────────────────────────────────────────────────────


async def human_delay(base: float = 2.0, jitter: float = 0.8):
    """Sleep for base ± jitter seconds, rounded to 2 decimal places.

    A human browsing stocks doesn't click at exactly 2.000 second intervals.
    This makes the request pattern irregular.
    """
    delay = base + random.uniform(-jitter, jitter)
    delay = max(0.5, round(delay, 2))  # never less than 0.5s
    await asyncio.sleep(delay)


# ── Batch pause ───────────────────────────────────────────────────────────


async def batch_pause(batch_num: int, stocks_per_batch: int = 30, pause_seconds: int = 25):
    """Take a break every N stocks to avoid triggering rate limits.

    After each batch, pause for pause_seconds ± 5s.
    """
    jittered = pause_seconds + random.randint(-5, 5)
    logger.info(
        "Batch %d complete (%d stocks) — pausing %ds...",
        batch_num, stocks_per_batch, jittered,
    )
    await asyncio.sleep(jittered)


# ── Safe sync executor ────────────────────────────────────────────────────


class SafeSyncer:
    """Wraps AKShare calls with anti-blocking measures.

    Usage:
        syncer = SafeSyncer(base_delay=2.0, batch_size=30, batch_pause=25)
        async for batch in syncer.sync_batches(stock_codes, fetch_fn):
            # process batch results
            ...
    """

    def __init__(
        self,
        base_delay: float = 2.0,
        jitter: float = 0.8,
        batch_size: int = 30,
        batch_pause_sec: int = 25,
        max_retries: int = 3,
    ):
        self.base_delay = base_delay
        self.jitter = jitter
        self.batch_size = batch_size
        self.batch_pause_sec = batch_pause_sec
        self.max_retries = max_retries

    async def sync_all(
        self,
        items: list[Any],
        fetch_fn,
        save_fn=None,
    ) -> dict:
        """Sync all items with safe pacing.

        Args:
            items: List of items to process (e.g. stock codes)
            fetch_fn: async fn(item) -> data — fetch from AKShare
            save_fn: async fn(item, data) -> None — save to DB

        Returns: {ok: int, fail: int, skip: int}
        """
        ok, fail, skip = 0, 0, 0

        for batch_num in range(0, len(items), self.batch_size):
            batch = items[batch_num : batch_num + self.batch_size]
            batch_idx = batch_num // self.batch_size + 1
            total_batches = (len(items) + self.batch_size - 1) // self.batch_size

            logger.info(
                "Batch %d/%d (%d items)",
                batch_idx, total_batches, len(batch),
            )

            for item in batch:
                try:
                    data = await self._fetch_with_retry(fetch_fn, item)
                    if data is None:
                        skip += 1
                    else:
                        if save_fn:
                            await save_fn(item, data)
                        ok += 1
                except Exception as e:
                    fail += 1
                    logger.warning("Failed: %s — %s", item, str(e)[:80])

                await human_delay(self.base_delay, self.jitter)

            # Pause between batches (unless it's the last batch)
            if batch_num + self.batch_size < len(items):
                await batch_pause(batch_idx, len(batch), self.batch_pause_sec)

        logger.info("Done: ok=%d fail=%d skip=%d", ok, fail, skip)
        return {"ok": ok, "fail": fail, "skip": skip}

    async def _fetch_with_retry(self, fetch_fn, item):
        """Call fetch_fn with retries on connection errors."""
        for attempt in range(self.max_retries):
            try:
                return await fetch_fn(item)
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt * self.base_delay
                    logger.debug("Retry %d/%d for %s in %.1fs", attempt + 1, self.max_retries, item, wait)
                    await asyncio.sleep(wait)
                else:
                    raise
