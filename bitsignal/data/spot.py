"""Current BTC price for display only (plan item 14). Never used by the model."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def _from_yfinance() -> Optional[Tuple[float, datetime]]:
    try:
        import yfinance as yf

        hist = yf.Ticker("BTC-USD").history(period="1d", interval="1m")
        if hist.empty:
            return None
        price = float(hist["Close"].iloc[-1])
        ts = hist.index[-1].to_pydatetime()
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return price, ts.astimezone(timezone.utc)
    except Exception as exc:
        logger.info("yfinance spot unavailable: %s", exc)
        return None


def _from_coinbase() -> Optional[Tuple[float, datetime]]:
    try:
        import requests

        resp = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=4)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            price = float(data.get("amount", 0))
            if price > 0:
                return price, datetime.now(timezone.utc)
    except Exception as exc:
        logger.info("coinbase spot unavailable: %s", exc)
    return None


def _from_binance() -> Optional[Tuple[float, datetime]]:
    try:
        import requests

        resp = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=4)
        if resp.status_code == 200:
            price = float(resp.json().get("price", 0))
            if price > 0:
                return price, datetime.now(timezone.utc)
    except Exception as exc:
        logger.info("binance spot unavailable: %s", exc)
    return None


def fetch_spot_usd() -> Optional[Tuple[float, datetime]]:
    """Last BTC-USD price from yfinance, or fallback to Coinbase/Binance, or None on error."""
    # 1. Primary: yfinance
    spot = _from_yfinance()
    if spot is not None:
        return spot

    # 2. Fallback: Coinbase API
    spot = _from_coinbase()
    if spot is not None:
        return spot

    # 3. Fallback: Binance API
    return _from_binance()
