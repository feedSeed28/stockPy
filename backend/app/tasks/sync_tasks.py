"""APScheduler tasks for incremental data sync.

Runs on trading days after market close (16:00 Beijing time).
Configured as async tasks so they reuse the FastAPI async session factory.
"""

from __future__ import annotations

import logging
from datetime import date, datetime

from app.core.database import async_session
from app.services.stock_sync_service import StockSyncService

logger = logging.getLogger(__name__)


async def _run_in_session(coro):
    """Create a session, run a coroutine, then close."""
    async with async_session() as db:
        svc = StockSyncService(db)
        return await coro(svc)


# ── Scheduled Jobs ────────────────────────────────────────────────────────


async def sync_daily_kline_incremental():
    """Daily incremental K-line sync — last 5 trading days, all stocks."""
    logger.info("[scheduler] Starting daily K-line incremental sync...")
    try:
        result = await _run_in_session(lambda svc: svc.sync_daily_incremental(adjust_type="qfq", lookback_days=5))
        logger.info("[scheduler] Daily K-line sync done: %d rows", result)
    except Exception as e:
        logger.error("[scheduler] Daily K-line sync failed: %s", e)


async def sync_weekly_kline():
    """Weekly K-line sync (Mondays after close)."""
    logger.info("[scheduler] Starting weekly K-line sync...")
    try:
        result = await _run_in_session(
            lambda svc: svc.sync_kline_batch(period="weekly", adjust_type="qfq")
        )
        logger.info("[scheduler] Weekly K-line sync done: %s", result)
    except Exception as e:
        logger.error("[scheduler] Weekly K-line sync failed: %s", e)


async def sync_monthly_kline():
    """Monthly K-line sync (first trading day of month)."""
    logger.info("[scheduler] Starting monthly K-line sync...")
    try:
        result = await _run_in_session(
            lambda svc: svc.sync_kline_batch(period="monthly", adjust_type="qfq")
        )
        logger.info("[scheduler] Monthly K-line sync done: %s", result)
    except Exception as e:
        logger.error("[scheduler] Monthly K-line sync failed: %s", e)


async def sync_stock_list_weekly():
    """Weekly stock list check — detect new listings."""
    logger.info("[scheduler] Checking for new stock listings...")
    try:
        result = await _run_in_session(lambda svc: svc.sync_stock_list())
        logger.info("[scheduler] Stock list check done: %d stocks", result)
    except Exception as e:
        logger.error("[scheduler] Stock list check failed: %s", e)


async def sync_performance_reports():
    """Check for new quarterly reports daily."""
    logger.info("[scheduler] Checking for new performance reports...")
    try:
        # Only sync the latest 2 quarters
        from datetime import date
        today = date.today()
        # Current quarter
        current_q = ((today.month - 1) // 3) * 3 + 3
        last_quarter = date(today.year, current_q, 1)
        result = await _run_in_session(
            lambda svc: svc.sync_performance_reports(
                start_quarter=last_quarter.strftime("%Y%m%d")
            )
        )
        logger.info("[scheduler] Performance reports sync done: %d rows", result)
    except Exception as e:
        logger.error("[scheduler] Performance reports sync failed: %s", e)


async def sync_fund_flow_daily():
    """Daily fund flow sync — last 5 trading days."""
    logger.info("[scheduler] Starting fund flow daily sync...")
    try:
        result = await _run_in_session(lambda svc: svc.sync_fund_flow(lookback_days=5))
        logger.info("[scheduler] Fund flow sync done: %d rows", result)
    except Exception as e:
        logger.error("[scheduler] Fund flow sync failed: %s", e)
