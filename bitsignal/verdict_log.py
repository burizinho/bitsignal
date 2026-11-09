"""Append-only weekly log of the model verdict (forward validation).

Each closed week gets one row with what the model said at the time it was recorded. Rows are never
rewritten: later revisions of the CoinMetrics data do not change past rows. This is the only
record of the model that is not retrospective. It is not a record of the user's transactions.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Union

import pandas as pd

from bitsignal.models import ReplayResult, Verdict

COLUMNS = [
    "week",
    "recorded_at",
    "phase",
    "sell_target",
    "buy_pct",
    "score",
    "score_min",
    "score_max",
    "score_status",
    "detector_level",
    "reset_pending",
    "cycle_start_date",
    "price_usd",
    "data_as_of",
    "model_hash",
    "reason",
]


def _num(x, digits: int = 6) -> str:
    if x is None or pd.isna(x):
        return ""
    return f"{float(x):.{digits}f}"


def verdict_row(result: ReplayResult, verdict: Verdict, recorded_at: datetime) -> Dict[str, str]:
    """One log row from the verdict and the last row of ``result.weeks`` (same week)."""
    if verdict.phase is None:
        raise ValueError(f"no verdict to record: {verdict.reason}")
    last = result.weeks.iloc[-1]
    if result.weeks.index[-1].date() != verdict.week:
        raise ValueError("verdict and replay refer to different weeks")
    return {
        "week": verdict.week.isoformat(),
        "recorded_at": recorded_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "phase": verdict.phase.value,
        "sell_target": _num(verdict.sell_target, 4),
        "buy_pct": "all_cash" if verdict.buy_all_cash else _num(verdict.buy_pct, 4),
        "score": _num(last["score"], 2),
        "score_min": _num(last["score_min"], 2),
        "score_max": _num(last["score_max"], 2),
        "score_status": verdict.score_status.value if verdict.score_status else "",
        "detector_level": str(int(last["level"])),
        "reset_pending": str(bool(last["reset_pending"])).lower(),
        "cycle_start_date": verdict.cycle_start_date.isoformat(),
        "price_usd": _num(last["price"], 2),
        "data_as_of": result.as_of.isoformat() if result.as_of else "",
        "model_hash": result.model_hash,
        "reason": verdict.reason,
    }


def last_recorded_week(path: Union[str, Path]) -> Optional[str]:
    p = Path(path)
    if not p.exists():
        return None
    with io.open(p, encoding="utf-8", newline="") as f:
        weeks = [r["week"] for r in csv.DictReader(f)]
    return weeks[-1] if weeks else None


def last_recorded_hash(path: Union[str, Path]) -> Optional[str]:
    """``model_hash`` of the last row, so one file never mixes two models."""
    p = Path(path)
    if not p.exists():
        return None
    with io.open(p, encoding="utf-8", newline="") as f:
        hashes = [r["model_hash"] for r in csv.DictReader(f)]
    return hashes[-1] if hashes else None


def append_verdict(path: Union[str, Path], row: Dict[str, str]) -> bool:
    """Append ``row`` if its week is newer than the last recorded one. Returns True if written.

    A week already recorded (or older) is never rewritten, so the log keeps what the model said
    at the time.
    """
    p = Path(path)
    last = last_recorded_week(p)
    if last is not None and row["week"] <= last:
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    new_file = not p.exists()
    with io.open(p, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        if new_file:
            w.writeheader()
        w.writerow(row)
    return True
