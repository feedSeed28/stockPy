"""Read queries for the API layer.

All queries go through here — no raw SQL in route handlers.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Select, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_info import StockInfo
from app.models.stock_quote import StockDailyQuote, StockWeeklyQuote, StockMonthlyQuote
from app.models.stock_financial import StockFinancialIndicator, StockPerformanceReport
from app.models.stock_forecast import StockProfitForecast
from app.models.stock_fund_flow import StockFundFlowDaily
from app.models.stock_board import StockBoardInfo, StockBoardMember


# ── Stock Info ────────────────────────────────────────────────────────────


async def list_stocks(
    db: AsyncSession,
    exchange: str | None = None,
    board_type: str | None = None,
    is_active: bool | None = True,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[StockInfo], int]:
    """Paginated stock list with optional filters."""
    stmt = select(StockInfo)
    count_stmt = select(func.count(StockInfo.code))

    if exchange:
        stmt = stmt.where(StockInfo.exchange == exchange)
        count_stmt = count_stmt.where(StockInfo.exchange == exchange)
    if board_type:
        stmt = stmt.where(StockInfo.board_type == board_type)
        count_stmt = count_stmt.where(StockInfo.board_type == board_type)
    if is_active is not None:
        stmt = stmt.where(StockInfo.is_active == is_active)
        count_stmt = count_stmt.where(StockInfo.is_active == is_active)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(
            (StockInfo.code.like(like)) | (StockInfo.name.like(like))
        )
        count_stmt = count_stmt.where(
            (StockInfo.code.like(like)) | (StockInfo.name.like(like))
        )

    total = await db.scalar(count_stmt) or 0
    stmt = stmt.order_by(StockInfo.code).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return result.scalars().all(), total


async def get_stock(db: AsyncSession, code: str) -> StockInfo | None:
    return await db.get(StockInfo, code)


# ── K-line Quotes ─────────────────────────────────────────────────────────


_QUOTE_MODEL = {
    "daily": StockDailyQuote,
    "weekly": StockWeeklyQuote,
    "monthly": StockMonthlyQuote,
}


async def get_kline(
    db: AsyncSession,
    stock_code: str,
    period: str = "daily",
    adjust_type: str = "qfq",
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 200,
) -> tuple[list[Any], int]:
    """Paginated K-line quotes for a stock."""
    model = _QUOTE_MODEL[period]
    stmt = select(model).where(
        model.stock_code == stock_code,
        model.adjust_type == adjust_type,
    )
    count_stmt = select(func.count(model.id)).where(
        model.stock_code == stock_code,
        model.adjust_type == adjust_type,
    )

    if start_date:
        stmt = stmt.where(model.trade_date >= start_date)
        count_stmt = count_stmt.where(model.trade_date >= start_date)
    if end_date:
        stmt = stmt.where(model.trade_date <= end_date)
        count_stmt = count_stmt.where(model.trade_date <= end_date)

    total = await db.scalar(count_stmt) or 0
    stmt = stmt.order_by(model.trade_date).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return result.scalars().all(), total


async def get_kline_date_range(
    db: AsyncSession,
    stock_code: str,
    period: str = "daily",
    adjust_type: str = "qfq",
) -> dict[str, date | None]:
    """Get the min/max trade_date for a stock's K-line."""
    model = _QUOTE_MODEL[period]
    stmt = select(
        func.min(model.trade_date),
        func.max(model.trade_date),
    ).where(
        model.stock_code == stock_code,
        model.adjust_type == adjust_type,
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if row:
        return {"min_date": row[0], "max_date": row[1]}
    return {"min_date": None, "max_date": None}


# ── Performance Reports ───────────────────────────────────────────────────


async def get_performance_reports(
    db: AsyncSession,
    stock_code: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[StockPerformanceReport], int]:
    stmt = (
        select(StockPerformanceReport)
        .where(StockPerformanceReport.stock_code == stock_code)
        .order_by(desc(StockPerformanceReport.report_date))
    )
    count_stmt = select(func.count(StockPerformanceReport.id)).where(
        StockPerformanceReport.stock_code == stock_code
    )

    total = await db.scalar(count_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return result.scalars().all(), total


async def get_latest_performance(
    db: AsyncSession, stock_code: str
) -> StockPerformanceReport | None:
    result = await db.execute(
        select(StockPerformanceReport)
        .where(StockPerformanceReport.stock_code == stock_code)
        .order_by(desc(StockPerformanceReport.report_date))
        .limit(1)
    )
    return result.scalar_one_or_none()


# ── Financial Indicators ──────────────────────────────────────────────────


async def get_financial_indicators(
    db: AsyncSession,
    stock_code: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[StockFinancialIndicator], int]:
    stmt = (
        select(StockFinancialIndicator)
        .where(StockFinancialIndicator.stock_code == stock_code)
        .order_by(desc(StockFinancialIndicator.report_date))
    )
    count_stmt = select(func.count(StockFinancialIndicator.id)).where(
        StockFinancialIndicator.stock_code == stock_code
    )

    total = await db.scalar(count_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return result.scalars().all(), total


# ── Profit Forecast ───────────────────────────────────────────────────────


async def get_profit_forecast(
    db: AsyncSession, stock_code: str
) -> StockProfitForecast | None:
    result = await db.execute(
        select(StockProfitForecast)
        .where(StockProfitForecast.stock_code == stock_code)
        .order_by(desc(StockProfitForecast.updated_date))
        .limit(1)
    )
    return result.scalar_one_or_none()


# ── Fund Flow ─────────────────────────────────────────────────────────────


async def get_fund_flow(
    db: AsyncSession,
    stock_code: str,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[StockFundFlowDaily], int]:
    stmt = select(StockFundFlowDaily).where(
        StockFundFlowDaily.stock_code == stock_code
    )
    count_stmt = select(func.count(StockFundFlowDaily.id)).where(
        StockFundFlowDaily.stock_code == stock_code
    )

    if start_date:
        stmt = stmt.where(StockFundFlowDaily.trade_date >= start_date)
        count_stmt = count_stmt.where(StockFundFlowDaily.trade_date >= start_date)
    if end_date:
        stmt = stmt.where(StockFundFlowDaily.trade_date <= end_date)
        count_stmt = count_stmt.where(StockFundFlowDaily.trade_date <= end_date)

    total = await db.scalar(count_stmt) or 0
    stmt = stmt.order_by(desc(StockFundFlowDaily.trade_date))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return result.scalars().all(), total


# ── Boards ────────────────────────────────────────────────────────────────


async def list_boards(
    db: AsyncSession,
    board_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[StockBoardInfo], int]:
    stmt = select(StockBoardInfo)
    count_stmt = select(func.count(StockBoardInfo.id))

    if board_type:
        stmt = stmt.where(StockBoardInfo.board_type == board_type)
        count_stmt = count_stmt.where(StockBoardInfo.board_type == board_type)

    total = await db.scalar(count_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return result.scalars().all(), total


async def get_board_members(
    db: AsyncSession,
    board_id: str,
    page: int = 1,
    page_size: int = 100,
) -> tuple[list[dict[str, Any]], int]:
    """Get board members joined with stock_info for names."""
    stmt = (
        select(StockBoardMember, StockInfo.name)
        .join(StockInfo, StockBoardMember.stock_code == StockInfo.code, isouter=True)
        .where(StockBoardMember.board_id == board_id)
    )
    count_stmt = select(func.count(StockBoardMember.id)).where(
        StockBoardMember.board_id == board_id
    )

    total = await db.scalar(count_stmt) or 0
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    return [
        {"stock_code": m.StockBoardMember.stock_code, "stock_name": name}
        for m, name in result.all()
    ], total
