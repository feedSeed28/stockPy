"""Quant API endpoints — indicators, screener, backtest."""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import pandas as pd
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.stock_quote import StockDailyQuote
from app.schemas.common import ApiResponse
from app.services.indicator_service import INDICATOR_REGISTRY
from app.services.screener_service import StockScreener
from app.services.backtest_service import (
    BacktestRunner,
    STRATEGY_REGISTRY,
    BacktestResult,
)

router = APIRouter(prefix="/quant", tags=["quant"])


# ═══════════════════════════════════════════════════════════════════════════
# Indicators
# ═══════════════════════════════════════════════════════════════════════════

class IndicatorRequest(BaseModel):
    indicators: list[str] = Field(default=["ma"], description="Indicator names: ma, ema, macd, rsi, kdj, boll, atr, obv")
    params: dict[str, Any] = Field(default={}, description="Override default params, e.g. {'ma': {'period': 10}}")


@router.post("/stocks/{code}/indicators")
async def compute_indicators(
    code: str,
    req: IndicatorRequest,
    db: AsyncSession = Depends(get_db),
):
    """Compute technical indicators for a stock's recent K-line data."""
    # Fetch recent K-line
    result = await db.execute(
        select(StockDailyQuote)
        .where(
            StockDailyQuote.stock_code == code,
            StockDailyQuote.adjust_type == "qfq",
        )
        .order_by(StockDailyQuote.trade_date.asc())
        .limit(300)
    )
    rows = result.scalars().all()
    if not rows:
        return ApiResponse(code=404, message=f"No K-line data for {code}")

    df = pd.DataFrame([
        {"trade_date": str(r.trade_date), "open": r.open, "close": r.close,
         "high": r.high, "low": r.low, "volume": r.volume}
        for r in rows
    ])

    output: dict[str, list] = {"trade_date": df["trade_date"].tolist()}

    for name in req.indicators:
        if name not in INDICATOR_REGISTRY:
            continue
        fn, defaults = INDICATOR_REGISTRY[name]
        kwargs = {**defaults, **req.params.get(name, {})}
        result_data = fn(df, **kwargs)

        if isinstance(result_data, pd.DataFrame):
            for col in result_data.columns:
                output[f"{name}_{col}"] = [
                    None if pd.isna(v) else round(float(v), 4)
                    for v in result_data[col]
                ]
        else:
            output[name] = [
                None if pd.isna(v) else round(float(v), 4)
                for v in result_data
            ]

    return ApiResponse(data=output)


# ═══════════════════════════════════════════════════════════════════════════
# Screener
# ═══════════════════════════════════════════════════════════════════════════

class ScreenerRequest(BaseModel):
    conditions: list[dict] = Field(
        default=[{"field": "roe", "op": "gt", "value": 15}],
        description="List of filter conditions"
    )
    sort_by: str = Field(default="code")
    limit: int = Field(default=50, ge=1, le=200)


@router.post("/screener")
async def run_screener(req: ScreenerRequest, db: AsyncSession = Depends(get_db)):
    """Multi-condition stock screener."""
    screener = StockScreener(db)
    result = await screener.scan(
        conditions=req.conditions,
        sort_by=req.sort_by,
        limit=req.limit,
    )
    return ApiResponse(data=result)


# ═══════════════════════════════════════════════════════════════════════════
# Backtest
# ═══════════════════════════════════════════════════════════════════════════

class BacktestRequest(BaseModel):
    stock_code: str = Field(default="000001")
    strategy: str = Field(default="ma_cross", description="Strategy name: ma_cross, macd, rsi")
    params: dict = Field(default={}, description="Strategy params")
    start_date: Optional[date] = Field(default=None)
    end_date: Optional[date] = Field(default=None)
    initial_capital: float = Field(default=100000.0, ge=1000)


@router.post("/backtest")
async def run_backtest(req: BacktestRequest, db: AsyncSession = Depends(get_db)):
    """Run a strategy backtest."""
    # Fetch K-line
    stmt = select(StockDailyQuote).where(
        StockDailyQuote.stock_code == req.stock_code,
        StockDailyQuote.adjust_type == "qfq",
    ).order_by(StockDailyQuote.trade_date.asc())

    if req.start_date:
        stmt = stmt.where(StockDailyQuote.trade_date >= req.start_date)
    if req.end_date:
        stmt = stmt.where(StockDailyQuote.trade_date <= req.end_date)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    if len(rows) < 60:
        return ApiResponse(code=400, message=f"Need at least 60 bars, got {len(rows)}")

    df = pd.DataFrame([
        {"trade_date": r.trade_date, "open": r.open, "close": r.close,
         "high": r.high, "low": r.low, "volume": r.volume}
        for r in rows
    ])

    # Instantiate strategy
    if req.strategy not in STRATEGY_REGISTRY:
        return ApiResponse(code=400, message=f"Unknown strategy: {req.strategy}")

    strat_cls = STRATEGY_REGISTRY[req.strategy]
    strategy = strat_cls(**req.params)

    runner = BacktestRunner(initial_capital=req.initial_capital)
    report = runner.run(
        df=df,
        strategy=strategy,
        strategy_name=req.strategy,
        stock_code=req.stock_code,
    )

    return ApiResponse(data={
        "strategy_name": report.strategy_name,
        "stock_code": report.stock_code,
        "start_date": str(report.start_date),
        "end_date": str(report.end_date),
        "initial_capital": report.initial_capital,
        "final_equity": report.final_equity,
        "total_return_pct": report.total_return,
        "annual_return_pct": report.annual_return,
        "max_drawdown_pct": report.max_drawdown,
        "sharpe_ratio": report.sharpe_ratio,
        "win_rate_pct": report.win_rate,
        "trade_count": report.trade_count,
        "equity_curve": report.equity_curve[-100:],  # last 100 points for chart
        "trades": report.trades[-20:],  # last 20 trades
    })


# ═══════════════════════════════════════════════════════════════════════════
# Strategy list
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/strategies")
async def list_strategies():
    """List available backtest strategies and their params."""
    return ApiResponse(data={
        "ma_cross": {"params": {"fast": 5, "slow": 20}, "description": "MA golden cross buy, death cross sell"},
        "macd": {"params": {"fast": 12, "slow": 26, "signal": 9}, "description": "MACD DIF/DEA cross"},
        "rsi": {"params": {"period": 14, "oversold": 30, "overbought": 70}, "description": "RSI overbought/oversold"},
    })
