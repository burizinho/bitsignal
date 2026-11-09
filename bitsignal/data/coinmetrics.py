"""CoinMetrics Community API client (plan item 12).

The only source of model inputs (design §2, Q7). No API key; CC BY-NC 4.0.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

URL = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"
CATALOG_URL = "https://community-api.coinmetrics.io/v4/catalog-v2/asset-metrics"
METRICS: Dict[str, str] = {
    "PriceUSD": "price",
    "CapMrktCurUSD": "mc",
    "CapMVRVCur": "mvrv_ratio",
    "IssTotUSD": "iss_usd",
    "HashRate": "hashrate",
}
COLUMNS = list(METRICS.values())
PAGE_SIZE = 10000
START = "2010-07-18"
TIMEOUT = 60
RETRY_WAITS = (1, 2, 4)  # up to 3 retries (4 calls in total) on 5xx / 429
PAGE_PAUSE = 0.6  # >= 0.6 s between pages keeps us under 10 requests / 6 s

_sleep = time.sleep  # patched in tests


class DataUnavailable(Exception):
    """CoinMetrics did not return the series the model needs."""


def _get_json(session: requests.Session, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    last_exc: Optional[Exception] = None
    for attempt in range(len(RETRY_WAITS) + 1):
        try:
            resp = session.get(url, params=params, timeout=TIMEOUT)
        except requests.RequestException as exc:
            last_exc = exc
        else:
            if resp.status_code == 429 or resp.status_code >= 500:
                last_exc = DataUnavailable(f"HTTP {resp.status_code} from {url}")
            else:
                resp.raise_for_status()
                return resp.json()
        if attempt < len(RETRY_WAITS):
            _sleep(RETRY_WAITS[attempt])
    raise DataUnavailable(f"CoinMetrics request failed after retries: {last_exc}")


def fetch_coinmetrics(session: Optional[requests.Session] = None) -> pd.DataFrame:
    """Fetch the 5 daily series since 2010-07-18.

    Returns a DataFrame indexed by ``date`` (the row ``time = D 00:00Z`` becomes date D, the
    close of day D) with float64 columns ``price, mc, mvrv_ratio, iss_usd, hashrate``.
    """
    sess = session or requests.Session()
    params: Optional[Dict[str, Any]] = {
        "assets": "btc",
        "metrics": ",".join(METRICS),
        "frequency": "1d",
        "start_time": START,
        "page_size": PAGE_SIZE,
    }
    url: Optional[str] = URL
    rows = []
    first = True
    while url:
        if not first:
            _sleep(PAGE_PAUSE)
        payload = _get_json(sess, url, params)
        rows.extend(payload.get("data", []))
        url = payload.get("next_page_url")
        params = None  # next_page_url already carries the query
        first = False

    if not rows:
        raise DataUnavailable("CoinMetrics returned no rows")
    df = pd.DataFrame(rows)
    missing = [m for m in METRICS if m not in df.columns]
    if missing:
        raise DataUnavailable(f"CoinMetrics response is missing metrics: {missing}")

    df["date"] = pd.to_datetime(df["time"], utc=True).dt.tz_localize(None).dt.normalize()
    out = df.set_index("date")[list(METRICS)].rename(columns=METRICS)
    out = out.apply(pd.to_numeric, errors="coerce").astype("float64")
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out.index.name = "date"
    return out


def check_catalog(session: Optional[requests.Session] = None) -> Dict[str, bool]:
    """Return, for each of the 5 metrics, whether it is available daily in the Community plan.

    Reads ``data[0].metrics[*]``; a metric counts as available when it has an entry in
    ``frequencies`` with ``frequency == "1d"`` and ``community == true``. Missing -> False.
    """
    sess = session or requests.Session()
    payload = _get_json(sess, CATALOG_URL, {"assets": "btc", "metrics": ",".join(METRICS)})
    found: Dict[str, bool] = {m: False for m in METRICS}
    data = payload.get("data") or []
    if data:
        for item in data[0].get("metrics", []):
            name = item.get("metric")
            if name in found:
                found[name] = any(
                    f.get("frequency") == "1d" and f.get("community") is True
                    for f in item.get("frequencies", [])
                )
    return found
