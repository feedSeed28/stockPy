"""Stock API endpoints — /api/v1/stocks/*.

Pattern: DB-first, with live AKShare fallback when local data is empty.
The LiveFetcher ensures dedup, timeout, and concurrent request limiting.
"""

import asyncio
import logging
from datetime import date, timedelta
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.stock_info import StockInfo
from app.models.stock_quote import StockDailyQuote
from app.schemas.common import ApiResponse
from app.services import stock_query_service as qs
from app.services.live_fetcher import live_fetcher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("")
async def list_stocks(
    exchange: Optional[str] = Query(None, description="交易所 SH/SZ/BJ"),
    board_type: Optional[str] = Query(None, description="板块类型 主板/科创板/创业板/北交所"),
    is_active: Optional[bool] = Query(True, description="是否仍上市"),
    keyword: Optional[str] = Query(None, description="搜索关键词 代码/名称"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    db: AsyncSession = Depends(get_db),
):
    """A股股票列表 — 分页，支持按交易所/板块/关键词筛选."""
    items, total = await qs.list_stocks(
        db, exchange=exchange, board_type=board_type,
        is_active=is_active, keyword=keyword, page=page, page_size=page_size,
    )
    return ApiResponse(data={
        "items": [{"code": s.code, "name": s.name, "exchange": s.exchange,
                   "board_type": s.board_type, "industry": s.industry,
                   "is_active": s.is_active, "listed_date": str(s.listed_date) if s.listed_date else None}
                  for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/industries")
async def get_stock_industries(
    codes: str = Query(..., description="Comma-separated stock codes"),
    db: AsyncSession = Depends(get_db),
):
    """Batch lookup stock industry names from local stock_info."""
    parsed_codes = []
    seen = set()
    for raw in codes.split(","):
        code = raw.strip().zfill(6)
        if len(code) == 6 and code.isdigit() and code not in seen:
            parsed_codes.append(code)
            seen.add(code)
        if len(parsed_codes) >= 500:
            break

    if not parsed_codes:
        return ApiResponse(data={"items": [], "map": {}})

    result = await db.execute(
        select(StockInfo.code, StockInfo.industry).where(StockInfo.code.in_(parsed_codes))
    )
    items = [
        {"code": r.code, "industry": r.industry or ""}
        for r in result.all()
    ]
    return ApiResponse(data={
        "items": items,
        "map": {item["code"]: item["industry"] for item in items},
    })


@router.get("/{code}")
async def get_stock(code: str, db: AsyncSession = Depends(get_db)):
    """单只股票基本信息."""
    s = await qs.get_stock(db, code)
    if s is None:
        return ApiResponse(code=404, message=f"Stock {code} not found")
    return ApiResponse(data={
        "code": s.code, "name": s.name, "exchange": s.exchange,
        "board_type": s.board_type, "industry": s.industry,
        "is_active": s.is_active, "listed_date": str(s.listed_date) if s.listed_date else None,
    })


@router.get("/{code}/daily")
async def get_daily_kline(
    code: str,
    adjust_type: str = Query("qfq", description="复权类型 qfq/hfq/none"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """某只股票的日K线 — 分页，支持日期范围与复权类型."""
    items, total = await qs.get_kline(
        db, code, period="daily", adjust_type=adjust_type,
        start_date=start_date, end_date=end_date, page=page, page_size=page_size,
    )

    # 总数为0 或 数据过期 → 触发实时拉取
    is_stale = total > 0 and not await _kline_is_fresh(db, code, "daily", adjust_type)
    if total == 0 or is_stale:
        try:
            _, from_live = await live_fetcher.fetch_or_live(
                db,
                cache_key=f"kline:daily:{code}:{adjust_type}",
                db_query_fn=lambda d: _kline_count(d, code, "daily", adjust_type),
                live_fetch_fn=lambda: _fetch_kline_single(code, "daily", adjust_type),
                save_fn=lambda d, df: _save_kline_single(d, code, "daily", adjust_type, df),
            )
            if from_live:
                items, total = await qs.get_kline(
                    db, code, period="daily", adjust_type=adjust_type,
                    start_date=start_date, end_date=end_date, page=page, page_size=page_size,
                )
        except Exception as e:
            logger.warning("Live K-line fallback failed for %s: %s", code, e)

    return ApiResponse(data={
        "items": [_quote_to_dict(q) for q in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/{code}/weekly")
async def get_weekly_kline(
    code: str,
    adjust_type: str = Query("qfq", description="复权类型 qfq/hfq/none"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """某只股票的周K线."""
    items, total = await qs.get_kline(
        db, code, period="weekly", adjust_type=adjust_type,
        start_date=start_date, end_date=end_date, page=page, page_size=page_size,
    )

    if total == 0:
        try:
            _, from_live = await live_fetcher.fetch_or_live(
                db,
                cache_key=f"kline:weekly:{code}:{adjust_type}",
                db_query_fn=lambda d: _kline_count(d, code, "weekly", adjust_type),
                live_fetch_fn=lambda: _fetch_kline_single(code, "weekly", adjust_type),
                save_fn=lambda d, df: _save_kline_single(d, code, "weekly", adjust_type, df),
            )
            if from_live:
                items, total = await qs.get_kline(
                    db, code, period="weekly", adjust_type=adjust_type,
                    start_date=start_date, end_date=end_date, page=page, page_size=page_size,
                )
        except Exception as e:
            logger.warning("Live weekly K-line fallback failed for %s: %s", code, e)

    return ApiResponse(data={
        "items": [_quote_to_dict(q) for q in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/{code}/monthly")
async def get_monthly_kline(
    code: str,
    adjust_type: str = Query("qfq", description="复权类型 qfq/hfq/none"),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """某只股票的月K线."""
    items, total = await qs.get_kline(
        db, code, period="monthly", adjust_type=adjust_type,
        start_date=start_date, end_date=end_date, page=page, page_size=page_size,
    )

    if total == 0:
        try:
            _, from_live = await live_fetcher.fetch_or_live(
                db,
                cache_key=f"kline:monthly:{code}:{adjust_type}",
                db_query_fn=lambda d: _kline_count(d, code, "monthly", adjust_type),
                live_fetch_fn=lambda: _fetch_kline_single(code, "monthly", adjust_type),
                save_fn=lambda d, df: _save_kline_single(d, code, "monthly", adjust_type, df),
            )
            if from_live:
                items, total = await qs.get_kline(
                    db, code, period="monthly", adjust_type=adjust_type,
                    start_date=start_date, end_date=end_date, page=page, page_size=page_size,
                )
        except Exception as e:
            logger.warning("Live monthly K-line fallback failed for %s: %s", code, e)

    return ApiResponse(data={
        "items": [_quote_to_dict(q) for q in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.get("/{code}/kline-range")
async def get_kline_range(
    code: str,
    period: str = Query("daily", description="daily/weekly/monthly"),
    adjust_type: str = Query("qfq"),
    db: AsyncSession = Depends(get_db),
):
    """获取某只股票K线数据的日期范围."""
    result = await qs.get_kline_date_range(db, code, period=period, adjust_type=adjust_type)
    return ApiResponse(data=result)


@router.get("/{code}/performance")
async def get_performance(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """业绩报表 — 季度数据."""
    items, total = await qs.get_performance_reports(db, code, page=page, page_size=page_size)

    if total == 0:
        try:
            _, from_live = await live_fetcher.fetch_or_live(
                db,
                cache_key=f"performance:{code}",
                db_query_fn=lambda d: _perf_count(d, code),
                live_fetch_fn=lambda: _fetch_performance_single(code),
                save_fn=lambda d, df: _save_performance_single(d, code, df),
            )
            if from_live:
                items, total = await qs.get_performance_reports(
                    db, code, page=page, page_size=page_size
                )
        except Exception as e:
            logger.warning("Live performance fallback failed for %s: %s", code, e)

    return ApiResponse(data={
        "items": [
            {
                "report_date": str(r.report_date), "eps": r.eps, "revenue": r.revenue,
                "revenue_yoy": r.revenue_yoy, "revenue_qoq": r.revenue_qoq,
                "net_profit": r.net_profit, "net_profit_yoy": r.net_profit_yoy,
                "net_profit_qoq": r.net_profit_qoq,
                "bvps": r.bvps, "roe": r.roe, "cfps": r.cfps,
                "gross_margin": r.gross_margin, "industry": r.industry,
            }
            for r in items
        ],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/{code}/financials")
async def get_financials(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """详细财务指标."""
    items, total = await qs.get_financial_indicators(db, code, page=page, page_size=page_size)

    if total == 0:
        try:
            _, from_live = await live_fetcher.fetch_or_live(
                db,
                cache_key=f"financials:{code}",
                db_query_fn=lambda d: _fin_count(d, code),
                live_fetch_fn=lambda: _fetch_financials_single(code),
                save_fn=lambda d, df: _save_financials_single(d, code, df),
            )
            if from_live:
                items, total = await qs.get_financial_indicators(
                    db, code, page=page, page_size=page_size
                )
        except Exception as e:
            logger.warning("Live financials fallback failed for %s: %s", code, e)

    return ApiResponse(data={
        "items": [
            {
                "report_date": str(r.report_date),
                "eps_basic": r.eps_basic, "eps_diluted": r.eps_diluted,
                "bvps": r.bvps, "cfps": r.cfps,
                "roe": r.roe, "roa": r.roa,
                "gross_margin": r.gross_margin, "net_margin": r.net_margin,
                "revenue_growth": r.revenue_growth,
                "profit_growth": r.profit_growth,
                "asset_growth": r.asset_growth,
                "current_ratio": r.current_ratio, "quick_ratio": r.quick_ratio,
                "debt_ratio": r.debt_ratio,
                "operating_cf": r.operating_cf,
                "investing_cf": r.investing_cf,
                "financing_cf": r.financing_cf,
            }
            for r in items
        ],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/{code}/forecast")
async def get_forecast(code: str, db: AsyncSession = Depends(get_db)):
    """盈利预测 — 最新一份."""
    f = await qs.get_profit_forecast(db, code)
    if f is None:
        try:
            _, from_live = await live_fetcher.fetch_or_live(
                db,
                cache_key=f"forecast:{code}",
                db_query_fn=lambda d: _forecast_exists(d, code),
                live_fetch_fn=lambda: _fetch_forecast_single(code),
                save_fn=lambda d, df: _save_forecast_single(d, code, df),
            )
            if from_live:
                f = await qs.get_profit_forecast(db, code)
        except Exception as e:
            logger.warning("Live forecast fallback failed for %s: %s", code, e)

    if f is None:
        return ApiResponse(data=None, message="No forecast data")
    return ApiResponse(data={
        "stock_code": f.stock_code, "stock_name": f.stock_name,
        "research_report_num": f.research_report_num,
        "ratings": {
            "buy": f.rating_buy, "overweight": f.rating_overweight,
            "neutral": f.rating_neutral, "underweight": f.rating_underweight,
            "sell": f.rating_sell,
        },
        "forecast_eps": [f.forecast_eps_year1, f.forecast_eps_year2,
                         f.forecast_eps_year3, f.forecast_eps_year4],
        "forecast_np": [f.forecast_np_year1, f.forecast_np_year2,
                        f.forecast_np_year3, f.forecast_np_year4],
        "target_avg_price": f.target_avg_price,
        "updated_date": str(f.updated_date),
    })


@router.get("/{code}/fund-flow")
async def get_fund_flow(
    code: str,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """资金流向 (东方财富接口被封，仅返回DB数据)."""
    items, total = await qs.get_fund_flow(
        db, code, start_date=start_date, end_date=end_date,
        page=page, page_size=page_size,
    )
    return ApiResponse(data={
        "items": [
            {
                "trade_date": str(f.trade_date), "close": f.close,
                "change_pct": f.change_pct,
                "main_net_inflow": f.main_net_inflow, "main_net_ratio": f.main_net_ratio,
                "huge_net_inflow": f.huge_net_inflow, "huge_net_ratio": f.huge_net_ratio,
                "large_net_inflow": f.large_net_inflow, "large_net_ratio": f.large_net_ratio,
                "medium_net_inflow": f.medium_net_inflow, "medium_net_ratio": f.medium_net_ratio,
                "small_net_inflow": f.small_net_inflow, "small_net_ratio": f.small_net_ratio,
            }
            for f in items
        ],
        "total": total, "page": page, "page_size": page_size,
    })


@router.get("/{code}/today")
async def get_today_summary(code: str, db: AsyncSession = Depends(get_db)):
    """当日行情摘要 + 涨停统计."""
    from datetime import date, timedelta
    from sqlalchemy import func, desc

    # Latest bar
    result = await db.execute(
        select(StockDailyQuote)
        .where(StockDailyQuote.stock_code == code, StockDailyQuote.adjust_type == "qfq")
        .order_by(desc(StockDailyQuote.trade_date))
        .limit(1)
    )
    bar = result.scalar_one_or_none()

    if bar is None:
        # Live fallback: fetch recent K-line for this stock
        try:
            _, from_live = await live_fetcher.fetch_or_live(
                db,
                cache_key=f"kline:daily:{code}:qfq",
                db_query_fn=lambda d: _bar_exists(d, code),
                live_fetch_fn=lambda: _fetch_kline_single(code, "daily", "qfq"),
                save_fn=lambda d, df: _save_kline_single(d, code, "daily", "qfq", df),
            )
            if from_live:
                result = await db.execute(
                    select(StockDailyQuote)
                    .where(StockDailyQuote.stock_code == code,
                           StockDailyQuote.adjust_type == "qfq")
                    .order_by(desc(StockDailyQuote.trade_date))
                    .limit(1)
                )
                bar = result.scalar_one_or_none()
        except Exception as e:
            logger.warning("Live today-summary fallback failed for %s: %s", code, e)

    if bar is None:
        return ApiResponse(data={"code": code, "message": "无K线数据"})

    today = date.today()
    year_start = date(today.year, 1, 1)

    # Limit-up counts
    async def _count_lu(start_d, threshold=9.8):
        r = await db.execute(
            select(func.count()).select_from(StockDailyQuote).where(
                StockDailyQuote.stock_code == code,
                StockDailyQuote.adjust_type == "qfq",
                StockDailyQuote.trade_date >= start_d,
                StockDailyQuote.change_pct >= threshold,
            )
        )
        return r.scalar() or 0

    return ApiResponse(data={
        "code": code,
        "trade_date": str(bar.trade_date),
        "open": bar.open,
        "close": bar.close,
        "high": bar.high,
        "low": bar.low,
        "volume": bar.volume,
        "amount": bar.amount,
        "change_pct": bar.change_pct,
        "change_amount": bar.change_amount,
        "turnover_rate": bar.turnover_rate,
        "amplitude": bar.amplitude,
        "lu_5d": await _count_lu(today - timedelta(days=5)),
        "lu_30d": await _count_lu(today - timedelta(days=30)),
        "lu_year": await _count_lu(year_start),
    })


# ═══════════════════════════════════════════════════════════════════════════
# Live-fetch helpers — called by LiveFetcher when DB is empty
# ═══════════════════════════════════════════════════════════════════════════


def _to_float(val) -> float | None:
    try:
        f = float(val)
        return None if pd.isna(f) else f
    except (ValueError, TypeError):
        return None


def _to_int(val) -> int | None:
    try:
        i = int(val)
        return None if pd.isna(i) else i
    except (ValueError, TypeError):
        return None


def _to_date(val):
    if val is None:
        return None
    try:
        if isinstance(val, date):
            return val
        s = str(val)
        if len(s) == 8 and s.isdigit():
            return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
        from datetime import datetime as dt
        if hasattr(val, 'strftime'):
            return date(val.year, val.month, val.day)
        return dt.strptime(s[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ── K-line helpers ───────────────────────────────────────────────────────

async def _kline_count(db, code: str, period: str, adjust_type: str):
    """Check if any K-line rows exist (returns count)."""
    from app.models.stock_quote import StockDailyQuote, StockWeeklyQuote, StockMonthlyQuote
    model = {"daily": StockDailyQuote, "weekly": StockWeeklyQuote, "monthly": StockMonthlyQuote}[period]
    r = await db.execute(
        select(func.count()).select_from(model).where(
            model.stock_code == code, model.adjust_type == adjust_type
        )
    )
    return r.scalar() or 0


async def _kline_is_fresh(db, code: str, period: str, adjust_type: str, max_age_days: int = 2):
    """Check if K-line data exists AND is recent (within max_age_days). Return False if stale or missing."""
    from datetime import date as dt_date, timedelta
    from app.models.stock_quote import StockDailyQuote, StockWeeklyQuote, StockMonthlyQuote
    model = {"daily": StockDailyQuote, "weekly": StockWeeklyQuote, "monthly": StockMonthlyQuote}[period]
    r = await db.execute(
        select(model.trade_date)
        .where(model.stock_code == code, model.adjust_type == adjust_type)
        .order_by(desc(model.trade_date))
        .limit(1)
    )
    latest = r.scalar_one_or_none()
    if latest is None:
        return False
    cutoff = dt_date.today() - timedelta(days=max_age_days)
    return latest >= cutoff


async def _bar_exists(db, code: str):
    """Check if recent today-summary bar exists (within 2 days)."""
    from datetime import date as dt_date, timedelta
    from sqlalchemy import desc as _desc
    r = await db.execute(
        select(StockDailyQuote.trade_date)
        .where(StockDailyQuote.stock_code == code, StockDailyQuote.adjust_type == "qfq")
        .order_by(_desc(StockDailyQuote.trade_date))
        .limit(1)
    )
    latest = r.scalar_one_or_none()
    if latest is None:
        return False
    # 超过2天没更新 → 触发实时拉取
    cutoff = dt_date.today() - timedelta(days=2)
    return latest >= cutoff


async def _fetch_kline_single(code: str, period: str, adjust_type: str):
    """Fetch full K-line history for a single stock from Sina via AKShare."""
    import akshare as ak
    return await asyncio.to_thread(
        ak.stock_zh_a_hist,
        symbol=code, period=period,
        start_date="19900101",
        end_date=date.today().strftime("%Y%m%d"),
        adjust=adjust_type,
    )


async def _save_kline_single(db, code: str, period: str, adjust_type: str, df: pd.DataFrame):
    """Save fetched K-line DataFrame to DB."""
    import uuid
    from sqlalchemy.dialects.mysql import insert as mysql_insert
    from app.models.stock_quote import StockDailyQuote, StockWeeklyQuote, StockMonthlyQuote

    model = {"daily": StockDailyQuote, "weekly": StockWeeklyQuote, "monthly": StockMonthlyQuote}[period]
    if df is None or df.empty:
        return

    rows = []
    for _, r in df.iterrows():
        trade_date = _to_date(r.get("日期"))
        if trade_date is None:
            continue
        rows.append({
            "id": str(uuid.uuid4()),
            "stock_code": code,
            "trade_date": trade_date,
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

    if rows:
        stmt = mysql_insert(model).values(rows)
        update_cols = {c.name: stmt.inserted[c.name] for c in model.__table__.columns
                       if c.name not in ("id", "stock_code", "trade_date", "adjust_type")}
        stmt = stmt.on_duplicate_key_update(**update_cols)
        await db.execute(stmt)
        await db.commit()


# ── Financial indicators helpers ──────────────────────────────────────────

async def _fin_count(db, code: str):
    from app.models.stock_financial import StockFinancialIndicator
    r = await db.execute(
        select(func.count()).select_from(StockFinancialIndicator).where(
            StockFinancialIndicator.stock_code == code
        )
    )
    return r.scalar() or 0


async def _fetch_financials_single(code: str):
    """Fetch financial indicators from 东方财富 for a single stock."""
    import akshare as ak
    em_symbol = f"{code}.{'SH' if code.startswith('6') else 'SZ'}"
    return await asyncio.to_thread(
        ak.stock_financial_analysis_indicator_em, symbol=em_symbol
    )


async def _save_financials_single(db, code: str, df: pd.DataFrame):
    """Save financial indicators DataFrame to DB."""
    import uuid
    from sqlalchemy.dialects.mysql import insert as mysql_insert
    from app.models.stock_financial import StockFinancialIndicator

    if df is None or df.empty:
        return

    rows = []
    for _, r in df.iterrows():
        rd = _to_date(r.get("REPORT_DATE"))
        if rd is None:
            continue
        rows.append({
            "id": str(uuid.uuid4()),
            "stock_code": code,
            "report_date": rd,
            "eps_basic": _to_float(r.get("EPSJB")),
            "eps_diluted": _to_float(r.get("EPSXS")),
            "bvps": _to_float(r.get("BPS")),
            "cfps": _to_float(r.get("MGJYXJJE")),
            "roe": _to_float(r.get("ROEJQ")),
            "roa": _to_float(r.get("ZZCJLL")),
            "gross_margin": _to_float(r.get("XSMLL")),
            "net_margin": _to_float(r.get("XSJLL")),
            "revenue_growth": _to_float(r.get("TOTALOPERATEREVETZ")),
            "profit_growth": _to_float(r.get("PARENTNETPROFITTZ")),
            "asset_growth": _to_float(r.get("TOAZZL")),
            "receivables_turnover": _to_float(r.get("YSZKZZTS")),
            "inventory_turnover": _to_float(r.get("CHZZTS")),
            "asset_turnover": _to_float(r.get("ZZCZZTS")),
            "current_ratio": _to_float(r.get("LD")),
            "quick_ratio": _to_float(r.get("SD")),
            "debt_ratio": _to_float(r.get("ZCFZL")),
            "operating_cf": _to_float(r.get("XJLLB")),
            "raw_data": r.to_json() if hasattr(r, "to_json") else "{}",
        })

    if rows:
        stmt = mysql_insert(StockFinancialIndicator).values(rows)
        update_cols = {c.name: stmt.inserted[c.name] for c in StockFinancialIndicator.__table__.columns
                       if c.name not in ("id", "stock_code", "report_date")}
        stmt = stmt.on_duplicate_key_update(**update_cols)
        await db.execute(stmt)
        await db.commit()


# ── Performance report helpers ────────────────────────────────────────────

async def _perf_count(db, code: str):
    from app.models.stock_financial import StockPerformanceReport
    r = await db.execute(
        select(func.count()).select_from(StockPerformanceReport).where(
            StockPerformanceReport.stock_code == code
        )
    )
    return r.scalar() or 0


async def _fetch_performance_single(code: str):
    """Fetch latest 3 quarters of performance reports, filter to one stock."""
    import akshare as ak
    from datetime import date as dt_date

    today = dt_date.today()
    # Generate last 3 quarter-end dates
    quarters = []
    for offset in range(3):
        q_month = ((today.month - 1) // 3 - offset) * 3
        if q_month <= 0:
            q_month += 12
            y = today.year - 1
        else:
            y = today.year
        # quarter end: month 3, 6, 9, 12 → last day
        import calendar
        last_day = calendar.monthrange(y, q_month)[1]
        quarters.append(f"{y}{q_month:02d}{last_day}")

    dfs = []
    for q in reversed(quarters):
        try:
            df = await asyncio.to_thread(ak.stock_yjbb_em, date=q)
            if df is not None and not df.empty:
                # Filter to this stock
                df["代码_str"] = df["股票代码"].astype(str).str.zfill(6)
                filtered = df[df["代码_str"] == code]
                if not filtered.empty:
                    dfs.append(filtered)
        except Exception:
            continue

    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()


async def _save_performance_single(db, code: str, df: pd.DataFrame):
    """Save performance report rows to DB."""
    import uuid
    from sqlalchemy.dialects.mysql import insert as mysql_insert
    from app.models.stock_financial import StockPerformanceReport

    if df is None or df.empty:
        return

    rows = []
    for _, r in df.iterrows():
        rd = None
        # Try to extract quarter date from the data
        report_date_val = r.get("report_date") if "report_date" in df.columns else None
        if report_date_val is None:
            continue
        rd = _to_date(report_date_val)
        if rd is None:
            continue

        rows.append({
            "id": str(uuid.uuid4()),
            "stock_code": code,
            "stock_name": str(r.get("股票简称", "")),
            "report_date": rd,
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

    if rows:
        stmt = mysql_insert(StockPerformanceReport).values(rows)
        update_cols = {c.name: stmt.inserted[c.name] for c in StockPerformanceReport.__table__.columns
                       if c.name not in ("id", "stock_code", "report_date")}
        stmt = stmt.on_duplicate_key_update(**update_cols)
        await db.execute(stmt)
        await db.commit()


# ── Forecast helpers ──────────────────────────────────────────────────────

async def _forecast_exists(db, code: str):
    from app.models.stock_forecast import StockProfitForecast
    r = await db.execute(
        select(func.count()).select_from(StockProfitForecast).where(
            StockProfitForecast.stock_code == code
        )
    )
    return (r.scalar() or 0) > 0


async def _fetch_forecast_single(code: str):
    """Fetch all profit forecasts and filter to one stock."""
    import akshare as ak
    df = await asyncio.to_thread(ak.stock_profit_forecast_em, symbol="")
    if df is None or df.empty:
        return df
    df["代码_str"] = df["代码"].astype(str).str.zfill(6)
    return df[df["代码_str"] == code]


async def _save_forecast_single(db, code: str, df: pd.DataFrame):
    """Save profit forecast rows to DB."""
    import uuid
    from sqlalchemy.dialects.mysql import insert as mysql_insert
    from app.models.stock_forecast import StockProfitForecast

    if df is None or df.empty:
        return

    rows = []
    for _, r in df.iterrows():
        rows.append({
            "id": str(uuid.uuid4()),
            "stock_code": code,
            "stock_name": str(r.get("名称", "")),
            "research_report_num": _to_int(r.get("研报数")),
            "rating_buy": _to_int(r.get("机构投资评级(近六个月)-买入")),
            "rating_overweight": _to_int(r.get("机构投资评级(近六个月)-增持")),
            "rating_neutral": _to_int(r.get("机构投资评级(近六个月)-中性")),
            "rating_underweight": _to_int(r.get("机构投资评级(近六个月)-减持")),
            "rating_sell": _to_int(r.get("机构投资评级(近六个月)-卖出")),
            "forecast_eps_year1": _to_float(r.get("2025预测每股收益")),
            "forecast_eps_year2": _to_float(r.get("2026预测每股收益")),
            "forecast_eps_year3": _to_float(r.get("2027预测每股收益")),
            "forecast_eps_year4": _to_float(r.get("2028预测每股收益")),
            "updated_date": date.today(),
        })

    if rows:
        stmt = mysql_insert(StockProfitForecast).values(rows)
        update_cols = {c.name: stmt.inserted[c.name] for c in StockProfitForecast.__table__.columns
                       if c.name not in ("id", "stock_code", "updated_date")}
        stmt = stmt.on_duplicate_key_update(**update_cols)
        await db.execute(stmt)
        await db.commit()


# ── Generic helpers ───────────────────────────────────────────────────────


def _quote_to_dict(q) -> dict:
    return {
        "trade_date": str(q.trade_date),
        "open": q.open,
        "close": q.close,
        "high": q.high,
        "low": q.low,
        "volume": q.volume,
        "amount": q.amount,
        "amplitude": q.amplitude,
        "change_pct": q.change_pct,
        "change_amount": q.change_amount,
        "turnover_rate": q.turnover_rate,
    }
