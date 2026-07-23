"""Strategy backtesting engine.

Strategy → BacktestRunner → Performance Report
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

import numpy as np
import pandas as pd

from app.services.indicator_service import detect_death_cross, detect_golden_cross


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
    pnl: float | None = None
    pnl_pct: float | None = None


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
        slippage: float = 0.001,     # 千分之一
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage

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

            if pending_signal == Signal.BUY and position == 0 and cash > 0:
                # Execute yesterday's signal at today's open.
                buy_price = open_price * (1 + self.slippage)
                shares = int(cash * 0.95 / (buy_price * (1 + self.commission)))
                if shares > 0:
                    cost = shares * buy_price * (1 + self.commission)
                    cash -= cost
                    position = shares
                    trades.append(Trade(buy_date=bar_date, buy_price=buy_price, shares=shares))

            elif pending_signal == Signal.SELL and position > 0:
                sell_price = open_price * (1 - self.slippage)
                revenue = position * sell_price * (1 - self.commission)
                cash += revenue
                # Close the last open trade
                open_trade = next((t for t in reversed(trades) if t.sell_date is None), None)
                if open_trade:
                    open_trade.sell_date = bar_date
                    open_trade.sell_price = sell_price
                    open_trade.pnl = (sell_price - open_trade.buy_price) * open_trade.shares
                    open_trade.pnl_pct = (sell_price / open_trade.buy_price - 1) * 100
                position = 0.0

            equity = cash + position * close_price
            equity_curve.append({"date": str(bar_date), "equity": round(equity, 2)})
            pending_signal = strategy.on_bar(
                idx=idx,
                bar_date=bar_date,
                df=df,
                indicators=indicators,
                position=position,
                cash=cash,
            )

        # Close any remaining position at last price
        if position > 0:
            last_price = float(df["close"].iloc[-1])
            revenue = position * last_price * (1 - self.commission)
            cash += revenue
            open_trade = next((t for t in reversed(trades) if t.sell_date is None), None)
            if open_trade:
                open_trade.sell_date = df["trade_date"].iloc[-1] if "trade_date" in df.columns else df.index[-1]
                open_trade.sell_price = last_price
                open_trade.pnl = (last_price - open_trade.buy_price) * open_trade.shares
                open_trade.pnl_pct = (last_price / open_trade.buy_price - 1) * 100
            position = 0.0
            if equity_curve:
                equity_curve[-1]["equity"] = round(cash, 2)

        return self._compute_metrics(
            equity_curve=equity_curve,
            trades=trades,
            strategy_name=strategy_name or strategy.__class__.__name__,
            stock_code=stock_code,
            start_date=df["trade_date"].iloc[0] if "trade_date" in df.columns else df.index[0],
            end_date=df["trade_date"].iloc[-1] if "trade_date" in df.columns else df.index[-1],
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    def _compute_indicators(self, df: pd.DataFrame, strategy: BaseStrategy) -> dict:
        """Compute indicators needed by strategy type."""
        indicators: dict = {}
        if isinstance(strategy, MaCrossStrategy):
            from app.services.indicator_service import compute_ma
            indicators[f"ma_{strategy.fast}"] = compute_ma(df, strategy.fast)
            indicators[f"ma_{strategy.slow}"] = compute_ma(df, strategy.slow)
        elif isinstance(strategy, MacdStrategy):
            from app.services.indicator_service import compute_macd
            indicators["macd"] = compute_macd(df, strategy.fast, strategy.slow, strategy.signal)
        elif isinstance(strategy, RsiStrategy):
            from app.services.indicator_service import compute_rsi
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
                    "pnl": round(t.pnl, 2) if t.pnl is not None else None,
                    "pnl_pct": round(t.pnl_pct, 2) if t.pnl_pct is not None else None,
                }
                for t in trades
            ],
        )
