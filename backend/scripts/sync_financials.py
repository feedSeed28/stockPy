"""Sync financial indicators with anti-blocking measures.

Usage (from backend/ directory):
    PYTHONUTF8=1 python scripts/sync_financials.py

Speed: ~2s per stock, 30 stocks per batch, 25s pause between batches.
       → ~1 stock/sec average
       → ~1.5 hours for all 5200 stocks
       → Supports resume (skips already-synced stocks)
"""

import sys, os, asyncio, logging, uuid
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(message)s', datefmt='%H:%M:%S')
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

from app.core.database import async_session
from app.models.stock_info import StockInfo
from app.models.stock_financial import StockFinancialIndicator
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from app.services.safe_syncer import SafeSyncer
import akshare as ak
import pandas as pd

# ── Helpers ────────────────────────────────────────────────────────────────

def _uid(): return str(uuid.uuid4())

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

def _to_float(v):
    try:
        f = float(v)
        return None if pd.isna(f) else f
    except:
        return None

# Sina indicator column mapping
COLUMN_MAP = {
    "日期": "report_date",
    "基本每股收益": "eps_basic",
    "稀释每股收益": "eps_diluted",
    "每股净资产": "bvps",
    "每股经营现金流": "cfps",
    "净资产收益率": "roe",
    "总资产报酬率": "roa",
    "销售毛利率": "gross_margin",
    "销售净利率": "net_margin",
    "主营收入增长率": "revenue_growth",
    "净利润增长率": "profit_growth",
    "总资产增长率": "asset_growth",
    "应收账款周转率": "receivables_turnover",
    "存货周转率": "inventory_turnover",
    "总资产周转率": "asset_turnover",
    "流动比率": "current_ratio",
    "速动比率": "quick_ratio",
    "资产负债率": "debt_ratio",
    "经营活动现金流净额": "operating_cf",
    "投资活动现金流净额": "investing_cf",
    "筹资活动现金流净额": "financing_cf",
}

async def main():
    async with async_session() as db:
        # ── Get stocks to sync ──────────────────────────────────────────
        result = await db.execute(select(StockInfo.code).order_by(StockInfo.code))
        all_codes = [r[0] for r in result.fetchall()]

        result = await db.execute(
            select(StockFinancialIndicator.stock_code).distinct()
        )
        done = {r[0] for r in result.fetchall()}
        remaining = [c for c in all_codes if c not in done]

        print(f"Total: {len(all_codes)} | Done: {len(done)} | Remaining: {len(remaining)}")
        print(f"Est. time: ~{len(remaining) / 60:.0f} min")
        print(f"Strategy: 2s delay, 30/batch, 25s pause, 3 retries")
        print("=" * 50)

        async def fetch_one(code: str):
            """Fetch financial indicators for one stock."""
            return await asyncio.to_thread(
                ak.stock_financial_analysis_indicator,
                symbol=code, start_year="2018"
            )

        async def save_one(code: str, df: pd.DataFrame):
            """Save indicators to DB."""
            if df is None or df.empty:
                return
            rows = []
            for _, r in df.iterrows():
                row_data = {"id": _uid(), "stock_code": code}
                report_date = _to_date(r.get("日期"))
                if report_date is None:
                    continue
                row_data["report_date"] = report_date

                for src_col, db_col in COLUMN_MAP.items():
                    if src_col in r.index:
                        val = _to_float(r.get(src_col))
                        if val is not None:
                            row_data[db_col] = val

                # Store raw JSON for unused columns
                try:
                    row_data["raw_data"] = r.to_json()
                except:
                    pass

                rows.append(row_data)

            if rows:
                stmt = mysql_insert(StockFinancialIndicator).values(rows)
                update_cols = {c: stmt.inserted[c]
                               for c in COLUMN_MAP.values()
                               if c in StockFinancialIndicator.__table__.columns}
                update_cols["raw_data"] = stmt.inserted["raw_data"]
                stmt = stmt.on_duplicate_key_update(**update_cols)
                await db.execute(stmt)
                await db.commit()

        syncer = SafeSyncer(
            base_delay=2.0, jitter=0.5,
            batch_size=30, batch_pause_sec=25,
            max_retries=3,
        )
        result = await syncer.sync_all(
            items=remaining,
            fetch_fn=fetch_one,
            save_fn=save_one,
        )
        print(f"\nDone: {result}")


if __name__ == "__main__":
    asyncio.run(main())
