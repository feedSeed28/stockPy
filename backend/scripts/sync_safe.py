"""Safe batch sync — processes stocks in small batches with pauses.
Resistant to rate limiting. Can be stopped and resumed.

Usage:
    PYTHONUTF8=1 python scripts/sync_safe.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

from app.core.database import async_session
from app.services.stock_sync_service import StockSyncService
from sqlalchemy import select
from app.models.stock_info import StockInfo
from app.models.stock_quote import StockDailyQuote
from sqlalchemy import func

BATCH_SIZE = 30   # stocks per batch
BATCH_PAUSE = 15  # seconds between batches


async def main():
    async with async_session() as db:
        svc = StockSyncService(db)

        # Get all stock codes
        result = await db.execute(select(StockInfo.code).order_by(StockInfo.code))
        all_codes = [r[0] for r in result.fetchall()]

        # Find which stocks already have data
        result = await db.execute(
            select(StockDailyQuote.stock_code).distinct()
        )
        done = {r[0] for r in result.fetchall()}
        remaining = [c for c in all_codes if c not in done]

        print(f"Total stocks: {len(all_codes)}")
        print(f"Already synced: {len(done)}")
        print(f"Remaining: {len(remaining)}")
        print(f"Batch size: {BATCH_SIZE}, pause: {BATCH_PAUSE}s")
        print("=" * 50)

        synced = 0
        failed = 0
        for i in range(0, len(remaining), BATCH_SIZE):
            batch = remaining[i:i + BATCH_SIZE]
            batch_num = i // BATCH_SIZE + 1
            total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE

            print(f"\nBatch {batch_num}/{total_batches} ({batch[0]}..{batch[-1]}, {len(batch)} stocks)")

            result = await svc.sync_kline_batch(
                period="daily",
                adjust_type="qfq",
                start_date="19900101",
                stock_codes=batch,
            )
            synced += result["total_rows"]
            failed += result["failed_stocks"]

            # Show progress
            print(f"  ✓ {len(batch) - result['failed_stocks']} stocks OK, "
                  f"{result['failed_stocks']} failed | "
                  f"Total rows: {synced:,}")

            # Pause between batches
            if i + BATCH_SIZE < len(remaining):
                print(f"  ⏳ Pausing {BATCH_PAUSE}s...")
                await asyncio.sleep(BATCH_PAUSE)

        print(f"\n{'=' * 50}")
        print(f"Complete! Rows synced: {synced:,}, stocks failed: {failed}/{len(remaining)}")


if __name__ == "__main__":
    asyncio.run(main())
