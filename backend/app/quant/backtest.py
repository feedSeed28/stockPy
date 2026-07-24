"""Strategy backtesting engine.

Strategy → BacktestRunner → Performance Report
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

import numpy as np
import pandas as pd

from app.quant.indicators import detect_death_cross, detect_golden_cross


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


# ── Strategy Base ─────────────────────────────────────────────────────────


class BaseStrategy:
    """Abstract base for all trading strategies."""

    def on_bar(
        self,
        idx: int,
        bar_date: date,
        df: pd.DataFrame,
        indicators: dict[str, pd.Series | pd.DataFrame],
        position: float,
        cash: float,
    ) -> Signal:
        """Evaluate one bar. Override this in subclasses."""
        return Signal.HOLD


# ── Built-in Strategies ───────────────────────────────────────────────────


class MaCrossStrategy(BaseStrategy):
    """Golden cross BUY, death cross SELL."""

    def __init__(self, fast: int = 5, slow: int = 20):
        self.fast = fast
        self.slow = slow

    def on_bar(self, idx, bar_date, df, indicators, position, cash):
        if idx < self.slow:
            return Signal.HOLD
        ma_fast = indicators[f"ma_{self.fast}"]
        ma_slow = indicators[f"ma_{self.slow}"]
        if detect_golden_cross(ma_fast, ma_slow).iloc[idx] and position == 0:
            return Signal.BUY
        if detect_death_cross(ma_fast, ma_slow).iloc[idx] and position > 0:
            return Signal.SELL
        return Signal.HOLD


class MacdStrategy(BaseStrategy):
    """MACD golden cross BUY, death cross SELL."""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def on_bar(self, idx, bar_date, df, indicators, position, cash):
        if idx < self.slow + self.signal:
            return Signal.HOLD
        macd = indicators["macd"]
        dif = macd["dif"]
        dea = macd["dea"]
        if detect_golden_cross(dif, dea).iloc[idx] and position == 0:
            return Signal.BUY
        if detect_death_cross(dif, dea).iloc[idx] and position > 0:
            return Signal.SELL
        return Signal.HOLD


class RsiStrategy(BaseStrategy):
    """Oversold (<30) BUY, overbought (>70) SELL."""

    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def on_bar(self, idx, bar_date, df, indicators, position, cash):
        if idx < self.period:
            return Signal.HOLD
        rsi = indicators[f"rsi_{self.period}"]
        if rsi.iloc[idx] < self.oversold and position == 0:
            return Signal.BUY
        if rsi.iloc[idx] > self.overbought and position > 0:
            return Signal.SELL
        return Signal.HOLD


STRATEGY_REGISTRY = {
    "ma_cross": MaCrossStrategy,
    "macd": MacdStrategy,
    "rsi": RsiStrategy,
}


# ── Trade Record ──────────────────────────────────────────────────────────


@dataclass
class Trade:
    buy_date: date
    buy_price: float
    sell_date: date | None = None
    sell_price: float | None = None
    shares: int = 0
    buy_cost: float = 0.0
    buy_fee: float = 0.0
    sell_amount: float | None = None
    sell_fee: float | None = None
    stamp_tax: float | None = None
    pnl: float | None = None
    pnl_pct: float | None = None
    exit_reason: str | None = None


# ── Backtest Result ───────────────────────────────────────────────────────


@dataclass
class BacktestResult:
    strategy_name: str
    stock_code: str
    start_date: date
    end_date: date
    initial_capital: float
    final_equity: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    trade_count: int
    equity_curve: list[dict]  # [{date, equity}, ...]
    trades: list[dict]


# ── Backtest Runner ───────────────────────────────────────────────────────


class BacktestRunner:
    """Run a strategy against historical data and compute performance."""

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission: float = 0.0003,  # 万三
        stamp_tax: float = 0.0005,   # sell-side stamp tax, configurable
        min_commission: float = 5.0,
        slippage: float = 0.001,     # 千分之一
        lot_size: int = 100,
        cash_usage: float = 0.95,
        enforce_t1: bool = True,
        enforce_price_limit: bool = True,
        skip_suspended: bool = True,
        is_st: bool = False,
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.stamp_tax = stamp_tax
        self.min_commission = min_commission
        self.slippage = slippage
        self.lot_size = lot_size
        self.cash_usage = cash_usage
        self.enforce_t1 = enforce_t1
        self.enforce_price_limit = enforce_price_limit
        self.skip_suspended = skip_suspended
        self.is_st = is_st

    def run(
        self,
        df: pd.DataFrame,
        strategy: BaseStrategy,
        strategy_name: str = "",
        stock_code: str = "",
    ) -> BacktestResult:
        """Execute backtest and return performance report."""
        cash = self.initial_capital
        position = 0.0  # shares held
        trades: list[Trade] = []
        equity_curve: list[dict] = []
        pending_signal = Signal.HOLD

        # Pre-compute indicators needed by the strategy
        indicators = self._compute_indicators(df, strategy)

        for idx in range(len(df)):
            bar_date = df.index[idx] if isinstance(df.index[idx], date) else df["trade_date"].iloc[idx]
            open_price = float(df["open"].iloc[idx])
            close_price = float(df["close"].iloc[idx])
            tradable = self._is_tradable_bar(df, idx)

            if (
                pending_signal == Signal.BUY
                and position == 0
                and cash > 0
                and tradable
                and not self._blocked_by_price_limit(df, idx, "buy", stock_code)
            ):
                # Execute yesterday's signal at today's open.
                buy_price = open_price * (1 + self.slippage)
                shares = self._calc_buy_shares(cash, buy_price)
                if shares > 0:
                    amount = shares * buy_price
                    buy_fee = self._commission_fee(amount)
                    cost = amount + buy_fee
                    cash -= cost
                    position = shares
                    trades.append(
                        Trade(
                            buy_date=bar_date,
                            buy_price=buy_price,
                            shares=shares,
                            buy_cost=cost,
                            buy_fee=buy_fee,
                        )
                    )

            elif (
                pending_signal == Signal.SELL
                and position > 0
                and tradable
                and not self._blocked_by_price_limit(df, idx, "sell", stock_code)
            ):
                open_trade = next((t for t in reversed(trades) if t.sell_date is None), None)
                if not (self.enforce_t1 and open_trade and open_trade.buy_date == bar_date):
                    sell_price = open_price * (1 - self.slippage)
                    sell_amount = position * sell_price
                    sell_fee = self._commission_fee(sell_amount)
                    stamp_tax = sell_amount * self.stamp_tax
                    revenue = sell_amount - sell_fee - stamp_tax
                    cash += revenue
                    if open_trade:
                        open_trade.sell_date = bar_date
                        open_trade.sell_price = sell_price
                        open_trade.sell_amount = sell_amount
                        open_trade.sell_fee = sell_fee
                        open_trade.stamp_tax = stamp_tax
                        open_trade.pnl = revenue - open_trade.buy_cost
                        open_trade.pnl_pct = (
                            (open_trade.pnl / open_trade.buy_cost) * 100
                            if open_trade.buy_cost
                            else None
                        )
                        open_trade.exit_reason = "signal"
                    position = 0.0

            mark_price = close_price if close_price > 0 else open_price
            equity = cash + position * mark_price
            equity_curve.append({"date": str(bar_date), "equity": round(equity, 2)})
            pending_signal = strategy.on_bar(
                idx=idx,
                bar_date=bar_date,
                df=df,
                indicators=indicators,
                position=position,
                cash=cash,
            )

        # Mark any remaining position at last close without assuming it can be sold.
        if position > 0:
            last_price = float(df["close"].iloc[-1])
            last_date = df["trade_date"].iloc[-1] if "trade_date" in df.columns else df.index[-1]
            open_trade = next((t for t in reversed(trades) if t.sell_date is None), None)
            if open_trade:
                sell_amount = position * last_price
                open_trade.sell_date = last_date
                open_trade.sell_price = last_price
                open_trade.sell_amount = sell_amount
                open_trade.sell_fee = 0.0
                open_trade.stamp_tax = 0.0
                open_trade.pnl = sell_amount - open_trade.buy_cost
                open_trade.pnl_pct = (
                    (open_trade.pnl / open_trade.buy_cost) * 100
                    if open_trade.buy_cost
                    else None
                )
                open_trade.exit_reason = "mark_to_market"
            if equity_curve:
                equity_curve[-1]["equity"] = round(cash + position * last_price, 2)

        return self._compute_metrics(
            equity_curve=equity_curve,
            trades=trades,
            strategy_name=strategy_name or strategy.__class__.__name__,
            stock_code=stock_code,
            start_date=df["trade_date"].iloc[0] if "trade_date" in df.columns else df.index[0],
            end_date=df["trade_date"].iloc[-1] if "trade_date" in df.columns else df.index[-1],
        )

    # ── Trading Rules ───────────────────────────────────────────────────

    def _commission_fee(self, amount: float) -> float:
        if amount <= 0:
            return 0.0
        return max(amount * self.commission, self.min_commission)

    def _calc_buy_shares(self, cash: float, buy_price: float) -> int:
        if buy_price <= 0 or self.lot_size <= 0:
            return 0
        budget = cash * self.cash_usage
        shares = int(budget / buy_price / self.lot_size) * self.lot_size
        while shares > 0:
            amount = shares * buy_price
            if amount + self._commission_fee(amount) <= budget:
                return shares
            shares -= self.lot_size
        return 0

    def _is_tradable_bar(self, df: pd.DataFrame, idx: int) -> bool:
        if not self.skip_suspended:
            return True
        if any(float(df[col].iloc[idx]) <= 0 for col in ("open", "close", "high", "low")):
            return False
        if "volume" in df.columns and float(df["volume"].iloc[idx]) <= 0:
            return False
        return True

    def _price_limit_pct(self, stock_code: str) -> float:
        if self.is_st:
            return 0.05
        if stock_code.startswith(("300", "301", "688")):
            return 0.20
        if stock_code.startswith(("8", "4", "92")):
            return 0.30
        return 0.10

    def _blocked_by_price_limit(
        self, df: pd.DataFrame, idx: int, side: str, stock_code: str
    ) -> bool:
        if not self.enforce_price_limit or idx <= 0:
            return False
        prev_close = float(df["close"].iloc[idx - 1])
        open_price = float(df["open"].iloc[idx])
        if prev_close <= 0 or open_price <= 0:
            return False
        limit_pct = self._price_limit_pct(stock_code)
        change = open_price / prev_close - 1
        tolerance = 0.001
        if side == "buy":
            return change >= limit_pct - tolerance
        if side == "sell":
            return change <= -limit_pct + tolerance
        return False

    # ── Helpers ──────────────────────────────────────────────────────────

    def _compute_indicators(self, df: pd.DataFrame, strategy: BaseStrategy) -> dict:
        """Compute indicators needed by strategy type."""
        indicators: dict = {}
        if isinstance(strategy, MaCrossStrategy):
            from app.quant.indicators import compute_ma
            indicators[f"ma_{strategy.fast}"] = compute_ma(df, strategy.fast)
            indicators[f"ma_{strategy.slow}"] = compute_ma(df, strategy.slow)
        elif isinstance(strategy, MacdStrategy):
            from app.quant.indicators import compute_macd
            indicators["macd"] = compute_macd(df, strategy.fast, strategy.slow, strategy.signal)
        elif isinstance(strategy, RsiStrategy):
            from app.quant.indicators import compute_rsi
            indicators[f"rsi_{strategy.period}"] = compute_rsi(df, strategy.period)
        return indicators

    def _compute_metrics(
        self,
        equity_curve: list[dict],
        trades: list[Trade],
        strategy_name: str,
        stock_code: str,
        start_date: date,
        end_date: date,
    ) -> BacktestResult:
        equities = np.array([e["equity"] for e in equity_curve])
        final_equity = float(equities[-1])
        total_return = float((final_equity / self.initial_capital - 1) * 100)

        # Annualized return
        days = max((end_date - start_date).days, 1)
        annual_return = float(
            ((final_equity / self.initial_capital) ** (365.0 / days) - 1) * 100
        )

        # Max drawdown
        peak = np.maximum.accumulate(equities)
        drawdowns = (equities - peak) / peak * 100
        max_drawdown = float(drawdowns.min())

        # Sharpe ratio (assuming risk-free = 3%)
        daily_returns = np.diff(equities) / equities[:-1]
        if len(daily_returns) > 1 and daily_returns.std() > 0:
            sharpe = float(
                (daily_returns.mean() * 252 - 0.03)
                / (daily_returns.std() * np.sqrt(252))
            )
        else:
            sharpe = 0.0

        # Win rate
        completed = [t for t in trades if t.sell_date is not None]
        if completed:
            win_rate = sum(1 for t in completed if (t.pnl or 0) > 0) / len(completed) * 100
        else:
            win_rate = 0.0

        return BacktestResult(
            strategy_name=strategy_name,
            stock_code=stock_code,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            final_equity=round(final_equity, 2),
            total_return=round(total_return, 2),
            annual_return=round(annual_return, 2),
            max_drawdown=round(max_drawdown, 2),
            sharpe_ratio=round(sharpe, 2),
            win_rate=round(win_rate, 2),
            trade_count=len(trades),
            equity_curve=equity_curve,
            trades=[
                {
                    "buy_date": str(t.buy_date),
                    "buy_price": t.buy_price,
                    "sell_date": str(t.sell_date) if t.sell_date else None,
                    "sell_price": t.sell_price,
                    "shares": t.shares,
                    "buy_fee": round(t.buy_fee, 2),
                    "sell_fee": round(t.sell_fee, 2) if t.sell_fee is not None else None,
                    "stamp_tax": round(t.stamp_tax, 2) if t.stamp_tax is not None else None,
                    "pnl": round(t.pnl, 2) if t.pnl is not None else None,
                    "pnl_pct": round(t.pnl_pct, 2) if t.pnl_pct is not None else None,
                    "exit_reason": t.exit_reason,
                }
                for t in trades
            ],
        )
