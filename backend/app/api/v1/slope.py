"""Trend slope screening API."""

from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.stock_info import StockInfo
from app.models.stock_quote import StockDailyQuote
from app.schemas.common import ApiResponse
from app.services.indicator_service import compute_slope_pct

router = APIRouter(prefix="/slope", tags=["slope"])

TREND_LABELS = {
    "strong_up": {"name": "强势上涨", "min": 0.5, "max": None},
    "mild_up": {"name": "温和上涨", "min": 0.1, "max": 0.5},
    "sideways": {"name": "横盘", "min": -0.1, "max": 0.1},
    "mild_down": {"name": "温和下跌", "min": -0.5, "max": -0.1},
    "strong_down": {"name": "大跌", "min": None, "max": -0.5},
}


@router.get("/scan")
async def scan_trend(
    trend: str = Query("mild_up", description="strong_up / mild_up / sideways / mild_down / strong_down"),
    period: int = Query(20, ge=5, le=60, description="斜率计算周期"),
    field: str = Query("close", description="close / ma_5 / ma_20"),
    board_type: Optional[str] = Query(None, description="主板 / 创业板 / 科创板"),
    exclude_st: bool = Query(True, description="排除ST股票"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """全市场斜率扫描 — 按趋势强度筛选股票。

    从本地数据库取最近 N 天K线，计算线性回归斜率，
    按趋势分类返回。
    """
    if trend not in TREND_LABELS:
        return ApiResponse(code=400, message=f"无效趋势类型: {trend}")

    label = TREND_LABELS[trend]
    min_val = label["min"]
    max_val = label["max"]

    # Board filter
    prefix_map = {
        "主板": ("600", "601", "603", "605", "000", "001", "002", "003"),
        "创业板": ("300", "301"),
        "科创板": ("688",),
    }

    # Get all active stock codes
    stmt = select(StockInfo.code, StockInfo.name, StockInfo.industry)
    result = await db.execute(stmt.order_by(StockInfo.code))
    all_stocks = [{"code": r[0], "name": r[1], "industry": r[2]} for r in result.fetchall()]

    if board_type and board_type in prefix_map:
        prefixes = prefix_map[board_type]
        all_stocks = [s for s in all_stocks if s["code"].startswith(prefixes)]

    # ST filter
    if exclude_st:
        all_stocks = [s for s in all_stocks if "ST" not in (s["name"] or "")]

    results = []
    for stock in all_stocks:
        # Get recent K-line, then restore chronological order for slope calculation.
        q = await db.execute(
            select(StockDailyQuote)
            .where(
                StockDailyQuote.stock_code == stock["code"],
                StockDailyQuote.adjust_type == "qfq",
            )
            .order_by(desc(StockDailyQuote.trade_date))
            .limit(period + 5)
        )
        rows = list(reversed(q.scalars().all()))
        if len(rows) < period:
            continue

        df = pd.DataFrame([
            {"close": r.close, "trade_date": r.trade_date}
            for r in rows
        ])

        if field.startswith("ma_"):
            ma_period = int(field.split("_", 1)[1])
            df[field] = df["close"].rolling(ma_period).mean()
            if df[field].isna().all():
                continue

        # Compute slope
        slope_series = compute_slope_pct(df, period=period, field=field)
        if slope_series.isna().all():
            continue
        last_slope = float(slope_series.iloc[-1])

        # Filter by trend range
        if min_val is not None and last_slope < min_val:
            continue
        if max_val is not None and last_slope > max_val:
            continue

        # Also compute recent change for display
        recent = rows[-1]
        ma5 = df["close"].rolling(5).mean().iloc[-1] if len(df) >= 5 else None
        ma20 = df["close"].rolling(20).mean().iloc[-1] if len(df) >= 20 else None

        results.append({
            "code": stock["code"],
            "name": stock["name"],
            "industry": stock.get("industry") or "",
            "slope": round(last_slope, 4),
            "close": recent.close,
            "change_pct": recent.change_pct,
            "volume": recent.volume,
            "amount": recent.amount,
            "ma5": round(float(ma5), 2) if ma5 and not pd.isna(ma5) else None,
            "ma20": round(float(ma20), 2) if ma20 and not pd.isna(ma20) else None,
            "trade_date": str(recent.trade_date),
        })

    # Sort by slope desc
    results.sort(key=lambda x: x["slope"], reverse=True)

    return ApiResponse(data={
        "trend": trend,
        "label": label["name"],
        "period": period,
        "items": results[:limit],
        "total": len(results),
    })
