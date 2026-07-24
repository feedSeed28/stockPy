from datetime import date, timedelta

import pandas as pd

from app.quant.backtest import BacktestRunner, BaseStrategy, Signal


class BuyAndHoldStrategy(BaseStrategy):
    def on_bar(self, idx, bar_date, df, indicators, position, cash):
        return Signal.BUY if idx == 0 and position == 0 else Signal.HOLD


class BuyThenSellStrategy(BaseStrategy):
    def on_bar(self, idx, bar_date, df, indicators, position, cash):
        if idx == 0 and position == 0:
            return Signal.BUY
        if idx == 1 and position > 0:
            return Signal.SELL
        return Signal.HOLD


def make_df(opens: list[float], closes: list[float] | None = None, volumes: list[int] | None = None):
    closes = closes or opens
    volumes = volumes or [1000] * len(opens)
    rows = []
    for idx, open_price in enumerate(opens):
        close_price = closes[idx]
        rows.append({
            "trade_date": date(2024, 1, 1) + timedelta(days=idx),
            "open": open_price,
            "close": close_price,
            "high": max(open_price, close_price),
            "low": min(open_price, close_price),
            "volume": volumes[idx],
        })
    return pd.DataFrame(rows)


def test_buy_uses_next_open_and_round_lot():
    df = make_df([10.0, 10.0, 10.5])
    report = BacktestRunner(
        initial_capital=10000,
        slippage=0,
        min_commission=0,
        enforce_price_limit=False,
    ).run(df, BuyAndHoldStrategy(), stock_code="600000")

    trade = report.trades[0]
    assert trade["buy_date"] == "2024-01-02"
    assert trade["shares"] % 100 == 0
    assert trade["shares"] == 900


def test_limit_up_blocks_buy():
    df = make_df([10.0, 11.0, 11.2], closes=[10.0, 11.0, 11.2])
    report = BacktestRunner(
        initial_capital=10000,
        slippage=0,
        min_commission=0,
        enforce_price_limit=True,
    ).run(df, BuyAndHoldStrategy(), stock_code="600000")

    assert report.trade_count == 0
    assert report.final_equity == 10000


def test_limit_down_blocks_signal_sell_and_marks_to_market():
    df = make_df([10.0, 10.0, 9.0], closes=[10.0, 10.0, 9.0])
    report = BacktestRunner(
        initial_capital=10000,
        slippage=0,
        min_commission=0,
        enforce_price_limit=True,
    ).run(df, BuyThenSellStrategy(), stock_code="600000")

    trade = report.trades[0]
    assert trade["buy_date"] == "2024-01-02"
    assert trade["sell_date"] == "2024-01-03"
    assert trade["exit_reason"] == "mark_to_market"
    assert report.final_equity < 10000


def test_sell_fee_and_stamp_tax_reduce_net_pnl():
    df = make_df([10.0, 10.0, 12.0], closes=[10.0, 10.0, 12.0])
    report = BacktestRunner(
        initial_capital=10000,
        commission=0.001,
        stamp_tax=0.001,
        slippage=0,
        min_commission=0,
        enforce_price_limit=False,
    ).run(df, BuyThenSellStrategy(), stock_code="600000")

    trade = report.trades[0]
    gross_pnl = (12.0 - 10.0) * trade["shares"]
    assert trade["exit_reason"] == "signal"
    assert trade["buy_fee"] > 0
    assert trade["sell_fee"] > 0
    assert trade["stamp_tax"] > 0
    assert trade["pnl"] < gross_pnl
