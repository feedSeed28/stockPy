"""Stock API endpoints — /api/v1/stocks/*."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.stock_quote import StockDailyQuote
from app.schemas.common import ApiResponse
from app.services import stock_query_service as qs

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
    """资金流向."""
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


# ── Helper ─────────────────────────────────────────────────────────────


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
