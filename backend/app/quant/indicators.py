"""Technical indicator calculator.

All computations are vectorized (numpy/pandas) and work on a DataFrame
with OHLCV columns: open, close, high, low, volume.

New indicators should follow the same signature:
    compute_xxx(df: pd.DataFrame, **params) -> pd.Series | pd.DataFrame
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ═══════════════════════════════════════════════════════════════════════════
# Trend Indicators (趋势类)
# ═══════════════════════════════════════════════════════════════════════════


def compute_ma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Simple Moving Average."""
    return df["close"].rolling(period).mean()


def compute_ema(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Exponential Moving Average."""
    return df["close"].ewm(span=period, adjust=False).mean()


def compute_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """MACD — Moving Average Convergence Divergence.

    Returns DataFrame with columns: dif, dea, macd_hist
    """
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = (dif - dea) * 2  # ×2 for visibility (Chinese convention)
    return pd.DataFrame({"dif": dif, "dea": dea, "macd_hist": hist}, index=df.index)


# ═══════════════════════════════════════════════════════════════════════════
# Momentum Indicators (动量类)
# ═══════════════════════════════════════════════════════════════════════════


def compute_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Relative Strength Index (0–100)."""
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def compute_kdj(
    df: pd.DataFrame, n: int = 9, k_period: int = 3, d_period: int = 3
) -> pd.DataFrame:
    """KDJ Stochastic indicator.

    Returns DataFrame with columns: k, d, j
    """
    low_n = df["low"].rolling(n).min()
    high_n = df["high"].rolling(n).max()
    rsv = ((df["close"] - low_n) / (high_n - low_n).replace(0, np.nan)) * 100

    k = rsv.ewm(alpha=1 / k_period, adjust=False).mean()
    d = k.ewm(alpha=1 / d_period, adjust=False).mean()
    j = 3 * k - 2 * d
    return pd.DataFrame({"k": k, "d": d, "j": j}, index=df.index)


# ═══════════════════════════════════════════════════════════════════════════
# Volatility Indicators (波动类)
# ═══════════════════════════════════════════════════════════════════════════


def compute_boll(
    df: pd.DataFrame, period: int = 20, std_mult: float = 2.0
) -> pd.DataFrame:
    """Bollinger Bands.

    Returns DataFrame with columns: mid, upper, lower, width
    """
    mid = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std()
    upper = mid + std_mult * std
    lower = mid - std_mult * std
    width = (upper - lower) / mid.replace(0, np.nan) * 100
    return pd.DataFrame(
        {"mid": mid, "upper": upper, "lower": lower, "width": width}, index=df.index
    )


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


# ═══════════════════════════════════════════════════════════════════════════
# Volume Indicators (量价类)
# ═══════════════════════════════════════════════════════════════════════════


def compute_obv(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume."""
    sign = np.where(df["close"] > df["close"].shift(1), 1,
                    np.where(df["close"] < df["close"].shift(1), -1, 0))
    return (sign * df["volume"]).cumsum()


def compute_volume_ma(df: pd.DataFrame, period: int = 5) -> pd.Series:
    """Volume Moving Average."""
    return df["volume"].rolling(period).mean()


# ═══════════════════════════════════════════════════════════════════════════
# Cross / Signal Detection
# ═══════════════════════════════════════════════════════════════════════════


def detect_golden_cross(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """Golden cross: fast crosses ABOVE slow. Returns boolean Series."""
    prev_fast, prev_slow = fast.shift(1), slow.shift(1)
    return (prev_fast <= prev_slow) & (fast > slow)


def detect_death_cross(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """Death cross: fast crosses BELOW slow. Returns boolean Series."""
    prev_fast, prev_slow = fast.shift(1), slow.shift(1)
    return (prev_fast >= prev_slow) & (fast < slow)


# ═══════════════════════════════════════════════════════════════════════════
# Trend Strength (趋势强度)
# ═══════════════════════════════════════════════════════════════════════════


def compute_slope(df: pd.DataFrame, period: int = 20, field: str = "close") -> pd.Series:
    """Linear regression slope over `period` bars.

    Positive = uptrend, negative = downtrend, ~0 = sideways.
    Uses numpy.polyfit for least-squares fit.
    """
    values = df[field].values
    x = np.arange(period)
    result = np.full(len(values), np.nan)

    for i in range(period - 1, len(values)):
        y = values[i - period + 1 : i + 1]
        slope_val, _ = np.polyfit(x, y, 1)
        result[i] = slope_val

    return pd.Series(result, index=df.index)


def compute_slope_pct(df: pd.DataFrame, period: int = 20, field: str = "close") -> pd.Series:
    """Slope as percentage of average price over the period (normalized).

    Uses absolute average price for normalization so negative closes
    (from 前复权 adjustments) don't flip the trend sign.
    """
    slope_raw = compute_slope(df, period, field)
    avg_price = df[field].rolling(period).mean().abs()
    result = np.where(avg_price > 0.01, (slope_raw / avg_price) * 100, slope_raw)
    return pd.Series(result, index=df.index)


# ═══════════════════════════════════════════════════════════════════════════
# Indicator Registry — maps name → compute function
# ═══════════════════════════════════════════════════════════════════════════

INDICATOR_REGISTRY: dict[str, tuple[callable, dict]] = {
    "ma": (compute_ma, {"period": 20}),
    "ema": (compute_ema, {"period": 20}),
    "macd": (compute_macd, {"fast": 12, "slow": 26, "signal": 9}),
    "rsi": (compute_rsi, {"period": 14}),
    "kdj": (compute_kdj, {"n": 9, "k_period": 3, "d_period": 3}),
    "boll": (compute_boll, {"period": 20, "std_mult": 2.0}),
    "atr": (compute_atr, {"period": 14}),
    "obv": (compute_obv, {}),
    "volume_ma": (compute_volume_ma, {"period": 5}),
    "slope": (compute_slope, {"period": 20}),
    "slope_pct": (compute_slope_pct, {"period": 20}),
}
