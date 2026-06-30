"""Incremental daily K-line sync.

Usage (from backend/ directory):
    PYTHONUTF8=1 python scripts/sync_daily.py
"""

import asyncio

from app.core.database import async_session
from app.services.stock_sync_service import StockSyncService


async def main():
    async with async_session() as db:
        svc = StockSyncService(db)
        n = await svc.sync_daily_incremental(adjust_type="qfq", lookback_days=5)
        print(f"\nDaily incremental sync done: {n} rows")


if __name__ == "__main__":
    asyncio.run(main())
