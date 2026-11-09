"""Dune: cross-check only (plan item 15, Q7). Never imported by engine/ or backtest/.

Adapted from the Dune read of the former ``bitsignal/ingestion.py`` (removed in S8).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

TIMEOUT = 10
THRESHOLDS = {"mvrv_z": 0.3, "puell": 0.1}


@dataclass(frozen=True)
class Divergence:
    metric: str
    date: date
    coinmetrics: float
    dune: float
    delta: float


def fetch_dune_latest(api_key: Optional[str], query_id: Optional[str], session: Optional[requests.Session] = None) -> Optional[dict]:
    """Latest row of the user's Dune query as ``{date, mvrv_z, puell}``, or ``None``."""
    if not api_key or not query_id:
        return None
    sess = session or requests.Session()
    try:
        url = f"https://api.dune.com/api/v1/query/{query_id}/results"
        resp = sess.get(url, headers={"X-Dune-Api-Key": api_key}, timeout=TIMEOUT)
        resp.raise_for_status()
        rows = resp.json().get("result", {}).get("rows", [])
        if not rows:
            return None
        latest = rows[-1]
        return {
            "date": pd.Timestamp(latest["date"]).date(),
            "mvrv_z": float(latest["mvrv_z"]),
            "puell": float(latest["puell_multiple"]),
        }
    except Exception as exc:
        logger.info("Dune cross-check unavailable: %s", exc)
        return None


def compare_with(daily_derived: pd.DataFrame, dune_row: Optional[dict]) -> List[Divergence]:
    """Compare Dune with the CoinMetrics daily row of the same date (if it exists)."""
    if not dune_row:
        return []
    ts = pd.Timestamp(dune_row["date"])
    if ts not in daily_derived.index:
        return []
    row = daily_derived.loc[ts]
    out: List[Divergence] = []
    for metric, limit in THRESHOLDS.items():
        cm = row.get(metric)
        if cm is None or pd.isna(cm):
            continue
        delta = float(dune_row[metric]) - float(cm)
        if abs(delta) > limit:
            out.append(Divergence(metric, ts.date(), float(cm), float(dune_row[metric]), delta))
    return out
