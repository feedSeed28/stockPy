"""Sync daily K-line using Sina data source (more reliable, less rate-limited).

Usage:
    PYTHONUTF8=1 python scripts/sync_sina.py
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
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
import akshare as ak
import pandas as pd
import uuid
from datetime import date, datetime

DELAY = 1.5  # seconds between requests (Sina can handle more traffic)


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


async def main():
    async with async_session() as db:
        result = await db.execute(select(StockInfo.code).order_by(StockInfo.code))
        all_codes = [r[0] for r in result.fetchall()]
        
        result = await db.execute(select(StockDailyQuote.stock_code).distinct())
        done = {r[0] for r in result.fetchall()}
        remaining = [c for c in all_codes if c not in done]
        
        print(f"Total: {len(all_codes)} | Done: {len(done)} | Remaining: {len(remaining)}")
        print(f"Delay: {DELAY}s | Est: ~{len(remaining) * DELAY / 60:.0f} min")
        print("=" * 50)
        
        ok, fail, skip = 0, 0, 0
        t0 = time.time()
        
        for i, code in enumerate(remaining):
            # Sina requires prefix: sh600000 or sz000001
            prefix = "sh" if code.startswith("6") else "sz"
            symbol = f"{prefix}{code}"
            
            try:
                # Use asyncio.to_thread to not block
                df = await asyncio.to_thread(
                    ak.stock_zh_a_daily,
                    symbol=symbol, 
                    start_date="19900101",
                    end_date="20260630",
                    adjust="qfq"
                )
                
                if df is None or df.empty:
                    skip += 1
                else:
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
                        
                        # Compute derived fields
                        amplitude = None
                        change_pct = None
                        change_amount = None
                        prev_close = None  # We'd need previous day's close
                        
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
                    
                    if rows:
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
                    if (i + 1) % 20 == 0:
                        elapsed = time.time() - t0
                        rate = (i + 1) / elapsed * 60
                        eta = (len(remaining) - i - 1) / rate
                        print(f"[{i+1}/{len(remaining)}] {code} ✓  "
                              f"ok={ok} fail={fail} skip={skip}  "
                              f"{len(rows)} bars  "
                              f"{rate:.0f} st/min  ETA {eta:.0f}min")
            
            except Exception as e:
                fail += 1
                await db.rollback()
                if (i + 1) % 10 == 0:
                    print(f"[{i+1}/{len(remaining)}] {code} ✗  "
                          f"ok={ok} fail={fail} skip={skip}  "
                          f"{str(e)[:60]}")
            
            await asyncio.sleep(DELAY)
        
        elapsed = time.time() - t0
        print(f"\nDone! ok={ok} fail={fail} skip={skip} in {elapsed/60:.1f} min")

asyncio.run(main())
