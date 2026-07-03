"""龙虎榜 API — Sina data source (实时，不存数据库)."""

from datetime import date
from typing import Optional

import akshare as ak
import pandas as pd
from fastapi import APIRouter, Query

from app.schemas.common import ApiResponse

router = APIRouter(prefix="/lhb", tags=["lhb"])


@router.get("/daily")
async def get_lhb_daily(
    date_str: Optional[str] = Query(None, alias="date", description="日期 YYYYMMDD"),
    reason: Optional[str] = Query(None, description="上榜原因筛选（模糊匹配）"),
):
    """每日龙虎榜上榜股票列表。

    返回上榜股票的汇总信息：代码、名称、收盘价、成交量、成交额、上榜原因。
    支持按上榜原因筛选（如"涨幅偏离值达7%"）。
    """
    try:
        target = date_str or date.today().strftime("%Y%m%d")
        df = ak.stock_lhb_detail_daily_sina(date=target)

        if df.empty:
            return ApiResponse(data={"date": target, "items": [], "total": 0})

        if reason:
            df = df[df["上榜原因"].astype(str).str.contains(reason, na=False)]

        items = []
        for _, r in df.iterrows():
            items.append({
                "code": str(r.get("股票代码", "")).zfill(6),
                "name": str(r.get("股票名称", "")),
                "close": float(r.get("收盘价", 0)) if pd.notna(r.get("收盘价")) else None,
                "change_val": float(r.get("对应值", 0)) if pd.notna(r.get("对应值")) else None,
                "volume": float(r.get("成交量", 0)) if pd.notna(r.get("成交量")) else None,
                "amount": float(r.get("成交额", 0)) if pd.notna(r.get("成交额")) else None,
                "reason": str(r.get("上榜原因", "")),
            })

        # Collect unique reasons for filter dropdown
        reasons = sorted(df["上榜原因"].dropna().unique().tolist())

        return ApiResponse(data={
            "date": target,
            "items": items,
            "total": len(items),
            "reasons": reasons,
        })

    except Exception as e:
        return ApiResponse(code=503, message=f"数据源不可用: {str(e)[:100]}",
                           data={"items": [], "total": 0, "reasons": []})


@router.get("/institution")
async def get_lhb_institution():
    """机构席位买卖明细。

    返回最近交易日机构席位在各股票上的买入额/卖出额。
    """
    try:
        df = ak.stock_lhb_jgmx_sina()

        if df.empty:
            return ApiResponse(data={"items": [], "total": 0})

        items = []
        for _, r in df.iterrows():
            items.append({
                "code": str(r.get("股票代码", "")).zfill(6),
                "name": str(r.get("股票名称", "")),
                "trade_date": str(r.get("交易日期", "")),
                "institution_buy": float(r.get("机构席位买入额", 0)) if pd.notna(r.get("机构席位买入额")) else 0,
                "institution_sell": float(r.get("机构席位卖出额", 0)) if pd.notna(r.get("机构席位卖出额")) else 0,
                "reason": str(r.get("上榜原因", "")) if pd.notna(r.get("上榜原因")) else "",
            })

        return ApiResponse(data={"items": items, "total": len(items)})

    except Exception as e:
        return ApiResponse(code=503, message=f"数据源不可用: {str(e)[:100]}",
                           data={"items": [], "total": 0})


@router.get("/stock-stats")
async def get_lhb_stock_stats(
    period: str = Query("5", description="统计周期: 5/10/30/60 日"),
):
    """个股上榜次数统计。

    返回最近N日上榜次数最多的股票排名。
    """
    try:
        df = ak.stock_lhb_ggtj_sina(symbol=period)

        if df.empty:
            return ApiResponse(data={"items": [], "total": 0})

        items = []
        for _, r in df.iterrows():
            items.append({
                "code": str(r.get("股票代码", "")).zfill(6),
                "name": str(r.get("股票名称", "")),
                "appear_count": int(r.get("上榜次数", 0)) if pd.notna(r.get("上榜次数")) else 0,
                "total_buy": float(r.get("累积购买额", 0)) if pd.notna(r.get("累积购买额")) else 0,
                "total_sell": float(r.get("累积卖出额", 0)) if pd.notna(r.get("累积卖出额")) else 0,
                "net_amount": float(r.get("净买入额", 0)) if pd.notna(r.get("净买入额")) else 0,
            })

        return ApiResponse(data={"items": items, "total": len(items), "period": f"{period}日"})

    except Exception as e:
        return ApiResponse(code=503, message=f"数据源不可用: {str(e)[:100]}",
                           data={"items": [], "total": 0})
