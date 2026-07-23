"""Incremental daily K-line sync using Sina source.
- Updates existing stocks with recent missing days
- Fills full history for stocks with no data

Usage:
    PYTHONUTF8=1 python scripts/sync_sina_incremental.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import time
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')

from app.core.database import async_session
from app.models.stock_info import StockInfo
from app.models.stock_quote import StockDailyQuote
from sqlalchemy import select, func
from sqlalchemy.dialects.mysql import insert as mysql_insert
import akshare as ak
import pandas as pd
import uuid
from datetime import date, datetime, timedelta

CONCURRENCY = 1  # py_mini_racer crashes with >1 thread on Windows
DELAY = 1.5  # seconds between requests per worker
LOOKBACK = 7  # days to look back for existing stocks


def uid(): return str(uuid.uuid4())

def to_float(v):
    try:
        f = float(v)
        return None if pd.isna(f) else f
    except: return None

def to_date(v):
    try:
        if isinstance(v, (date, datetime)):
            return v.date() if isinstance(v, datetime) else v
        s = str(v)
        if len(s) == 8 and s.isdigit():
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except: return None


async def fetch_sina(code: str, start_date: str, end_date: str):
    """Fetch daily K-line from Sina for a single stock."""
    prefix = "sh" if code.startswith("6") else "sz"
    symbol = f"{prefix}{code}"
    return await asyncio.to_thread(
        ak.stock_zh_a_daily,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"
    )


def build_rows(code: str, df: pd.DataFrame) -> list[dict]:
    """Convert Sina DataFrame to DB rows."""
    rows = []
    for _, r in df.iterrows():
        trade_date = to_date(r.get("date"))
        if trade_date is None:
            continue
        open_p = to_float(r.get("open"))
        close_p = to_float(r.get("close"))
        high_p = to_float(r.get("high"))
        low_p = to_float(r.get("low"))
        vol = int(to_float(r.get("volume", 0)) or 0)
        amt = to_float(r.get("amount", 0)) or 0.0
        turnover = to_float(r.get("turnover"))

        amplitude = None
        change_pct = None
        change_amount = None

        if open_p and close_p and high_p and low_p:
            if open_p != 0:
                change_pct = round((close_p - open_p) / open_p * 100, 3)
            change_amount = round(close_p - open_p, 3) if close_p and open_p else None
            if open_p != 0:
                amplitude = round((high_p - low_p) / open_p * 100, 3)

        rows.append({
            "id": uid(), "stock_code": code,
            "trade_date": trade_date,
            "adjust_type": "qfq",
            "open": open_p, "close": close_p,
            "high": high_p, "low": low_p,
            "volume": vol, "amount": amt,
            "amplitude": amplitude,
            "change_pct": change_pct,
            "change_amount": change_amount,
            "turnover_rate": turnover,
        })
    return rows


async def main():
    today_str = date.today().strftime("%Y%m%d")
    lookback_start = (date.today() - timedelta(days=LOOKBACK)).strftime("%Y%m%d")

    async with async_session() as db:
        # Get all stocks
        result = await db.execute(select(StockInfo.code).order_by(StockInfo.code))
        all_codes = [r[0] for r in result.fetchall()]

        # Get stocks WITH daily data and their latest date
        result = await db.execute(
            select(StockDailyQuote.stock_code, func.max(StockDailyQuote.trade_date))
            .group_by(StockDailyQuote.stock_code)
        )
        existing = {r[0]: r[1] for r in result.fetchall()}

        # Split: stocks needing incremental vs full history
        incremental = []  # (code, start_date) — has data, needs recent days
        full_sync = []    # code — no data at all
        already_fresh = 0

        for code in all_codes:
            if code in existing:
                last_date = existing[code]
                if last_date >= date.today():
                    already_fresh += 1
                else:
                    # Fetch from last_date - LOOKBACK to today (with overlap)
                    start = (last_date - timedelta(days=LOOKBACK)).strftime("%Y%m%d")
                    incremental.append((code, start))
            else:
                full_sync.append(code)

        print(f"Total stocks: {len(all_codes)}")
        print(f"  Already fresh (up to today): {already_fresh}")
        print(f"  Need incremental update: {len(incremental)}")
        print(f"  Need full sync (no data): {len(full_sync)}")
        print(f"Concurrency: {CONCURRENCY} | Delay: {DELAY}s")
        print("=" * 50)

        sem = asyncio.Semaphore(CONCURRENCY)
        ok = 0
        fail = 0
        total_rows = 0
        t0 = time.time()
        processed = 0
        last_log = [0]  # mutable for closure

        async def process_one(code: str, start_date: str, label: str):
            nonlocal ok, fail, total_rows, processed
            async with sem:
                try:
                    df = await fetch_sina(code, start_date, today_str)
                    if df is None or df.empty:
                        return

                    rows = build_rows(code, df)
                    if rows:
                        stmt = mysql_insert(StockDailyQuote).values(rows)
                        stmt = stmt.on_duplicate_key_update(
                            open=stmt.inserted.open, close=stmt.inserted.close,
                            high=stmt.inserted.high, low=stmt.inserted.low,
                            volume=stmt.inserted.volume, amount=stmt.inserted.amount,
                            amplitude=stmt.inserted.amplitude,
                            change_pct=stmt.inserted.change_pct,
                            change_amount=stmt.inserted.change_amount,
                            turnover_rate=stmt.inserted.turnover_rate,
                        )
                        await db.execute(stmt)
                        await db.commit()
                        total_rows += len(rows)
                    ok += 1
                except Exception as e:
                    fail += 1
                    try:
                        await db.rollback()
                    except:
                        pass

                processed += 1
                if processed % 50 == 0 or processed == 1:
                    elapsed = time.time() - t0
                    rate = processed / elapsed * 60
                    eta = (len(incremental) + len(full_sync) - processed) / rate if rate > 0 else 0
                    print(f"[{processed}/{len(incremental) + len(full_sync)}] "
                          f"{label} ok={ok} fail={fail} rows={total_rows} "
                          f"{rate:.0f} st/min ETA {eta:.0f}min")

                await asyncio.sleep(DELAY)

        # Process incremental first (faster, fills the gap)
        tasks = [process_one(code, start, "incr") for code, start in incremental]
        tasks += [process_one(code, "19900101", "full") for code in full_sync]
        await asyncio.gather(*tasks)

        elapsed = time.time() - t0
        print(f"\nDone! ok={ok} fail={fail} rows={total_rows} in {elapsed/60:.1f} min")


asyncio.run(main())
