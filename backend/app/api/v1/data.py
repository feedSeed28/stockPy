"""数据管理 API — 同步状态查询 & 手动触发同步."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.sync_status import SyncStatus
from app.schemas.common import ApiResponse
from app.tasks.sync_tasks import (
    sync_daily_kline_incremental,
    sync_fund_flow_daily,
    sync_performance_reports,
    sync_stock_list_weekly,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/data", tags=["data"])

# ── 表名中文映射 ──────────────────────────────────────────────────────────

_TABLE_LABELS = {
    "stock_info": "股票列表",
    "stock_daily_quote": "日K线",
    "stock_weekly_quote": "周K线",
    "stock_monthly_quote": "月K线",
    "stock_financial_indicator": "财务指标",
    "stock_performance_report": "业绩报表",
    "stock_profit_forecast": "盈利预测",
    "stock_fund_flow_daily": "资金流",
    "stock_board_info": "板块信息",
    "stock_board_member": "板块成员",
}

# ── 手动触发映射 ──────────────────────────────────────────────────────────

_TRIGGER_MAP = {
    "stock_info": sync_stock_list_weekly,
    "stock_daily_quote": sync_daily_kline_incremental,
    "stock_fund_flow_daily": sync_fund_flow_daily,
    "stock_performance_report": sync_performance_reports,
}


class TriggerRequest(BaseModel):
    table: str


@router.get("/sync-status")
async def get_sync_status(db: AsyncSession = Depends(get_db)):
    """获取所有表的同步状态."""
    result = await db.execute(select(SyncStatus).order_by(SyncStatus.table_name))
    rows = result.scalars().all()

    items = []
    for r in rows:
        items.append({
            "table_name": r.table_name,
            "table_label": _TABLE_LABELS.get(r.table_name, r.table_name),
            "last_sync_time": r.last_sync_time.isoformat() if r.last_sync_time else None,
            "last_data_date": str(r.last_data_date) if r.last_data_date else None,
            "row_count": r.row_count,
            "status": r.status,
            "error_message": r.error_message,
        })

    # 补上没有记录的默认表
    existing = {r.table_name for r in rows}
    for name, label in _TABLE_LABELS.items():
        if name not in existing:
            items.append({
                "table_name": name,
                "table_label": label,
                "last_sync_time": None,
                "last_data_date": None,
                "row_count": None,
                "status": "pending",
                "error_message": None,
            })

    return ApiResponse(data={"items": items, "total": len(items)})


@router.post("/trigger-sync")
async def trigger_sync(req: TriggerRequest):
    """手动触发某张表的同步（异步执行，不阻塞）."""
    import asyncio

    fn = _TRIGGER_MAP.get(req.table)
    if fn is None:
        return ApiResponse(
            code=400,
            message=f"不支持的同步表: {req.table}。支持: {list(_TRIGGER_MAP.keys())}",
        )

    try:
        # Fire and forget — 不阻塞 HTTP 响应
        asyncio.create_task(fn())
        label = _TABLE_LABELS.get(req.table, req.table)
        return ApiResponse(message=f"{label} 同步已触发，将在后台执行")
    except Exception as e:
        return ApiResponse(code=500, message=f"触发失败: {str(e)[:100]}")
