"""Unit tests for mathematical indicator calculations."""

import numpy as np
import pandas as pd
from bitsignal.engine.indicators import (
    ema,
    hash_ribbon_daily,
    mvrv_z,
    picycle_bottom,
    picycle_spread,
    price_to_sma,
    puell,
    rsi_wilder,
    sma,
)


def test_sma_and_ema_require_full_window():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    assert sma(s, 3).isna().tolist() == [True, True, False, False, False]
    assert sma(s, 3).iloc[-1] == 4.0
    e = ema(s, 3)
    assert e.isna().tolist() == [True, True, False, False, False]
    assert e.iloc[-1] == s.ewm(span=3, adjust=False).mean().iloc[-1]


def test_rsi_wilder_no_fill():
    rising = pd.Series(np.arange(1.0, 40.0) + np.sin(np.arange(39)))
    rsi = rsi_wilder(rising, 14)
    assert rsi.iloc[:14].isna().all()  # positions 0..13
    assert rsi.first_valid_index() == rising.index[14]
    assert not (rsi.dropna() == 50.0).any()

    strictly_up = pd.Series(np.arange(1.0, 40.0))
    assert rsi_wilder(strictly_up, 14).iloc[-1] == 100.0

    constant = pd.Series([5.0] * 30)
    assert rsi_wilder(constant, 14).isna().all()  # 0/0 -> NaN, never 50


def test_picycle_vector_functions():
    ema150 = pd.Series([100.0, 100.0, 74.5, np.nan])
    sma471 = pd.Series([200.0, 80.0, 100.0, 100.0])
    bottom = picycle_bottom(ema150, sma471, 0.745)
    assert bottom.iloc[0] == True  # noqa: E712
    assert bottom.iloc[1] == False  # noqa: E712
    assert bottom.iloc[2] == False  # noqa: E712  (equal -> inactive)
    assert pd.isna(bottom.iloc[3])

    spread = picycle_spread(pd.Series([100.0, 100.0]), pd.Series([50.0, 0.0]))
    assert spread.iloc[0] == 1.0
    assert np.isnan(spread.iloc[1])

    ratio = price_to_sma(pd.Series([70000.0, 1.0]), pd.Series([35000.0, -1.0]))
    assert ratio.iloc[0] == 2.0
    assert np.isnan(ratio.iloc[1])


def test_mvrv_z_has_no_lookahead():
    rng = np.random.default_rng(20261108)
    n = 900
    mc = pd.Series(np.cumsum(rng.normal(1.0, 5.0, n)) + 1000.0)
    ratio = pd.Series(1.0 + rng.uniform(0.1, 2.0, n))
    full = mvrv_z(mc, ratio)
    assert full.iloc[:729].isna().all()
    assert full.iloc[729:].notna().all()
    t = 800
    truncated = mvrv_z(mc.iloc[:t], ratio.iloc[:t])
    pd.testing.assert_series_equal(truncated, full.iloc[:t])


def test_puell_needs_365_days():
    iss = pd.Series(np.full(400, 10.0))
    p = puell(iss)
    assert p.iloc[:364].isna().all()
    assert p.iloc[364] == 1.0


def test_hash_ribbon_daily_cross_up():
    # SMA30 starts below SMA60 (hashrate falling), then hashrate jumps so SMA30 crosses up.
    hashrate = pd.Series([100.0] * 60 + [50.0] * 40 + [300.0] * 40)
    hr = hash_ribbon_daily(hashrate)
    assert list(hr.columns) == ["hash_sma30", "hash_sma60", "hash_cross_up"]
    crosses = hr.index[hr["hash_cross_up"]].tolist()
    assert len(crosses) == 1
    d = crosses[0]
    assert hr.loc[d, "hash_sma30"] >= hr.loc[d, "hash_sma60"]
    assert hr.loc[d - 1, "hash_sma30"] < hr.loc[d - 1, "hash_sma60"]


def test_hash_ribbon_cross_counts_equality():
    # 60 days at 10, 30 days at 4 (SMA30 < SMA60), then 10 days at 16: on the last day
    # SMA30 == SMA60 exactly (10 == 10) after being below, which counts as a cross (>=).
    hashrate = pd.Series([10.0] * 60 + [4.0] * 30 + [16.0] * 10)
    hr = hash_ribbon_daily(hashrate)
    last = hr.index[-1]
    assert hr.loc[last, "hash_sma30"] == hr.loc[last, "hash_sma60"]
    assert hr.loc[last - 1, "hash_sma30"] < hr.loc[last - 1, "hash_sma60"]
    assert bool(hr.loc[last, "hash_cross_up"]) is True
