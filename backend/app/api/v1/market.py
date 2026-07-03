"""Market overview API — 行情概览（从本地数据库读取最新交易日数据）."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.stock_quote import StockDailyQuote
from app.models.stock_info import StockInfo
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/today")
async def get_today_market(
    sort_by: str = Query("change_pct", description="排序字段: change_pct, volume, amount, turnover_rate"),
    order: str = Query("desc", description="desc / asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """当日行情概览。

    从本地数据库获取最新交易日的涨跌数据，无需调用外部 API。
    """
    # Find the most recent trading date
    max_date_result = await db.execute(select(func.max(StockDailyQuote.trade_date)))
    latest_date = max_date_result.scalar()
    if not latest_date:
        return ApiResponse(data={"items": [], "total": 0, "date": None})

    # Count totals
    count_stmt = select(func.count()).select_from(StockDailyQuote).where(
        StockDailyQuote.trade_date == latest_date,
        StockDailyQuote.adjust_type == "qfq",
    )
    total = await db.scalar(count_stmt) or 0

    # Sort column
    sort_col = getattr(StockDailyQuote, sort_by, StockDailyQuote.change_pct)
    if order == "asc":
        sort_col = sort_col.asc()
    else:
        sort_col = sort_col.desc()

    # Query with join to get stock name + industry
    stmt = (
        select(
            StockDailyQuote.stock_code,
            StockInfo.name,
            StockInfo.industry,
            StockDailyQuote.close,
            StockDailyQuote.open,
            StockDailyQuote.high,
            StockDailyQuote.low,
            StockDailyQuote.volume,
            StockDailyQuote.amount,
            StockDailyQuote.change_pct,
            StockDailyQuote.change_amount,
            StockDailyQuote.turnover_rate,
            StockDailyQuote.amplitude,
        )
        .join(StockInfo, StockDailyQuote.stock_code == StockInfo.code, isouter=True)
        .where(
            StockDailyQuote.trade_date == latest_date,
            StockDailyQuote.adjust_type == "qfq",
        )
        .order_by(sort_col)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Statistics
    up_count_stmt = select(func.count()).select_from(StockDailyQuote).where(
        StockDailyQuote.trade_date == latest_date,
        StockDailyQuote.adjust_type == "qfq",
        StockDailyQuote.change_pct > 0,
    )
    up_count = await db.scalar(up_count_stmt) or 0

    down_count_stmt = select(func.count()).select_from(StockDailyQuote).where(
        StockDailyQuote.trade_date == latest_date,
        StockDailyQuote.adjust_type == "qfq",
        StockDailyQuote.change_pct < 0,
    )
    down_count = await db.scalar(down_count_stmt) or 0
    flat_count = total - up_count - down_count

    items = [
        {
            "code": r.stock_code,
            "name": r.name or "",
            "industry": r.industry or "",
            "close": r.close,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "volume": r.volume,
            "amount": r.amount,
            "change_pct": r.change_pct,
            "change_amount": r.change_amount,
            "turnover_rate": r.turnover_rate,
            "amplitude": r.amplitude,
        }
        for r in rows
    ]

    return ApiResponse(data={
        "date": str(latest_date),
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "stats": {
            "up": up_count,
            "down": down_count,
            "flat": flat_count,
        },
    })
