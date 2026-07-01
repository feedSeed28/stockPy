"""AKShare → MySQL data sync service.

Handles full and incremental sync for all A-stock data tables.
AKShare calls are synchronous — wrapped with asyncio.to_thread to avoid
blocking the event loop.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Any

import akshare as ak
import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_info import StockInfo
from app.models.stock_quote import StockDailyQuote, StockWeeklyQuote, StockMonthlyQuote
from app.models.stock_financial import StockFinancialIndicator, StockPerformanceReport
from app.models.stock_forecast import StockProfitForecast
from app.models.stock_fund_flow import StockFundFlowDaily
from app.models.stock_board import StockBoardInfo, StockBoardMember
from app.models.sync_status import SyncStatus
from app.services.rate_limiter import async_retry, throttle

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────

BATCH_SIZE = 200  # rows per INSERT batch
SYNC_CONCURRENCY = 2  # max concurrent stock-level sync tasks (keep low to avoid rate limits)


# ── Helpers ───────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.utcnow()


def _uid() -> str:
    return str(uuid.uuid4())


def _to_float(val: Any) -> float | None:
    """Safe float cast — returns None for NaN/inf."""
    if val is None:
        return None
    try:
        f = float(val)
        if pd.isna(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _to_int(val: Any) -> int | None:
    if val is None:
        return None
    try:
        i = int(val)
        if pd.isna(i):
            return None
        return i
    except (ValueError, TypeError):
        return None


def _to_date(val: Any) -> date | None:
    """Parse a date from various formats."""
    if val is None:
        return None
    try:
        if isinstance(val, date):
            return val
        if isinstance(val, datetime):
            return val.date()
        if isinstance(val, pd.Timestamp):
            return val.date()
        s = str(val)
        # Try YYYYMMDD
        if len(s) == 8 and s.isdigit():
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        # Try YYYY-MM-DD
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _build_code(s: Any) -> str:
    """Normalize stock code to 6-digit string."""
    return str(s).zfill(6)


def _exchange_from_code(code: str) -> str:
    """Derive exchange from stock code prefix."""
    if code.startswith("6"):
        return "SH"
    if code.startswith(("0", "3")):
        return "SZ"
    if code.startswith(("8", "4")):
        return "BJ"
    return "SZ"


def _board_type_from_code(code: str) -> str | None:
    """Derive board type from stock code."""
    if code.startswith("688"):
        return "科创板"
    if code.startswith("300") or code.startswith("301"):
        return "创业板"
    if code.startswith(("8", "4")):
        return "北交所"
    return "主板"


# ── Batch Upsert ──────────────────────────────────────────────────────────


async def _batch_upsert(
    db: AsyncSession,
    rows: list[dict[str, Any]],
    model_cls: type,
    unique_cols: list[str],
) -> int:
    """Batch INSERT ON DUPLICATE KEY UPDATE.

    Returns number of rows written.
    """
    if not rows:
        return 0

    for i in range(0, len(rows), BATCH_SIZE):
        batch = rows[i : i + BATCH_SIZE]
        stmt = mysql_insert(model_cls).values(batch)
        # On duplicate key, update all columns except the unique ones
        update_cols = {
            c.name: stmt.inserted[c.name]
            for c in model_cls.__table__.columns
            if c.name not in unique_cols and c.name != "id"
        }
        stmt = stmt.on_duplicate_key_update(**update_cols)
        await db.execute(stmt)

    await db.commit()
    return len(rows)


# ── Sync Status Helpers ───────────────────────────────────────────────────


async def _get_last_data_date(db: AsyncSession, table_name: str) -> date | None:
    result = await db.execute(
        select(SyncStatus.last_data_date).where(SyncStatus.table_name == table_name)
    )
    return result.scalar_one_or_none()


async def _update_sync_status(
    db: AsyncSession,
    table_name: str,
    last_data_date: date | None = None,
    row_count: int | None = None,
    status: str = "idle",
    error_message: str | None = None,
):
    row = await db.get(SyncStatus, table_name)
    if row is None:
        row = SyncStatus(table_name=table_name)
        db.add(row)
    row.status = status
    row.last_sync_time = _now()
    if last_data_date is not None:
        row.last_data_date = last_data_date
    if row_count is not None:
        row.row_count = row_count
    if error_message is not None:
        row.error_message = error_message
    await db.commit()


# ═══════════════════════════════════════════════════════════════════════════
# StockSyncService
# ═══════════════════════════════════════════════════════════════════════════


class StockSyncService:
    """Orchestrates AKShare → MySQL data synchronization."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 1. Stock List ──────────────────────────────────────────────────

    async def sync_stock_list(self) -> int:
        """Fetch full A-stock list from AKShare → stock_info table."""
        logger.info("Syncing stock list...")
        await _update_sync_status(self.db, "stock_info", status="syncing")

        try:
            df: pd.DataFrame = await asyncio.to_thread(ak.stock_info_a_code_name)
        except Exception:
            await _update_sync_status(
                self.db, "stock_info", status="error", error_message="AKShare fetch failed"
            )
            raise

        rows = []
        for _, r in df.iterrows():
            code = _build_code(r.get("code", ""))
            rows.append({
                "code": code,
                "name": str(r.get("name", "")),
                "exchange": _exchange_from_code(code),
                "board_type": _board_type_from_code(code),
                "is_active": True,
            })

        count = await _batch_upsert(self.db, rows, StockInfo, ["code"])
        await _update_sync_status(self.db, "stock_info", last_data_date=date.today(), row_count=count)
        logger.info("Stock list synced: %d stocks.", count)
        return count

    # ── 2. K-line (Daily / Weekly / Monthly) ───────────────────────────

    async def sync_kline_batch(
        self,
        period: str = "daily",
        adjust_type: str = "qfq",
        start_date: str = "19900101",
        end_date: str | None = None,
        stock_codes: list[str] | None = None,
    ) -> dict[str, int]:
        """Sync K-line for multiple stocks concurrently.

        period: daily / weekly / monthly
        adjust_type: qfq / hfq / none
        """
        model_map = {
            "daily": StockDailyQuote,
            "weekly": StockWeeklyQuote,
            "monthly": StockMonthlyQuote,
        }
        table_map = {
            "daily": "stock_daily_quote",
            "weekly": "stock_weekly_quote",
            "monthly": "stock_monthly_quote",
        }
        model_cls = model_map[period]
        table_name = table_map[period]
        unique_cols = ["stock_code", "trade_date", "adjust_type"]

        if end_date is None:
            end_date = date.today().strftime("%Y%m%d")

        # Resolve stock codes
        if stock_codes is None:
            result = await self.db.execute(select(StockInfo.code))
            stock_codes = [r[0] for r in result.fetchall()]

        logger.info("Syncing %s K-line for %d stocks...", period, len(stock_codes))
        await _update_sync_status(self.db, table_name, status="syncing")

        sem = asyncio.Semaphore(SYNC_CONCURRENCY)
        total = 0
        errors = 0

        async def _sync_one(code: str) -> int:
            nonlocal errors
            async with sem:
                try:
                    return await self._sync_single_kline(
                        code, period, adjust_type, start_date, end_date, model_cls, unique_cols
                    )
                except Exception as e:
                    logger.error("K-line sync failed for %s: %s", code, e)
                    errors += 1
                    return 0

        tasks = [_sync_one(c) for c in stock_codes]
        results = await asyncio.gather(*tasks)
        total = sum(results)

        await _update_sync_status(
            self.db, table_name, last_data_date=_to_date(end_date), row_count=total,
            status="error" if errors else "idle",
            error_message=f"{errors} stocks failed" if errors else None,
        )
        logger.info("%s K-line synced: %d rows, %d failed.", period, total, errors)
        return {"total_rows": total, "failed_stocks": errors}

    async def _sync_single_kline(
        self,
        code: str,
        period: str,
        adjust_type: str,
        start_date: str,
        end_date: str,
        model_cls: type,
        unique_cols: list[str],
        max_retries: int = 3,
    ) -> int:
        """Sync K-line for a single stock, with retry on connection errors."""
        last_err = None
        for attempt in range(max_retries + 1):
            try:
                await throttle()
                df: pd.DataFrame = await asyncio.to_thread(
                    ak.stock_zh_a_hist,
                    symbol=code,
                    period=period,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust_type,
                )
                if df.empty:
                    return 0

                rows = []
                for _, r in df.iterrows():
                    rows.append({
                        "id": _uid(),
                        "stock_code": code,
                        "trade_date": _to_date(r.get("日期")),
                        "adjust_type": adjust_type,
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

                return await _batch_upsert(self.db, rows, model_cls, unique_cols)

            except Exception as e:
                last_err = e
                if attempt < max_retries:
                    delay = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning("K-line retry %d/%d for %s: %s", attempt + 1, max_retries, code, e)
                    await asyncio.sleep(delay)
                else:
                    logger.error("K-line failed for %s after %d retries: %s", code, max_retries, last_err)

        raise last_err

    async def sync_daily_incremental(
        self, adjust_type: str = "qfq", lookback_days: int = 5
    ) -> int:
        """Incremental daily K-line sync: fetch last N days for all stocks."""
        last_date = await _get_last_data_date(self.db, "stock_daily_quote")
        if last_date is None:
            logger.warning("No previous sync found — run full sync first")
            return 0

        start = (last_date - timedelta(days=lookback_days)).strftime("%Y%m%d")
        end = date.today().strftime("%Y%m%d")

        result = await self.sync_kline_batch(
            period="daily", adjust_type=adjust_type, start_date=start, end_date=end
        )
        return result["total_rows"]

    # ── 3. Performance Reports ─────────────────────────────────────────

    async def sync_performance_reports(
        self, start_quarter: str = "20100331"
    ) -> int:
        """Sync quarterly performance reports.

        start_quarter: YYYYMMDD format, e.g. "20100331"
        """
        logger.info("Syncing performance reports from %s...", start_quarter)
        await _update_sync_status(self.db, "stock_performance_report", status="syncing")

        # Generate quarter-end dates from start_quarter to now
        quarters = self._generate_quarters(start_quarter)
        total = 0

        for q in quarters:
            try:
                await throttle()
                df: pd.DataFrame = await asyncio.to_thread(ak.stock_yjbb_em, date=q)
                if df.empty:
                    continue

                rows = []
                for _, r in df.iterrows():
                    rows.append({
                        "id": _uid(),
                        "stock_code": _build_code(r.get("股票代码")),
                        "stock_name": str(r.get("股票简称", "")),
                        "report_date": _to_date(q),
                        "eps": _to_float(r.get("每股收益")),
                        "revenue": _to_float(r.get("营业总收入-营业总收入")),
                        "revenue_yoy": _to_float(r.get("营业总收入-同比增长")),
                        "revenue_qoq": _to_float(r.get("营业总收入-季度环比增长")),
                        "net_profit": _to_float(r.get("净利润-净利润")),
                        "net_profit_yoy": _to_float(r.get("净利润-同比增长")),
                        "net_profit_qoq": _to_float(r.get("净利润-季度环比增长")),
                        "bvps": _to_float(r.get("每股净资产")),
                        "roe": _to_float(r.get("净资产收益率")),
                        "cfps": _to_float(r.get("每股经营现金流量")),
                        "gross_margin": _to_float(r.get("销售毛利率")),
                        "industry": str(r.get("所处行业", "")) if r.get("所处行业") else None,
                        "announce_date": _to_date(r.get("最新公告日期")),
                    })

                count = await _batch_upsert(
                    self.db, rows, StockPerformanceReport, ["stock_code", "report_date"]
                )
                total += count
                logger.debug("  Quarter %s: %d reports", q, count)

            except Exception as e:
                logger.error("Performance report sync failed for %s: %s", q, e)

        await _update_sync_status(
            self.db, "stock_performance_report",
            last_data_date=_to_date(quarters[-1]) if quarters else None,
            row_count=total,
        )
        logger.info("Performance reports synced: %d rows.", total)
        return total

    # ── 4. Financial Indicators ────────────────────────────────────────

    async def sync_financial_indicators(
        self, stock_codes: list[str] | None = None
    ) -> int:
        """Sync detailed financial indicators for each stock."""
        logger.info("Syncing financial indicators...")
        await _update_sync_status(self.db, "stock_financial_indicator", status="syncing")

        if stock_codes is None:
            result = await self.db.execute(select(StockInfo.code))
            stock_codes = [r[0] for r in result.fetchall()]

        sem = asyncio.Semaphore(SYNC_CONCURRENCY)
        total = 0

        async def _sync_one(code: str) -> int:
            async with sem:
                try:
                    await throttle()
                    df: pd.DataFrame = await asyncio.to_thread(
                        ak.stock_financial_analysis_indicator, symbol=code, start_year="1990"
                    )
                    if df.empty:
                        return 0

                    rows = []
                    for _, r in df.iterrows():
                        row_dict = {
                            "id": _uid(),
                            "stock_code": code,
                            "report_date": _to_date(r.get("日期")),
                            "eps_basic": _to_float(r.get("基本每股收益")),
                            "eps_diluted": _to_float(r.get("稀释每股收益")),
                            "bvps": _to_float(r.get("每股净资产")),
                            "cfps": _to_float(r.get("每股经营现金流")),
                            "roe": _to_float(r.get("净资产收益率")),
                            "roa": _to_float(r.get("总资产报酬率")),
                            "gross_margin": _to_float(r.get("销售毛利率")),
                            "net_margin": _to_float(r.get("销售净利率")),
                            "revenue_growth": _to_float(r.get("主营收入增长率")),
                            "profit_growth": _to_float(r.get("净利润增长率")),
                            "asset_growth": _to_float(r.get("总资产增长率")),
                            "receivables_turnover": _to_float(r.get("应收账款周转率")),
                            "inventory_turnover": _to_float(r.get("存货周转率")),
                            "asset_turnover": _to_float(r.get("总资产周转率")),
                            "current_ratio": _to_float(r.get("流动比率")),
                            "quick_ratio": _to_float(r.get("速动比率")),
                            "debt_ratio": _to_float(r.get("资产负债率")),
                            "operating_cf": _to_float(r.get("经营活动现金流净额")),
                            "investing_cf": _to_float(r.get("投资活动现金流净额")),
                            "financing_cf": _to_float(r.get("筹资活动现金流净额")),
                            "raw_data": r.to_json() if hasattr(r, "to_json") else str(r.to_dict()),
                        }
                        rows.append(row_dict)

                    return await _batch_upsert(
                        self.db, rows, StockFinancialIndicator, ["stock_code", "report_date"]
                    )
                except Exception as e:
                    logger.error("Financial indicator sync failed for %s: %s", code, e)
                    return 0

        tasks = [_sync_one(c) for c in stock_codes]
        results = await asyncio.gather(*tasks)
        total = sum(results)

        await _update_sync_status(
            self.db, "stock_financial_indicator", row_count=total,
        )
        logger.info("Financial indicators synced: %d rows.", total)
        return total

    # ── 5. Profit Forecasts ────────────────────────────────────────────

    async def sync_profit_forecasts(self) -> int:
        """Sync analyst profit forecasts for all A-stocks."""
        logger.info("Syncing profit forecasts...")
        await _update_sync_status(self.db, "stock_profit_forecast", status="syncing")

        try:
            await throttle()
            df: pd.DataFrame = await asyncio.to_thread(ak.stock_profit_forecast_em, symbol="")
        except Exception:
            await _update_sync_status(
                self.db, "stock_profit_forecast", status="error", error_message="AKShare fetch failed"
            )
            raise

        rows = []
        for _, r in df.iterrows():
            rows.append({
                "id": _uid(),
                "stock_code": _build_code(r.get("代码")),
                "stock_name": str(r.get("名称", "")),
                "research_report_num": _to_int(r.get("研报数")),
                "rating_buy": _to_int(r.get("机构投资评级(近六个月)-买入")),
                "rating_overweight": _to_int(r.get("机构投资评级(近六个月)-增持")),
                "rating_neutral": _to_int(r.get("机构投资评级(近六个月)-中性")),
                "rating_underweight": _to_int(r.get("机构投资评级(近六个月)-减持")),
                "rating_sell": _to_int(r.get("机构投资评级(近六个月)-卖出")),
                "forecast_eps_year1": _to_float(r.get(r.columns[12] if len(r.columns) > 12 else None)),
                "forecast_eps_year2": _to_float(r.get(r.columns[16] if len(r.columns) > 16 else None)),
                "forecast_eps_year3": _to_float(r.get(r.columns[20] if len(r.columns) > 20 else None)),
                "forecast_eps_year4": _to_float(r.get(r.columns[24] if len(r.columns) > 24 else None)),
                "forecast_np_year1": _to_float(r.get(r.columns[13] if len(r.columns) > 13 else None)),
                "forecast_np_year2": _to_float(r.get(r.columns[17] if len(r.columns) > 17 else None)),
                "forecast_np_year3": _to_float(r.get(r.columns[21] if len(r.columns) > 21 else None)),
                "forecast_np_year4": _to_float(r.get(r.columns[25] if len(r.columns) > 25 else None)),
                "target_avg_price": _to_float(r.get(r.columns[28] if len(r.columns) > 28 else None)),
                "updated_date": date.today(),
            })

        count = await _batch_upsert(
            self.db, rows, StockProfitForecast, ["stock_code", "updated_date"]
        )
        await _update_sync_status(
            self.db, "stock_profit_forecast", last_data_date=date.today(), row_count=count,
        )
        logger.info("Profit forecasts synced: %d stocks.", count)
        return count

    # ── 6. Fund Flow ───────────────────────────────────────────────────

    async def sync_fund_flow(
        self, stock_codes: list[str] | None = None, lookback_days: int = 30
    ) -> int:
        """Sync daily fund flow data."""
        logger.info("Syncing fund flow data...")
        await _update_sync_status(self.db, "stock_fund_flow_daily", status="syncing")

        if stock_codes is None:
            result = await self.db.execute(select(StockInfo.code))
            stock_codes = [r[0] for r in result.fetchall()]

        sem = asyncio.Semaphore(SYNC_CONCURRENCY)
        total = 0

        async def _sync_one(code: str) -> int:
            async with sem:
                try:
                    market = "sh" if code.startswith("6") else "sz"
                    await throttle()
                    df: pd.DataFrame = await asyncio.to_thread(
                        ak.stock_individual_fund_flow, stock=code, market=market
                    )
                    if df.empty:
                        return 0

                    rows = []
                    for _, r in df.iterrows():
                        rows.append({
                            "id": _uid(),
                            "stock_code": code,
                            "trade_date": _to_date(r.get("日期")),
                            "close": _to_float(r.get("收盘价")),
                            "change_pct": _to_float(r.get("涨跌幅")),
                            "main_net_inflow": _to_float(r.get("主力净流入-净额")),
                            "main_net_ratio": _to_float(r.get("主力净流入-净占比")),
                            "huge_net_inflow": _to_float(r.get("超大单净流入-净额")),
                            "huge_net_ratio": _to_float(r.get("超大单净流入-净占比")),
                            "large_net_inflow": _to_float(r.get("大单净流入-净额")),
                            "large_net_ratio": _to_float(r.get("大单净流入-净占比")),
                            "medium_net_inflow": _to_float(r.get("中单净流入-净额")),
                            "medium_net_ratio": _to_float(r.get("中单净流入-净占比")),
                            "small_net_inflow": _to_float(r.get("小单净流入-净额")),
                            "small_net_ratio": _to_float(r.get("小单净流入-净占比")),
                        })
                    return await _batch_upsert(
                        self.db, rows, StockFundFlowDaily, ["stock_code", "trade_date"]
                    )
                except Exception as e:
                    logger.error("Fund flow sync failed for %s: %s", code, e)
                    return 0

        tasks = [_sync_one(c) for c in stock_codes]
        results = await asyncio.gather(*tasks)
        total = sum(results)

        await _update_sync_status(
            self.db, "stock_fund_flow_daily", last_data_date=date.today(), row_count=total,
        )
        logger.info("Fund flow synced: %d rows.", total)
        return total

    # ── 7. Boards ──────────────────────────────────────────────────────

    async def sync_boards(self) -> dict[str, int]:
        """Sync industry and concept boards + member stocks."""
        logger.info("Syncing boards...")
        await _update_sync_status(self.db, "stock_board_info", status="syncing")

        board_count = 0
        member_count = 0

        # Industry boards (东方财富)
        try:
            await throttle()
            df_ind = await asyncio.to_thread(ak.stock_board_industry_name_em)
            board_count += await self._sync_board_batch(df_ind, "industry", "em")
        except Exception as e:
            logger.error("Industry board sync failed: %s", e)

        # Concept boards (东方财富)
        try:
            await throttle()
            df_con = await asyncio.to_thread(ak.stock_board_concept_name_em)
            board_count += await self._sync_board_batch(df_con, "concept", "em")
        except Exception as e:
            logger.error("Concept board sync failed: %s", e)

        await _update_sync_status(
            self.db, "stock_board_info", last_data_date=date.today(), row_count=board_count,
        )
        logger.info("Boards synced: %d boards, %d members.", board_count, member_count)
        return {"boards": board_count, "members": member_count}

    async def _sync_board_batch(
        self, df: pd.DataFrame, board_type: str, source: str
    ) -> int:
        """Sync a batch of boards."""
        rows = []
        for _, r in df.iterrows():
            rows.append({
                "id": _uid(),
                "board_code": _build_code(r.get("板块代码", r.iloc[0])),
                "board_name": str(r.get("板块名称", r.iloc[1])),
                "board_type": board_type,
                "source": source,
            })
        return await _batch_upsert(
            self.db, rows, StockBoardInfo, ["board_name", "board_type", "source"]
        )

    # ── 8. Full Initial Sync ───────────────────────────────────────────

    async def full_sync(self) -> dict[str, Any]:
        """Run a complete initial sync (all tables, full history).

        Order: stock_info → kline → performance → financials → forecast → fund_flow → boards
        """
        results: dict[str, Any] = {}

        # 1. Stock list
        results["stock_info"] = await self.sync_stock_list()

        # 2. Daily K-line (前复权, all history)
        results["daily_kline"] = await self.sync_kline_batch(
            period="daily", adjust_type="qfq", start_date="19900101"
        )

        # 3. Weekly K-line
        results["weekly_kline"] = await self.sync_kline_batch(
            period="weekly", adjust_type="qfq", start_date="19900101"
        )

        # 4. Monthly K-line
        results["monthly_kline"] = await self.sync_kline_batch(
            period="monthly", adjust_type="qfq", start_date="19900101"
        )

        # 5. Performance reports
        results["performance_reports"] = await self.sync_performance_reports()

        # 6. Financial indicators
        results["financial_indicators"] = await self.sync_financial_indicators()

        # 7. Profit forecasts
        results["profit_forecasts"] = await self.sync_profit_forecasts()

        # 8. Fund flow
        results["fund_flow"] = await self.sync_fund_flow()

        # 9. Boards
        results["boards"] = await self.sync_boards()

        logger.info("Full sync complete: %s", results)
        return results

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _generate_quarters(start: str) -> list[str]:
        """Generate quarter-end date strings from start to now."""
        y = int(start[:4])
        m = int(start[4:6])
        start_quarter = date(y, m, 1)
        today = date.today()

        quarters = []
        d = start_quarter
        while d <= today:
            # Quarter end months: 3, 6, 9, 12
            q_month = ((d.month - 1) // 3 + 1) * 3
            q_end = date(d.year, q_month, 1) + timedelta(days=31)
            q_end = q_end.replace(day=1) - timedelta(days=1)
            quarters.append(q_end.strftime("%Y%m%d"))
            # Next quarter
            d = (q_end.replace(day=28) + timedelta(days=5)).replace(day=1)
        return quarters
