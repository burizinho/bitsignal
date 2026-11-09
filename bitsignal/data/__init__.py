"""Data layer: CoinMetrics history (model inputs), spot price (display) and Dune (cross-check)."""

from bitsignal.data.coinmetrics import DataUnavailable, check_catalog, fetch_coinmetrics
from bitsignal.data.history import MarketHistory, from_frame, load_frozen_history

__all__ = [
    "DataUnavailable",
    "MarketHistory",
    "check_catalog",
    "fetch_coinmetrics",
    "from_frame",
    "load_frozen_history",
]
