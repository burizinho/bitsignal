"""S3: CoinMetrics client, without network (requests mocked)."""

from unittest import mock

import pandas as pd
import pytest

from bitsignal.data import coinmetrics as cm


class FakeResp:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        return self.responses.pop(0)


def _row(day, price=100.0):
    return {
        "asset": "btc",
        "time": f"{day}T00:00:00.000000000Z",
        "PriceUSD": str(price),
        "CapMrktCurUSD": "1000",
        "CapMVRVCur": "1.5",
        "IssTotUSD": "10",
        "HashRate": "5",
    }


@pytest.fixture(autouse=True)
def no_sleep():
    with mock.patch.object(cm, "_sleep") as fake:
        yield fake


def test_pagination_and_mapping():
    sess = FakeSession(
        [
            FakeResp(payload={"data": [_row("2010-07-18"), _row("2010-07-19")], "next_page_url": "https://next"}),
            FakeResp(payload={"data": [_row("2010-07-20", 120.5)]}),
        ]
    )
    df = cm.fetch_coinmetrics(sess)
    assert list(df.columns) == ["price", "mc", "mvrv_ratio", "iss_usd", "hashrate"]
    assert df.index.name == "date"
    assert df.index[0] == pd.Timestamp("2010-07-18")
    assert df.loc["2010-07-20", "price"] == 120.5
    assert all(dt == "float64" for dt in df.dtypes)
    # first call carries the query; the next page uses next_page_url as given
    assert sess.calls[0][0] == cm.URL and sess.calls[0][1]["metrics"].count(",") == 4
    assert sess.calls[0][1]["frequency"] == "1d" and sess.calls[0][1]["start_time"] == "2010-07-18"
    assert sess.calls[1] == ("https://next", None)


def test_missing_metric_raises():
    row = _row("2010-07-18")
    del row["HashRate"]
    sess = FakeSession([FakeResp(payload={"data": [row]})])
    with pytest.raises(cm.DataUnavailable):
        cm.fetch_coinmetrics(sess)


def test_empty_response_raises():
    with pytest.raises(cm.DataUnavailable):
        cm.fetch_coinmetrics(FakeSession([FakeResp(payload={"data": []})]))


def test_retry_on_429_then_success(no_sleep):
    sess = FakeSession([FakeResp(429), FakeResp(503), FakeResp(payload={"data": [_row("2010-07-18")]})])
    df = cm.fetch_coinmetrics(sess)
    assert len(df) == 1
    assert [c.args[0] for c in no_sleep.call_args_list] == [1, 2]


def test_gives_up_after_three_retries(no_sleep):
    sess = FakeSession([FakeResp(429)] * 4)
    with pytest.raises(cm.DataUnavailable):
        cm.fetch_coinmetrics(sess)
    assert len(sess.calls) == 4


def test_check_catalog():
    payload = {
        "data": [
            {
                "asset": "btc",
                "metrics": [
                    {"metric": "PriceUSD", "frequencies": [{"frequency": "1d", "community": True}]},
                    {"metric": "CapMrktCurUSD", "frequencies": [{"frequency": "1d", "community": True}]},
                    {"metric": "CapMVRVCur", "frequencies": [{"frequency": "1d", "community": False}]},
                    {"metric": "IssTotUSD", "frequencies": [{"frequency": "1h", "community": True}]},
                ],
            }
        ]
    }
    found = cm.check_catalog(FakeSession([FakeResp(payload=payload)]))
    assert found == {
        "PriceUSD": True,
        "CapMrktCurUSD": True,
        "CapMVRVCur": False,  # not community
        "IssTotUSD": False,  # no daily frequency
        "HashRate": False,  # missing from the response
    }
