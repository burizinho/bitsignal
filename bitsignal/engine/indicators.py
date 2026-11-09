"""Pure vectorised indicator calculations for the unified cycle model.

Every function maps Series -> Series. Every window requires ``min_periods`` equal to its length
and nothing missing is filled (no "NaN becomes 50").
"""

import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    """Simple moving average; NaN until ``n`` observations exist."""
    return s.rolling(n, min_periods=n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    """Exponential moving average (span ``n``, ``adjust=False``); NaN until ``n`` observations."""
    return s.ewm(span=n, adjust=False, min_periods=n).mean()


def rsi_wilder(s: pd.Series, n: int = 14) -> pd.Series:
    """Wilder RSI without filling.

    NaN in positions 0..n-1 (the first difference is NaN). Average loss 0 with gain > 0 gives 100;
    a constant price (0/0) gives NaN.
    """
    delta = s.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = avg_gain / avg_loss  # x/0 -> inf (RSI 100); 0/0 -> NaN
    return 100.0 - 100.0 / (1.0 + rs)


def picycle_spread(sma111: pd.Series, sma350: pd.Series) -> pd.Series:
    """Pi Cycle Top spread: SMA111 / (2 * SMA350); NaN when SMA350 is missing or not positive."""
    return sma111 / (2.0 * sma350.where(sma350 > 0))


def picycle_bottom(ema150: pd.Series, sma471: pd.Series, factor: float = 0.745) -> pd.Series:
    """Pi Cycle Bottom active when EMA150 < SMA471 * factor; <NA> when an input is missing."""
    active = (ema150 < sma471 * factor).astype("boolean")
    return active.mask(ema150.isna() | sma471.isna())


def price_to_sma(price: pd.Series, sma_series: pd.Series) -> pd.Series:
    """Price / SMA; NaN when the SMA is missing or not positive."""
    return price / sma_series.where(sma_series > 0)


def mvrv_z(mc: pd.Series, mvrv_ratio: pd.Series, min_periods: int = 730) -> pd.Series:
    """MVRV Z = (MC - RC) / expanding std of MC, with RC = MC / MVRV ratio.

    Uses only data up to each date (expanding window), so truncating the series at t does not
    change values at or before t.
    """
    rc = mc / mvrv_ratio
    return (mc - rc) / mc.expanding(min_periods=min_periods).std()


def puell(iss_usd: pd.Series) -> pd.Series:
    """Puell Multiple: daily issuance in USD / its 365-day mean (NaN for the first 364 days)."""
    return iss_usd / iss_usd.rolling(365, min_periods=365).mean()


def hash_ribbon_daily(hashrate: pd.Series) -> pd.DataFrame:
    """Daily Hash Ribbon inputs.

    ``hash_cross_up`` is True on day d when SMA30_d >= SMA60_d and SMA30_(d-1) < SMA60_(d-1).
    The weekly state is aggregated later (engine/weekly.py).
    """
    s30 = sma(hashrate, 30)
    s60 = sma(hashrate, 60)
    cross_up = (s30 >= s60) & (s30.shift(1) < s60.shift(1))
    return pd.DataFrame({"hash_sma30": s30, "hash_sma60": s60, "hash_cross_up": cross_up})
