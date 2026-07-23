"""Stock screener — multi-condition filtering across all A-stocks."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_info import StockInfo
from app.models.stock_quote import StockDailyQuote
from app.models.stock_financial import StockFinancialIndicator

logger = logging.getLogger(__name__)

# ── Condition DSL ─────────────────────────────────────────────────────────


@dataclass
class Condition:
    field: str
    op: str        # gt, lt, gte, lte, eq, between, golden_cross, death_cross
    value: Any = None
    value2: Any = None  # for 'between' op
    params: dict = field(default_factory=dict)  # extra params like fast, slow periods


# ── Screener ──────────────────────────────────────────────────────────────


class StockScreener:
    """Scan all stocks against a list of conditions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def scan(
        self,
        conditions: list[dict],
        sort_by: str = "code",
        limit: int = 50,
    ) -> dict:
        """Run screener and return matching stocks.

        conditions: list of dicts like:
            {"field": "roe", "op": "gt", "value": 15}
            {"field": "ma_cross", "op": "golden", "params": {"fast": 5, "slow": 20}}

        Returns: {results: [...], total: int, conditions: [...]}
        """
        parsed = [self._parse_cond(c) for c in conditions]

        # Get all active stocks
        result = await self.db.execute(
            select(StockInfo.code, StockInfo.name, StockInfo.industry)
            .where(StockInfo.is_active == True)
            .order_by(StockInfo.code)
        )
        stocks = [{"code": r[0], "name": r[1], "industry": r[2]} for r in result.fetchall()]

        # Apply each condition
        matched = stocks
        for cond in parsed:
            if not matched:
                break
            matched = await self._apply_condition(cond, matched)

        total = len(matched)
        # Sort
        if sort_by == "code":
            matched.sort(key=lambda s: s["code"])
        elif sort_by == "name":
            matched.sort(key=lambda s: s["name"])

        return {
            "results": matched[:limit],
            "total": total,
            "conditions": conditions,
        }

    # ── Condition Parsing ───────────────────────────────────────────────

    def _parse_cond(self, raw: dict) -> Condition:
        return Condition(
            field=raw["field"],
            op=raw["op"],
            value=raw.get("value"),
            value2=raw.get("value2"),
            params=raw.get("params", {}),
        )

    # ── Apply Condition ──────────────────────────────────────────────────

    async def _apply_condition(self, cond: Condition, stocks: list[dict]) -> list[dict]:
        if cond.field in ("roe", "eps_basic", "gross_margin", "revenue_growth", "profit_growth",
                          "debt_ratio", "current_ratio", "bvps"):
            return await self._filter_financial(cond, stocks)
        if cond.field in ("ma_cross", "macd_cross", "rsi"):
            return await self._filter_technical(cond, stocks)
        if cond.field == "pe":
            return await self._filter_pe(cond, stocks)
        logger.warning("Unknown field: %s", cond.field)
        return stocks

    async def _filter_financial(self, cond: Condition, stocks: list[dict]) -> list[dict]:
        codes = [s["code"] for s in stocks]
        # Get latest financial indicator for each stock
        from sqlalchemy import desc
        result = await self.db.execute(
            select(StockFinancialIndicator)
            .where(StockFinancialIndicator.stock_code.in_(codes))
            .order_by(StockFinancialIndicator.stock_code, desc(StockFinancialIndicator.report_date))
        )
        latest: dict[str, StockFinancialIndicator] = {}
        for r in result.scalars():
            if r.stock_code not in latest:
                latest[r.stock_code] = r

        op = cond.op
        val = cond.value
        matched = []
        for s in stocks:
            ind = latest.get(s["code"])
            if ind is None:
                continue
            field_val = getattr(ind, cond.field, None)
            if field_val is None:
                continue
            if self._compare(field_val, op, val, cond.value2):
                s[f"_{cond.field}"] = round(float(field_val), 2)
                matched.append(s)
        return matched

    async def _filter_technical(self, cond: Condition, stocks: list[dict]) -> list[dict]:
        """Technical indicator screening — scan recent K-line data."""
        from app.services.indicator_service import compute_ma, compute_macd, compute_rsi, detect_golden_cross

        matched = []
        for s in stocks:
            try:
                df = await self._get_recent_kline(s["code"], lookback=100)
                if df.empty or len(df) < 60:
                    continue

                if cond.field == "ma_cross":
                    fast = cond.params.get("fast", 5)
                    slow = cond.params.get("slow", 20)
                    ma_fast = compute_ma(df, fast)
                    ma_slow = compute_ma(df, slow)
                    if detect_golden_cross(ma_fast, ma_slow).iloc[-1]:
                        s["_signal"] = f"MA{fast}↑MA{slow}"
                        matched.append(s)

                elif cond.field == "macd_cross":
                    macd = compute_macd(df)
                    if detect_golden_cross(macd["dif"], macd["dea"]).iloc[-1]:
                        s["_signal"] = "MACD金叉"
                        matched.append(s)

                elif cond.field == "rsi":
                    rsi = compute_rsi(df, cond.params.get("period", 14))
                    last_rsi = float(rsi.iloc[-1])
                    op = cond.op
                    if self._compare(last_rsi, op, cond.value, cond.value2):
                        s["_rsi"] = round(last_rsi, 1)
                        matched.append(s)

            except Exception:
                continue  # skip problematic stocks silently
        return matched

    async def _filter_pe(self, cond: Condition, stocks: list[dict]) -> list[dict]:
        """PE screening — requires spot data (not yet available without sync).
        Fallback: skip PE for now."""
        logger.warning("PE screening requires spot data sync — skipping")
        return stocks  # pass-through for now

    async def _get_recent_kline(self, code: str, lookback: int = 100) -> pd.DataFrame:
        """Get recent daily K-line for a stock."""
        result = await self.db.execute(
            select(StockDailyQuote)
            .where(
                StockDailyQuote.stock_code == code,
                StockDailyQuote.adjust_type == "qfq",
            )
            .order_by(StockDailyQuote.trade_date.desc())
            .limit(lookback)
        )
        rows = result.scalars().all()
        if not rows:
            return pd.DataFrame()
        data = [
            {"open": r.open, "close": r.close, "high": r.high, "low": r.low, "volume": r.volume}
            for r in reversed(rows)
        ]
        return pd.DataFrame(data)

    @staticmethod
    def _compare(field_val: float, op: str, target: Any, target2: Any = None) -> bool:
        if op == "gt":
            return field_val > float(target)
        if op == "lt":
            return field_val < float(target)
        if op == "gte":
            return field_val >= float(target)
        if op == "lte":
            return field_val <= float(target)
        if op == "eq":
            return field_val == float(target)
        if op == "between":
            if target is None or target2 is None:
                return False
            lower = float(target)
            upper = float(target2)
            if lower > upper:
                lower, upper = upper, lower
            return lower <= field_val <= upper
        return False
