"""数据管理 API — 同步状态查询、手动触发同步、静态数据导出."""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
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

_BACKEND_DIR = Path(__file__).resolve().parents[3]
_EXPORT_SCRIPT = _BACKEND_DIR / "scripts" / "export_frontend_data.py"
_export_status: dict[str, Any] = {
    "status": "idle",
    "started_at": None,
    "finished_at": None,
    "output_dir": None,
    "command": None,
    "returncode": None,
    "stdout_tail": "",
    "stderr_tail": "",
    "error_message": None,
}


class TriggerRequest(BaseModel):
    table: str


class ExportStaticRequest(BaseModel):
    symbols: str | None = Field(
        default=None,
        description="逗号分隔股票代码；为空则只导出股票列表/行情/板块等轻量数据",
    )
    all_kline: bool = Field(default=False, description="是否导出所有活跃股票K线")
    kline_limit: int = Field(default=500, ge=1, le=5000, description="每只股票每周期最多导出K线条数")
    periods: str = Field(default="daily", description="K线周期：daily,weekly,monthly，可逗号分隔")
    include_board_members: bool = Field(default=True, description="是否导出板块成分股文件")
    out: str | None = Field(default=None, description="可选输出目录；默认 frontend/public/data")


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


@router.post("/export-static")
async def export_static_data(req: ExportStaticRequest):
    """触发前端静态 JSON 数据导出（后台执行，不阻塞 HTTP 响应）."""
    if _export_status["status"] == "running":
        return ApiResponse(code=409, message="已有导出任务正在执行", data=_export_status)

    if req.all_kline and not req.symbols:
        logger.warning("Full-market K-line static export requested from UI")

    _export_status.update({
        "status": "queued",
        "started_at": None,
        "finished_at": None,
        "returncode": None,
        "stdout_tail": "",
        "stderr_tail": "",
        "error_message": None,
    })
    asyncio.create_task(_run_static_export(req))
    return ApiResponse(message="静态数据导出已触发，将在后台执行", data=_export_status)


@router.get("/export-static/status")
async def get_export_static_status():
    """获取最近一次静态数据导出状态."""
    return ApiResponse(data=_export_status)


async def _run_static_export(req: ExportStaticRequest):
    started_at = datetime.now()
    cmd = [
        sys.executable,
        str(_EXPORT_SCRIPT),
        "--kline-limit",
        str(req.kline_limit),
        "--periods",
        req.periods,
    ]
    if req.symbols:
        cmd.extend(["--symbols", req.symbols])
    if req.all_kline:
        cmd.append("--all-kline")
    if not req.include_board_members:
        cmd.append("--no-board-members")
    if req.out:
        cmd.extend(["--out", req.out])

    _export_status.update({
        "status": "running",
        "started_at": started_at.isoformat(timespec="seconds"),
        "finished_at": None,
        "output_dir": req.out,
        "command": " ".join(cmd),
        "returncode": None,
        "stdout_tail": "",
        "stderr_tail": "",
        "error_message": None,
    })

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(_BACKEND_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        _export_status.update({
            "status": "success" if proc.returncode == 0 else "error",
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "returncode": proc.returncode,
            "stdout_tail": stdout_text[-4000:],
            "stderr_tail": stderr_text[-4000:],
            "error_message": None if proc.returncode == 0 else stderr_text[-500:],
        })
    except Exception as e:
        logger.exception("Static export failed")
        _export_status.update({
            "status": "error",
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "returncode": None,
            "error_message": str(e),
        })
