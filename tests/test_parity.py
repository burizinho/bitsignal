"""S4: dashboard path (CoinMetrics fetch) and backtest path (frozen CSV) give identical weeks."""

from unittest import mock

import pandas as pd

from bitsignal.config import load_config
from bitsignal.data import coinmetrics as cm
from bitsignal.data.history import from_frame, load_frozen_history
from bitsignal.engine.pipeline import run_model

CFG = load_config()


class _Resp:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def _session_from_csv(daily: pd.DataFrame, page_size: int = 2500):
    """Fake CoinMetrics session serving the frozen CSV as API rows (as strings, like the API)."""
    inverse = {v: k for k, v in cm.METRICS.items()}
    rows = []
    for d, rec in daily.dropna(how="all").iterrows():
        row = {"asset": "btc", "time": f"{d.date().isoformat()}T00:00:00.000000000Z"}
        for col, val in rec.items():
            if pd.notna(val):
                row[inverse[col]] = repr(float(val))
        rows.append(row)
    pages = [rows[i : i + page_size] for i in range(0, len(rows), page_size)]
    responses = []
    for n, page in enumerate(pages):
        payload = {"data": page}
        if n + 1 < len(pages):
            payload["next_page_url"] = f"https://next/{n + 1}"
        responses.append(_Resp(payload))
    sess = mock.Mock()
    sess.get.side_effect = responses
    return sess


def test_dashboard_and_backtest_paths_match():
    frozen = load_frozen_history(CFG.data.csv_path)
    with mock.patch.object(cm, "_sleep"):
        live_df = cm.fetch_coinmetrics(_session_from_csv(frozen.daily))
    live = from_frame(live_df, source="coinmetrics_live")

    a = run_model(live, CFG)
    b = run_model(frozen, CFG)
    pd.testing.assert_frame_equal(a.weeks, b.weeks, check_freq=False)
    assert a.events == b.events
    assert a.model_hash == b.model_hash
