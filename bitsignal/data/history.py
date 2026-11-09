"""Market history model, frozen CSV and shared daily derivations (plan item 13)."""

from __future__ import annotations

import hashlib
import io
import json
import logging
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union

import pandas as pd

from bitsignal.config import Config, repo_path
from bitsignal.data.coinmetrics import COLUMNS, METRICS, START, URL
from bitsignal.engine import indicators as ind

logger = logging.getLogger(__name__)

LICENSE = "CC BY-NC 4.0"


@dataclass(frozen=True)
class MarketHistory:
    """Daily CoinMetrics series on a full calendar (no forward fill)."""

    daily: pd.DataFrame
    source: Literal["coinmetrics_live", "coinmetrics_frozen"]
    as_of: date
    fetched_at: datetime
    csv_sha256: Optional[str] = None

    def truncate(self, t: Union[date, pd.Timestamp]) -> "MarketHistory":
        """Rows up to and including ``t``; ``as_of`` recalculated."""
        cut = self.daily.loc[: pd.Timestamp(t)]
        return replace(self, daily=cut, as_of=_as_of(cut))


def _as_of(daily: pd.DataFrame) -> date:
    valid = daily["price"].dropna()
    if valid.empty:
        raise ValueError("history has no price")
    return valid.index[-1].date()


def _calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Reindex on the full daily calendar from START to the last price, without filling."""
    df = df.sort_index()
    last = df["price"].dropna().index[-1]
    idx = pd.date_range(pd.Timestamp(START), last, freq="D", name="date")
    return df.reindex(idx)[COLUMNS].astype("float64")


def from_frame(
    df: pd.DataFrame,
    source: Literal["coinmetrics_live", "coinmetrics_frozen"],
    fetched_at: Optional[datetime] = None,
    csv_sha256: Optional[str] = None,
) -> MarketHistory:
    daily = _calendar(df)
    return MarketHistory(
        daily=daily,
        source=source,
        as_of=_as_of(daily),
        fetched_at=fetched_at or datetime.now(timezone.utc),
        csv_sha256=csv_sha256,
    )


def _gaps(daily: pd.DataFrame) -> Dict[str, List[str]]:
    """Dates with NaN between the first and last valid value of each column."""
    gaps: Dict[str, List[str]] = {}
    for col in daily.columns:
        s = daily[col]
        first, last = s.first_valid_index(), s.last_valid_index()
        if first is None:
            continue
        inner = s.loc[first:last]
        missing = inner.index[inner.isna()]
        if len(missing):
            gaps[col] = [d.strftime("%Y-%m-%d") for d in missing]
    return gaps


def _csv_bytes(daily: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    daily.to_csv(buf, index_label="date", date_format="%Y-%m-%d", lineterminator="\n")
    return buf.getvalue().encode("utf-8")


def write_frozen_history(df: pd.DataFrame, csv_path: Union[str, Path], fetched_at: Optional[datetime] = None) -> dict:
    """Write the CSV and its ``.meta.json``; return the meta. Logs internal gaps."""
    daily = _calendar(df)
    data = _csv_bytes(daily)
    path = repo_path(csv_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    gaps = _gaps(daily)
    for col, dates in gaps.items():
        logger.warning("CoinMetrics gap in %s: %d day(s), first %s", col, len(dates), dates[0])
    meta = {
        "source_url": URL,
        "metrics": METRICS,
        "fetched_at": (fetched_at or datetime.now(timezone.utc)).isoformat(),
        "rows": int(len(daily)),
        "last_date": _as_of(daily).isoformat(),
        "gaps": gaps,
        "license": LICENSE,
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    _meta_path(path).write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return meta


def _meta_path(csv_path: Path) -> Path:
    return csv_path.with_name(csv_path.stem + ".meta.json")


def load_frozen_history(csv_path: Union[str, Path]) -> MarketHistory:
    """Read the frozen CSV and its meta; the CSV hash must match the meta."""
    path = repo_path(csv_path)
    data = path.read_bytes()
    meta = json.loads(_meta_path(path).read_text(encoding="utf-8"))
    digest = hashlib.sha256(data).hexdigest()
    if digest != meta["sha256"]:
        raise ValueError(f"{path} does not match its meta sha256")
    df = pd.read_csv(io.BytesIO(data), parse_dates=["date"], index_col="date")
    return from_frame(
        df,
        source="coinmetrics_frozen",
        fetched_at=datetime.fromisoformat(meta["fetched_at"]),
        csv_sha256=digest,
    )


def compare_histories(live: MarketHistory, frozen: MarketHistory, rel_tol: float = 1e-6) -> pd.DataFrame:
    """Dates/columns where the live history differs from the frozen one on their common range.

    Mitigation for "CoinMetrics revises history". Returns columns ``date, column, frozen, live``.
    """
    common = live.daily.index.intersection(frozen.daily.index)
    a = frozen.daily.loc[common, COLUMNS]
    b = live.daily.loc[common, COLUMNS]
    rows = []
    for col in COLUMNS:
        x, y = a[col], b[col]
        both_nan = x.isna() & y.isna()
        one_nan = x.isna() ^ y.isna()
        rel = (y - x).abs() / x.abs().where(x.abs() > 0, 1.0)
        diff = one_nan | ((rel > rel_tol) & ~both_nan)
        for d in common[diff.to_numpy()]:
            rows.append({"date": d.date(), "column": col, "frozen": x.loc[d], "live": y.loc[d]})
    return pd.DataFrame(rows, columns=["date", "column", "frozen", "live"])


def derive_daily(history: MarketHistory, cfg: Config) -> pd.DataFrame:
    """Add the derived daily columns shared by the dashboard and the backtest."""
    d = history.daily.copy()
    d["mvrv_z"] = ind.mvrv_z(d["mc"], d["mvrv_ratio"])
    d["puell"] = ind.puell(d["iss_usd"])
    hr = ind.hash_ribbon_daily(d["hashrate"])
    d["hash_sma30"] = hr["hash_sma30"]
    d["hash_sma60"] = hr["hash_sma60"]
    d["hash_cross_up"] = hr["hash_cross_up"]
    d["sma111"] = ind.sma(d["price"], 111)
    d["sma350"] = ind.sma(d["price"], 350)
    d["sma471"] = ind.sma(d["price"], 471)
    d["ema150"] = ind.ema(d["price"], 150)
    d["picycle_spread"] = ind.picycle_spread(d["sma111"], d["sma350"])
    d["picycle_bottom"] = ind.picycle_bottom(d["ema150"], d["sma471"], cfg.score.picycle_bottom_factor)
    return d
