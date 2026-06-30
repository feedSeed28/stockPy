"""Sync stock list only.

Usage (from backend/ directory):
    PYTHONUTF8=1 python scripts/sync_stocks.py
"""

import asyncio

from app.core.database import async_session
from app.services.stock_sync_service import StockSyncService


async def main():
    async with async_session() as db:
        svc = StockSyncService(db)
        n = await svc.sync_stock_list()
        print(f"\nStock list synced: {n} stocks")


if __name__ == "__main__":
    asyncio.run(main())
