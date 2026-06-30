"""Run a full historical data sync — all tables, all A-stocks.

Usage (from backend/ directory):
    PYTHONUTF8=1 python scripts/sync_full.py
    # or via Makefile from project root: make sync-full
"""

import asyncio

from app.core.database import async_session
from app.services.stock_sync_service import StockSyncService


async def main():
    async with async_session() as db:
        svc = StockSyncService(db)
        result = await svc.full_sync()
        print("\n=== Full Sync Complete ===")
        for table, info in result.items():
            print(f"  {table}: {info}")


if __name__ == "__main__":
    asyncio.run(main())
