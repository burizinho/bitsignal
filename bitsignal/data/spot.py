"""Current BTC price for display only (plan item 14). Never used by the model."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def fetch_spot_usd() -> Optional[Tuple[float, datetime]]:
    """Last BTC-USD price from yfinance, or ``None`` on any error."""
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
    except Exception as exc:  # display-only: never propagate
        logger.info("spot price unavailable: %s", exc)
        return None
