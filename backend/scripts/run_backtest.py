"""Run a single-stock strategy backtest from the command line.

Usage (from backend/):
    PYTHONUTF8=1 python scripts/run_backtest.py --stock 000001 --strategy ma_cross
    PYTHONUTF8=1 python scripts/run_backtest.py --stock 600000 --start 2020-01-01 --end 2024-12-31 --json-out reports/600000.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session
from app.models.stock_info import StockInfo
from app.models.stock_quote import StockDailyQuote
from app.quant.backtest import BacktestRunner, STRATEGY_REGISTRY


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def parse_strategy_params(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise ValueError("strategy params must be a JSON object")
        return parsed
    except json.JSONDecodeError as e:
        raise argparse.ArgumentTypeError(f"invalid JSON params: {e}") from e


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a single-stock A-share backtest from local MySQL data.")
    parser.add_argument("--stock", required=True, help="6-digit stock code, e.g. 000001")
    parser.add_argument("--strategy", default="ma_cross", choices=sorted(STRATEGY_REGISTRY.keys()))
    parser.add_argument("--params", help='Strategy params JSON, e.g. \'{"fast":5,"slow":20}\'')
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD")
    parser.add_argument("--capital", type=float, default=100000.0)
    parser.add_argument("--commission", type=float, default=0.0003)
    parser.add_argument("--stamp-tax", type=float, default=0.0005)
    parser.add_argument("--min-commission", type=float, default=5.0)
    parser.add_argument("--slippage", type=float, default=0.001)
    parser.add_argument("--lot-size", type=int, default=100)
    parser.add_argument("--cash-usage", type=float, default=0.95)
    parser.add_argument("--allow-st", action="store_true", help="Allow ST stocks; default rejects them")
    parser.add_argument("--no-t1", action="store_true", help="Disable T+1 sell restriction")
    parser.add_argument("--no-price-limit", action="store_true", help="Disable price-limit execution blocks")
    parser.add_argument("--include-suspended", action="store_true", help="Allow zero-volume/invalid-price bars")
    parser.add_argument("--json-out", help="Optional output JSON file")
    return parser.parse_args()


async def load_backtest_frame(stock: str, start: date | None, end: date | None) -> tuple[pd.DataFrame, StockInfo | None]:
    async with async_session() as db:
        stock_info = await db.get(StockInfo, stock)
        stmt = (
            select(StockDailyQuote)
            .where(
                StockDailyQuote.stock_code == stock,
                StockDailyQuote.adjust_type == "qfq",
            )
            .order_by(StockDailyQuote.trade_date.asc())
        )
        if start:
            stmt = stmt.where(StockDailyQuote.trade_date >= start)
        if end:
            stmt = stmt.where(StockDailyQuote.trade_date <= end)
        result = await db.execute(stmt)
        rows = result.scalars().all()

    df = pd.DataFrame([
        {
            "trade_date": r.trade_date,
            "open": r.open,
            "close": r.close,
            "high": r.high,
            "low": r.low,
            "volume": r.volume,
        }
        for r in rows
    ])
    return df, stock_info


def report_to_dict(report) -> dict[str, Any]:
    return {
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
        "equity_curve": report.equity_curve,
        "trades": report.trades,
    }


async def main() -> None:
    args = parse_args()
    stock = args.stock.strip().zfill(6)
    params = parse_strategy_params(args.params)
    df, stock_info = await load_backtest_frame(stock, parse_date(args.start), parse_date(args.end))
    if len(df) < 60:
        raise SystemExit(f"Need at least 60 bars, got {len(df)}")

    is_st = bool(stock_info and stock_info.name and "ST" in stock_info.name.upper())
    if is_st and not args.allow_st:
        raise SystemExit(f"{stock} is ST; use --allow-st to backtest it")

    strategy = STRATEGY_REGISTRY[args.strategy](**params)
    runner = BacktestRunner(
        initial_capital=args.capital,
        commission=args.commission,
        stamp_tax=args.stamp_tax,
        min_commission=args.min_commission,
        slippage=args.slippage,
        lot_size=args.lot_size,
        cash_usage=args.cash_usage,
        enforce_t1=not args.no_t1,
        enforce_price_limit=not args.no_price_limit,
        skip_suspended=not args.include_suspended,
        is_st=is_st,
    )
    report = runner.run(df, strategy, strategy_name=args.strategy, stock_code=stock)
    payload = report_to_dict(report)

    print(
        f"{stock} {args.strategy}: final={report.final_equity:,.2f}, "
        f"return={report.total_return:.2f}%, mdd={report.max_drawdown:.2f}%, "
        f"sharpe={report.sharpe_ratio:.2f}, trades={report.trade_count}"
    )

    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON written: {out}")


if __name__ == "__main__":
    asyncio.run(main())
