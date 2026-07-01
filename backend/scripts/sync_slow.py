"""Slow, sequential sync — one stock at a time with long delays.
Minimizes rate limiting. Can be interrupted and resumed.

Usage:
    PYTHONUTF8=1 python scripts/sync_slow.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')

from app.core.database import async_session
from app.models.stock_info import StockInfo
from app.models.stock_quote import StockDailyQuote
from sqlalchemy import select, func
import akshare as ak
import pandas as pd
import uuid
from datetime import date, datetime
from app.services.rate_limiter import sync_retry

DELAY = 2.0  # seconds between stocks

def _uid():
    return str(uuid.uuid4())

def _to_float(v):
    try:
        f = float(v)
        return None if pd.isna(f) else f
    except:
        return None

def _to_int(v):
    try:
        i = int(v)
        return None if pd.isna(i) else i
    except:
        return None

def _to_date(v):
    try:
        if isinstance(v, (date, datetime)):
            return v.date() if isinstance(v, datetime) else v
        s = str(v)
        if len(s) == 8 and s.isdigit():
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except:
        return None

@sync_retry(max_retries=3, base_delay=5.0, max_delay=30.0)
def fetch_one_kline(code, start_date, end_date):
    """Fetch K-line for one stock — retry on connection errors."""
    return ak.stock_zh_a_hist(
        symbol=code, period="daily", 
        start_date=start_date, end_date=end_date,
        adjust="qfq"
    )

async def main():
    async with async_session() as db:
        # Get stocks needing sync
        result = await db.execute(select(StockInfo.code).order_by(StockInfo.code))
        all_codes = [r[0] for r in result.fetchall()]
        
        result = await db.execute(select(StockDailyQuote.stock_code).distinct())
        done = {r[0] for r in result.fetchall()}
        remaining = [c for c in all_codes if c not in done]
        
        print(f"Total: {len(all_codes)} | Done: {len(done)} | Remaining: {len(remaining)}")
        print(f"Delay between stocks: {DELAY}s")
        print(f"Est. time: ~{len(remaining) * DELAY / 60:.0f} min")
        print("=" * 50)
        
        ok, fail = 0, 0
        for i, code in enumerate(remaining):
            try:
                df = fetch_one_kline(code, "19900101", "20260630")
                if df is None or df.empty:
                    fail += 1
                    if i % 50 == 0:
                        print(f"[{i+1}/{len(remaining)}] {code} — empty, skipping")
                else:
                    from sqlalchemy.dialects.mysql import insert as mysql_insert
                    rows = []
                    for _, r in df.iterrows():
                        rows.append({
                            "id": _uid(), "stock_code": code,
                            "trade_date": _to_date(r.get("日期")),
                            "adjust_type": "qfq",
                            "open": _to_float(r.get("开盘")),
                            "close": _to_float(r.get("收盘")),
                            "high": _to_float(r.get("最高")),
                            "low": _to_float(r.get("最低")),
                            "volume": _to_int(r.get("成交量")) or 0,
                            "amount": _to_float(r.get("成交额")) or 0.0,
                            "amplitude": _to_float(r.get("振幅")),
                            "change_pct": _to_float(r.get("涨跌幅")),
                            "change_amount": _to_float(r.get("涨跌额")),
                            "turnover_rate": _to_float(r.get("换手率")),
                        })
                    stmt = mysql_insert(StockDailyQuote).values(rows)
                    stmt = stmt.on_duplicate_key_update(
                        open=stmt.inserted.open, close=stmt.inserted.close,
                        high=stmt.inserted.high, low=stmt.inserted.low,
                        volume=stmt.inserted.volume, amount=stmt.inserted.amount,
                        amplitude=stmt.inserted.amplitude, change_pct=stmt.inserted.change_pct,
                        change_amount=stmt.inserted.change_amount, turnover_rate=stmt.inserted.turnover_rate,
                    )
                    await db.execute(stmt)
                    await db.commit()
                    ok += 1
                    if (i + 1) % 10 == 0:
                        print(f"[{i+1}/{len(remaining)}] {code} ✓  |  "
                              f"ok={ok} fail={fail}  |  {len(rows)} bars")
            except Exception as e:
                fail += 1
                await db.rollback()
                if (i + 1) % 10 == 0:
                    print(f"[{i+1}/{len(remaining)}] {code} ✗  |  ok={ok} fail={fail}  |  {str(e)[:60]}")
            
            await asyncio.sleep(DELAY)
        
        print(f"\nDone! ok={ok} fail={fail}")

asyncio.run(main())
