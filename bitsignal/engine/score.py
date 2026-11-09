"""Valuation score (design §4, plan item 21). Replaces normalizer.py in S8."""

from __future__ import annotations

import numpy as np
import pandas as pd

from bitsignal.config import INPUT_KEYS, Config
from bitsignal.models import InputState, ScoreStatus


def normalize_linear(series: pd.Series, lo: float, hi: float) -> pd.Series:
    """Linear map to 0–100 clipped at the ends; NaN stays NaN (never 50)."""
    return ((series - lo) / (hi - lo) * 100.0).clip(lower=0.0, upper=100.0)


def score_weekly(weekly: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    """Columns ``pts_<input>``, ``score``, ``score_min``, ``score_max``, ``status``."""
    sc = cfg.score
    out = pd.DataFrame(index=weekly.index)
    points = {}
    for name in INPUT_KEYS:
        inp = sc.inputs[name]
        if name == "hash_ribbon":
            pts = weekly["hash_ribbon"].map(sc.hash_ribbon_points).astype("float64")
        elif name == "picycle":
            pts = normalize_linear(weekly["picycle_spread"], inp.min, inp.max)
            bottom = weekly["picycle_bottom"].astype("boolean").fillna(False).astype(bool)
            pts = pts.where(~bottom, 0.0)
        else:
            pts = normalize_linear(weekly[name], inp.min, inp.max)
        present = (weekly[f"state_{name}"] == InputState.PRESENT.value).to_numpy()
        pts = pts.where(present)
        points[name] = pts
        out[f"pts_{name}"] = pts

    hr_vals = list(sc.hash_ribbon_points.values())
    dom_min = {n: (min(hr_vals) if n == "hash_ribbon" else 0.0) for n in INPUT_KEYS}
    dom_max = {n: (max(hr_vals) if n == "hash_ribbon" else 100.0) for n in INPUT_KEYS}

    known = pd.Series(0.0, index=weekly.index)
    lo = pd.Series(0.0, index=weekly.index)
    hi = pd.Series(0.0, index=weekly.index)
    missing_weight = pd.Series(0.0, index=weekly.index)
    essential_missing = pd.Series(False, index=weekly.index)
    for name in INPUT_KEYS:
        w = sc.inputs[name].weight
        miss = points[name].isna()
        contrib = (points[name] * w).fillna(0.0)
        known += contrib
        lo += contrib + miss * w * dom_min[name]
        hi += contrib + miss * w * dom_max[name]
        missing_weight += miss * w
        if name in sc.essential:
            essential_missing |= miss

    unavailable = essential_missing | (missing_weight > sc.max_missing_weight + 1e-12)
    interval = ~unavailable & (missing_weight > 0)
    status = np.where(unavailable, ScoreStatus.UNAVAILABLE.value,
                      np.where(interval, ScoreStatus.INTERVAL.value, ScoreStatus.OK.value))
    out["status"] = status
    ok = status == ScoreStatus.OK.value
    out["score"] = known.where(ok)
    out["score_min"] = lo.where(~unavailable)
    out["score_max"] = hi.where(~unavailable)
    return out
