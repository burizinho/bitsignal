"""S3: Dune cross-check and display-only spot price (no network)."""

from datetime import date
from unittest import mock

import pandas as pd

from bitsignal.data import dune, spot


def _daily():
    idx = pd.date_range("2026-11-01", periods=3, freq="D", name="date")
    return pd.DataFrame({"mvrv_z": [1.0, 1.1, 1.2], "puell": [0.9, 0.95, 1.0]}, index=idx)


def test_compare_with_thresholds():
    row = {"date": date(2026, 11, 2), "mvrv_z": 1.1 + 0.31, "puell": 0.95 + 0.05}
    divs = dune.compare_with(_daily(), row)
    assert [d.metric for d in divs] == ["mvrv_z"]  # 0.31 > 0.3; 0.05 <= 0.1
    assert round(divs[0].delta, 2) == 0.31

    row_ok = {"date": date(2026, 11, 2), "mvrv_z": 1.1 + 0.29, "puell": 0.95 + 0.11}
    assert [d.metric for d in dune.compare_with(_daily(), row_ok)] == ["puell"]


def test_compare_with_date_without_daily_row():
    row = {"date": date(2026, 12, 25), "mvrv_z": 9.0, "puell": 9.0}
    assert dune.compare_with(_daily(), row) == []
    assert dune.compare_with(_daily(), None) == []


def test_fetch_dune_latest_without_key_returns_none():
    assert dune.fetch_dune_latest(None, None) is None


def test_fetch_dune_latest_parses_last_row():
    resp = mock.Mock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"result": {"rows": [
        {"date": "2026-11-01", "mvrv_z": "1.0", "puell_multiple": "0.9"},
        {"date": "2026-11-02", "mvrv_z": "1.1", "puell_multiple": "0.95"},
    ]}}
    sess = mock.Mock()
    sess.get.return_value = resp
    out = dune.fetch_dune_latest("key", "123", session=sess)
    assert out == {"date": date(2026, 11, 2), "mvrv_z": 1.1, "puell": 0.95}


def test_fetch_spot_returns_none_on_error():
    with mock.patch("yfinance.Ticker", side_effect=RuntimeError("boom")):
        assert spot.fetch_spot_usd() is None
