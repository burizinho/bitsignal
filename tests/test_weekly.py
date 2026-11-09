"""S4: weekly sampling (design §3)."""

import numpy as np
import pandas as pd

from bitsignal.config import load_config
from bitsignal.engine.weekly import to_weekly
from bitsignal.models import InputState

CFG = load_config()
DAILY_COLS = ["mvrv_z", "puell", "sma111", "sma350", "sma471", "ema150", "picycle_spread", "picycle_bottom",
              "hash_sma30", "hash_sma60", "hash_cross_up"]


def daily(n=70, start="2020-01-01"):
    idx = pd.date_range(start, periods=n, freq="D", name="date")
    d = pd.DataFrame(index=idx)
    d["price"] = np.linspace(100, 200, n)
    for c in DAILY_COLS:
        d[c] = 1.0
    d["picycle_bottom"] = pd.array([False] * n, dtype="boolean")
    d["hash_sma30"] = 2.0
    d["hash_sma60"] = 1.0
    d["hash_cross_up"] = False
    return d


def test_only_sundays_with_price_and_closed():
    d = daily()
    sundays = d.index[d.index.day_of_week == 6]
    d.loc[sundays[2], "price"] = np.nan  # Sunday without price -> dropped
    as_of = sundays[-1] - pd.Timedelta(days=1)  # last week still open -> dropped
    w = to_weekly(d, as_of.date(), CFG)
    assert all(ix.day_of_week == 6 for ix in w.index)
    assert sundays[2] not in w.index
    assert sundays[-1] not in w.index
    assert w.index[-1] == sundays[-2]


def test_missing_series_keeps_the_week_and_marks_missing_vs_warmup():
    d = daily()
    sundays = d.index[d.index.day_of_week == 6]
    d.loc[: sundays[1], "puell"] = np.nan  # before first valid -> WARMUP
    d.loc[sundays[4], "puell"] = np.nan  # after -> MISSING, week kept
    w = to_weekly(d, d.index[-1].date(), CFG)
    assert sundays[4] in w.index
    assert w.loc[sundays[0], "state_puell"] == InputState.WARMUP.value
    assert w.loc[sundays[1], "state_puell"] == InputState.WARMUP.value
    assert w.loc[sundays[2], "state_puell"] == InputState.PRESENT.value
    assert w.loc[sundays[4], "state_puell"] == InputState.MISSING.value
    # price-derived inputs still warming up (SMA200w needs 200 weeks)
    assert (w["state_price_to_sma200w"] == InputState.WARMUP.value).all()


def test_first_week_is_not_ath_and_new_highs_are():
    d = daily()
    w = to_weekly(d, d.index[-1].date(), CFG)
    assert bool(w["new_ath"].iloc[0]) is False
    assert w["new_ath"].iloc[1:].all()  # rising price -> every later week is a new high


def _hash_case(cross_day_offset, s30_sunday, s60_sunday):
    d = daily(n=21, start="2020-01-06")  # Monday 2020-01-06 .. Sunday 2020-01-26
    sundays = d.index[d.index.day_of_week == 6]
    week_mon = sundays[1] - pd.Timedelta(days=6)
    d.loc[week_mon + pd.Timedelta(days=cross_day_offset), "hash_cross_up"] = True
    d.loc[sundays[1], "hash_sma30"] = s30_sunday
    d.loc[sundays[1], "hash_sma60"] = s60_sunday
    w = to_weekly(d, d.index[-1].date(), CFG)
    return w.loc[sundays[1], "hash_ribbon"], w.loc[sundays[0], "hash_ribbon"]


def test_hash_ribbon_cross_on_wednesday_is_buy_recovery():
    this_week, other = _hash_case(2, 2.0, 1.0)  # Wednesday cross, SMA30 >= SMA60 on Sunday
    assert this_week == "BUY_RECOVERY"
    assert other == "NORMAL"


def test_hash_ribbon_capitulation_on_sunday_wins():
    this_week, _ = _hash_case(2, 1.0, 2.0)  # crossed Wednesday but SMA30 < SMA60 on Sunday
    assert this_week == "CAPITULATION"


def test_trend_columns_follow_config():
    from bitsignal.config import apply_overrides

    d = daily(n=200)
    cfg = apply_overrides(CFG, {"detector": {"trend_sma_weeks": 3, "n2_sma_weeks": 5, "arming_weeks": 4}})
    w = to_weekly(d, d.index[-1].date(), cfg)
    assert w["trend_sma"].iloc[:2].isna().all() and pd.notna(w["trend_sma"].iloc[2])
    assert w["n2_sma"].iloc[:4].isna().all() and pd.notna(w["n2_sma"].iloc[4])
    assert w["high52w"].iloc[:3].isna().all() and pd.notna(w["high52w"].iloc[3])
