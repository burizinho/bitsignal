"""Pure functional technical and on-chain indicator calculations."""

import numpy as np
import pandas as pd


def calculate_sma(series: pd.Series, window: int) -> pd.Series:
    """Calculate Simple Moving Average."""
    return series.rolling(window=window).mean()


def calculate_ema(series: pd.Series, span: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return series.ewm(span=span, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's smoothing (equivalent to alpha=1/period EMA)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()

    # Where avg_loss is 0 and avg_gain > 0, RSI is 100.0.
    # Where avg_gain is 0 and avg_loss > 0, RSI is 0.0.
    rs = np.where(avg_loss == 0, np.where(avg_gain > 0, np.inf, 1.0), avg_gain / avg_loss)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return pd.Series(rsi, index=series.index).fillna(50.0)


def calculate_picycle_top_ratio(sma_111: float, sma_350: float) -> float:
    """Calculate Pi Cycle Top Proximity Spread Ratio: SMA_111 / (2 * SMA_350)."""
    if sma_350 <= 0:
        return 0.0
    return float(sma_111 / (2.0 * sma_350))


def is_picycle_bottom_triggered(ema_150: float, sma_471: float) -> bool:
    """Evaluate Pi Cycle Bottom convergence: EMA_150 * 0.745 <= SMA_471."""
    if ema_150 <= 0 or sma_471 <= 0:
        return False
    return float(ema_150 * 0.745) <= float(sma_471)


def calculate_200w_sma_ratio(price: float, sma_200w: float) -> float:
    """Calculate Price to 200-week SMA Extension Ratio."""
    if sma_200w <= 0:
        return 1.0
    return float(price / sma_200w)
