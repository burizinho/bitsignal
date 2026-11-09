"""Weekly sampling (design §3, plan item 20).

A week W-SUN enters the model when its Sunday has a price and the Sunday is <= ``as_of``
(closed week). Weekly windows count valid weekly rows, not calendar weeks.
"""

from __future__ import annotations

from datetime import date
from typing import Dict

import numpy as np
import pandas as pd

from bitsignal.config import Config
from bitsignal.engine import indicators as ind
from bitsignal.models import HashRibbonState, InputState

# Score input -> the weekly columns that must all be present for the input to be usable.
INPUT_COLUMNS: Dict[str, tuple] = {
    "mvrv_z": ("mvrv_z",),
    "price_to_sma200w": ("price_to_sma200w",),
    "puell": ("puell",),
    "picycle": ("picycle_spread", "picycle_bottom"),
    "rsi14w": ("rsi14w",),
    "hash_ribbon": ("hash_ribbon",),
}

_DAILY_SAMPLED = ("mvrv_z", "puell", "sma111", "sma350", "sma471", "ema150", "picycle_spread", "picycle_bottom")


def _hash_ribbon_weekly(daily: pd.DataFrame, sundays: pd.DatetimeIndex) -> pd.Series:
    """CAPITULATION if SMA30 < SMA60 on Sunday; else BUY_RECOVERY if a cross-up happened
    Monday..Sunday of that week; else NORMAL. NaN when the SMAs do not exist on Sunday."""
    cross = daily["hash_cross_up"].fillna(False).astype(bool)
    week_cross = cross.resample("W-SUN").max().reindex(sundays).fillna(False).astype(bool)
    s30 = daily["hash_sma30"].reindex(sundays)
    s60 = daily["hash_sma60"].reindex(sundays)
    state = pd.Series(HashRibbonState.NORMAL.value, index=sundays, dtype=object)
    state[week_cross.to_numpy()] = HashRibbonState.BUY_RECOVERY.value
    state[(s30 < s60).to_numpy()] = HashRibbonState.CAPITULATION.value
    state[(s30.isna() | s60.isna()).to_numpy()] = np.nan
    return state


def to_weekly(daily_derived: pd.DataFrame, as_of: date, cfg: Config) -> pd.DataFrame:
    """Build the weekly frame from the derived daily frame (see ``derive_daily``)."""
    d = daily_derived
    sundays = d.index[(d.index.dayofweek == 6) & d["price"].notna().to_numpy()]
    sundays = sundays[sundays <= pd.Timestamp(as_of)]
    w = pd.DataFrame(index=sundays)
    w.index.name = "week"

    price = d["price"].reindex(sundays)
    w["price"] = price
    det = cfg.detector
    w["trend_sma"] = ind.sma(price, det.trend_sma_weeks)
    w["n2_sma"] = ind.sma(price, det.n2_sma_weeks)
    w["sma200w"] = ind.sma(price, 200)
    w["rsi14w"] = ind.rsi_wilder(price, 14)
    w["high52w"] = price.rolling(det.arming_weeks, min_periods=det.arming_weeks).max()
    w["ath"] = price.cummax()
    w["new_ath"] = (price > w["ath"].shift(1)).fillna(False).astype(bool)
    w["price_to_sma200w"] = ind.price_to_sma(price, w["sma200w"])
    for col in _DAILY_SAMPLED:
        w[col] = d[col].reindex(sundays)
    w["hash_ribbon"] = _hash_ribbon_weekly(d, sundays)

    for name, cols in INPUT_COLUMNS.items():
        valid = pd.Series(True, index=sundays)
        for c in cols:
            valid &= w[c].notna().to_numpy()
        state = pd.Series(InputState.MISSING.value, index=sundays, dtype=object)
        state[valid.to_numpy()] = InputState.PRESENT.value
        first = valid.idxmax() if valid.any() else None
        if first is None:
            state[:] = InputState.WARMUP.value
        else:
            state[sundays < first] = InputState.WARMUP.value
        w[f"state_{name}"] = state
    return w
