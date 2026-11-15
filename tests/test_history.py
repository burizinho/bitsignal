"""S3: MarketHistory, frozen CSV, revision check and daily derivations (no network)."""

import numpy as np
import pandas as pd
import pytest

from bitsignal.config import load_config
from bitsignal.data.history import (
    compare_histories,
    derive_daily,
    from_frame,
    load_frozen_history,
    load_live_or_incremental_history,
    write_frozen_history,
)


def _frame(days=800, start="2010-07-18", drop=()):
    idx = pd.date_range(start, periods=days, freq="D", name="date")
    rng = np.random.default_rng(1)
    df = pd.DataFrame(
        {
            "price": np.linspace(10, 1000, days),
            "mc": np.linspace(100, 10000, days),
            "mvrv_ratio": 1.0 + rng.uniform(0.1, 2.0, days),
            "iss_usd": np.full(days, 50.0),
            "hashrate": np.linspace(1, 100, days),
        },
        index=idx,
    )
    return df.drop(index=[pd.Timestamp(d) for d in drop])


def test_from_frame_reindexes_calendar_without_filling():
    df = _frame(days=10, drop=("2010-07-20",))
    h = from_frame(df, source="coinmetrics_live")
    assert len(h.daily) == 10
    assert h.daily.loc["2010-07-20"].isna().all()  # gap kept as NaN, not filled
    assert h.as_of.isoformat() == "2010-07-27"


def test_truncate_cuts_and_recomputes_as_of():
    h = from_frame(_frame(days=30), source="coinmetrics_live")
    t = h.truncate(pd.Timestamp("2010-07-25"))
    assert t.daily.index[-1] == pd.Timestamp("2010-07-25")
    assert t.as_of.isoformat() == "2010-07-25"
    assert len(h.daily) == 30  # original untouched


def test_frozen_csv_roundtrip_and_meta(tmp_path):
    df = _frame(days=40, drop=("2010-07-25",))
    out = tmp_path / "hist.csv"
    meta = write_frozen_history(df, out)
    assert meta["rows"] == 40
    assert meta["gaps"]["price"] == ["2010-07-25"]
    assert meta["license"] == "CC BY-NC 4.0"
    h = load_frozen_history(out)
    assert h.source == "coinmetrics_frozen"
    assert h.csv_sha256 == meta["sha256"]
    pd.testing.assert_frame_equal(h.daily, from_frame(df, source="coinmetrics_live").daily, check_freq=False)


def test_frozen_csv_hash_mismatch_is_rejected(tmp_path):
    out = tmp_path / "hist.csv"
    write_frozen_history(_frame(days=10), out)
    out.write_bytes(out.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        load_frozen_history(out)


def test_compare_histories_detects_revision():
    df = _frame(days=20)
    frozen = from_frame(df, source="coinmetrics_frozen")
    revised = df.copy()
    revised.loc["2010-07-22", "mc"] *= 1.01
    live = from_frame(revised, source="coinmetrics_live")
    diffs = compare_histories(live, frozen)
    assert len(diffs) == 1
    assert diffs.iloc[0]["column"] == "mc"
    assert compare_histories(frozen, frozen).empty


def test_derive_daily_columns_and_warmup():
    cfg = load_config()
    h = from_frame(_frame(days=800), source="coinmetrics_live")
    d = derive_daily(h, cfg)
    for col in [
        "mvrv_z", "puell", "hash_sma30", "hash_sma60", "hash_cross_up",
        "sma111", "sma350", "sma471", "ema150", "picycle_spread", "picycle_bottom",
    ]:
        assert col in d.columns
    assert d["sma471"].iloc[:470].isna().all() and d["sma471"].iloc[470:].notna().all()
    assert d["puell"].iloc[:364].isna().all()
    assert d["mvrv_z"].iloc[:729].isna().all()
    assert d["picycle_bottom"].iloc[:470].isna().all()  # <NA> until SMA471 exists
    assert not (d[["mvrv_z", "puell", "sma111"]] == 50.0).any().any()


def test_load_live_or_incremental_history_with_frozen_fallback(tmp_path):
    from unittest import mock
    from bitsignal.data.coinmetrics import DataUnavailable

    csv_file = tmp_path / "base.csv"
    df = _frame(days=10)
    write_frozen_history(df, csv_file)

    # When network fails, it falls back to frozen history without raising
    with mock.patch("bitsignal.data.history.fetch_coinmetrics", side_effect=DataUnavailable("offline")):
        h = load_live_or_incremental_history(csv_file)
        assert h.source == "coinmetrics_frozen"
        assert h.as_of == df.index[-1].date()


def test_load_live_or_incremental_history_merges_new_rows(tmp_path):
    from unittest import mock

    csv_file = tmp_path / "base.csv"
    df_base = _frame(days=10)
    write_frozen_history(df_base, csv_file)

    # Mock new row for the next day
    next_day = df_base.index[-1] + pd.Timedelta(days=1)
    df_new = pd.DataFrame(
        {
            "price": [9999.0],
            "mc": [100000.0],
            "mvrv_ratio": [2.5],
            "iss_usd": [50.0],
            "hashrate": [120.0],
        },
        index=pd.DatetimeIndex([next_day], name="date"),
    )

    with mock.patch("bitsignal.data.history.fetch_coinmetrics", return_value=df_new) as fake_fetch:
        h = load_live_or_incremental_history(csv_file)
        assert fake_fetch.called
        assert fake_fetch.call_args.kwargs.get("start_time") == df_base.index[-1].date().isoformat()
        assert h.source == "coinmetrics_live"
        assert h.as_of == next_day.date()
        assert h.daily.loc[next_day, "price"] == 9999.0
