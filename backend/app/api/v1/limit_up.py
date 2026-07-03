"""涨停板 API — real-time data from AKShare + historical stats from local DB."""

from datetime import date, datetime, timedelta
from typing import Optional

import akshare as ak
import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.stock_info import StockInfo
from app.models.stock_quote import StockDailyQuote
from app.schemas.common import ApiResponse

router = APIRouter(prefix="/limit-up", tags=["limit-up"])

# Board type → stock code prefix filter
BOARD_PREFIX_MAP = {
    "主板": ("600", "601", "603", "605", "000", "001", "002", "003"),
    "创业板": ("300", "301"),
    "科创板": ("688",),
}


def _filter_by_board(df: pd.DataFrame, board_type: Optional[str]) -> pd.DataFrame:
    if board_type is None or board_type not in BOARD_PREFIX_MAP:
        return df
    prefixes = BOARD_PREFIX_MAP[board_type]
    df["代码_str"] = df["代码"].astype(str).str.zfill(6)
    return df[df["代码_str"].str.startswith(prefixes)]


async def _get_limit_up_counts(
    db: AsyncSession, codes: list[str]
) -> dict[str, dict]:
    """Query local DB for limit-up counts per stock.

    Returns: { code: { last_5d, last_30d, this_year } }
    """
    if not codes:
        return {}

    today = date.today()
    d5 = today - timedelta(days=5)
    d30 = today - timedelta(days=30)
    year_start = date(today.year, 1, 1)

    result = {}

    for code in codes:
        counts = {}
        # 近5天
        r = await db.execute(
            select(func.count()).select_from(StockDailyQuote).where(
                StockDailyQuote.stock_code == code,
                StockDailyQuote.adjust_type == "qfq",
                StockDailyQuote.trade_date >= d5,
                StockDailyQuote.change_pct >= 9.8,
            )
        )
        counts["last_5d"] = r.scalar() or 0

        # 近30天
        r = await db.execute(
            select(func.count()).select_from(StockDailyQuote).where(
                StockDailyQuote.stock_code == code,
                StockDailyQuote.adjust_type == "qfq",
                StockDailyQuote.trade_date >= d30,
                StockDailyQuote.change_pct >= 9.8,
            )
        )
        counts["last_30d"] = r.scalar() or 0

        # 今年
        r = await db.execute(
            select(func.count()).select_from(StockDailyQuote).where(
                StockDailyQuote.stock_code == code,
                StockDailyQuote.adjust_type == "qfq",
                StockDailyQuote.trade_date >= year_start,
                StockDailyQuote.change_pct >= 9.8,
            )
        )
        counts["this_year"] = r.scalar() or 0

        result[code] = counts

    return result


@router.get("")
async def get_limit_up(
    date_str: Optional[str] = Query(None, alias="date", description="日期 YYYYMMDD"),
    board_type: Optional[str] = Query(None, description="主板 / 创业板 / 科创板"),
    db: AsyncSession = Depends(get_db),
):
    try:
        target_date = date_str or date.today().strftime("%Y%m%d")
        df = ak.stock_zt_pool_em(date=target_date)

        if df.empty:
            df = ak.stock_zt_pool_previous_em(date=target_date)
        if df.empty:
            df = ak.stock_zt_pool_strong_em(date=target_date)

        if board_type:
            df = _filter_by_board(df, board_type)

        codes = [str(r.get("代码", "")).zfill(6) for _, r in df.iterrows()]
        counts_map = await _get_limit_up_counts(db, codes)

        items = []
        for _, r in df.iterrows():
            code = str(r.get("代码", "")).zfill(6)
            counts = counts_map.get(code, {})
            items.append({
                "code": code,
                "name": str(r.get("名称", "")),
                "price": float(r.get("最新价", 0)) if pd.notna(r.get("最新价")) else None,
                "change_pct": float(r.get("涨跌幅", 0)) if pd.notna(r.get("涨跌幅")) else None,
                "amount": float(r.get("成交额", 0)) if pd.notna(r.get("成交额")) else None,
                "float_mv": float(r.get("流通市值", 0)) if pd.notna(r.get("流通市值")) else None,
                "total_mv": float(r.get("总市值", 0)) if pd.notna(r.get("总市值")) else None,
                "turnover": float(r.get("换手率", 0)) if pd.notna(r.get("换手率")) else None,
                "seal_amount": float(r.get("封板资金", 0)) if pd.notna(r.get("封板资金")) else None,
                "first_seal_time": str(r.get("首次封板时间", "")),
                "last_seal_time": str(r.get("最后封板时间", "")),
                "break_count": int(r.get("炸板次数", 0)) if pd.notna(r.get("炸板次数")) else 0,
                "limit_up_count": str(r.get("涨停统计", "")),
                "consecutive": int(r.get("连板数", 0)) if pd.notna(r.get("连板数")) else 0,
                "industry": str(r.get("所属行业", "")) if pd.notna(r.get("所属行业")) else "",
                "stats_5d": counts.get("last_5d", 0),
                "stats_30d": counts.get("last_30d", 0),
                "stats_year": counts.get("this_year", 0),
            })

        return ApiResponse(data={
            "board_type": board_type or "全部",
            "date": target_date,
            "items": items,
            "total": len(items),
        })

    except Exception as e:
        return ApiResponse(
            code=503,
            message=f"数据源暂时不可用: {str(e)[:100]}",
            data={"board_type": board_type or "全部", "items": [], "total": 0},
        )


@router.get("/period")
async def get_limit_up_by_period(
    days: int = Query(1, ge=1, le=365, description="查询天数"),
    board_type: Optional[str] = Query(None, description="主板 / 创业板 / 科创板"),
    db: AsyncSession = Depends(get_db),
):
    """从本地数据库查询最近N天内的涨停股票。

    不依赖东方财富，数据来自已有的日K线表。
    涨停判断：主板涨跌幅 >= 9.8%，科创/创业板 >= 19.8%
    """
    start_date = date.today() - timedelta(days=days)

    # Build prefix filter
    prefixes = BOARD_PREFIX_MAP.get(board_type)

    # Get all stocks that hit limit-up in the period
    stmt = (
        select(
            StockDailyQuote.stock_code,
            StockDailyQuote.trade_date,
            StockDailyQuote.close,
            StockDailyQuote.volume,
            StockDailyQuote.amount,
            StockDailyQuote.change_pct,
            StockDailyQuote.turnover_rate,
            StockInfo.name,
            StockInfo.industry,
        )
        .join(StockInfo, StockDailyQuote.stock_code == StockInfo.code, isouter=True)
        .where(
            StockDailyQuote.trade_date >= start_date,
            StockDailyQuote.adjust_type == "qfq",
            StockDailyQuote.change_pct >= 9.8,
        )
        .order_by(StockDailyQuote.trade_date.desc(), StockDailyQuote.change_pct.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Filter by board type and deduplicate (keep highest change_pct per stock per day)
    from collections import defaultdict
    stock_info: dict[str, dict] = {}
    for r in rows:
        code = r.stock_code
        if prefixes and not code.startswith(prefixes):
            continue
        if code not in stock_info:
            stock_info[code] = {
                "code": code,
                "name": r.name or "",
                "industry": r.industry or "",
                "max_change": r.change_pct or 0,
                "latest_date": str(r.trade_date),
                "latest_close": r.close,
                "volume": r.volume,
                "amount": r.amount,
                "turnover": r.turnover_rate,
                "count": 0,
            }
        stock_info[code]["count"] += 1
        if (r.change_pct or 0) > stock_info[code]["max_change"]:
            stock_info[code]["max_change"] = r.change_pct or 0
            stock_info[code]["latest_date"] = str(r.trade_date)
            stock_info[code]["latest_close"] = r.close
            stock_info[code]["volume"] = r.volume
            stock_info[code]["amount"] = r.amount
            stock_info[code]["turnover"] = r.turnover_rate

    # Get historical stats
    codes = list(stock_info.keys())
    counts_map = await _get_limit_up_counts(db, codes)

    items = []
    for code, info in stock_info.items():
        counts = counts_map.get(code, {})
        items.append({
            "code": code,
            "name": info["name"],
            "industry": info["industry"],
            "price": info["latest_close"],
            "change_pct": info["max_change"],
            "count": info["count"],
            "trade_date": info["latest_date"],
            "volume": info["volume"],
            "amount": info["amount"],
            "turnover": info["turnover"],
            "stats_5d": counts.get("last_5d", 0),
            "stats_30d": counts.get("last_30d", 0),
            "stats_year": counts.get("this_year", 0),
        })

    # Sort by change_pct desc
    items.sort(key=lambda x: x["change_pct"], reverse=True)

    return ApiResponse(data={
        "days": days,
        "board_type": board_type or "全部",
        "items": items,
        "total": len(items),
    })
