"""Reversal detector (design §5 is normative; plan item 22).

Per week, in this order: trigger (if no active episode) -> levels N2/N3 -> closing test
(not on the trigger week). On the closing week ``level`` still shows the episode level; from
the next week it is 0. Week counts are per valid weekly row.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd

from bitsignal.config import Config


def _consecutive(cond: pd.Series, k: int) -> pd.Series:
    """True when ``cond`` held on this row and the previous k-1 rows."""
    return cond.astype(int).rolling(k, min_periods=k).sum().eq(k)


SCORE60_WEEKS = 26  # arm_score60 (pre-registered, design §7)


def _armed(weekly: pd.DataFrame, cfg: Config, score_df: Optional[pd.DataFrame]) -> pd.Series:
    """Arming rule. ``ath`` is the model; ``score60`` / ``score35`` are Phase 2 comparisons."""
    mode = cfg.comparison.detector_arming
    if mode == "ath":
        return weekly["new_ath"].astype(int).rolling(cfg.detector.arming_weeks, min_periods=1).max().astype(bool)
    if score_df is None:
        raise ValueError(f"detector_arming={mode!r} needs score_df")
    valid = score_df["status"] != "UNAVAILABLE"
    if mode == "score60":
        cond = valid & (score_df["score_max"] >= 60)
        return cond.astype(int).rolling(SCORE60_WEEKS, min_periods=1).max().astype(bool)
    return (valid & (score_df["score_min"] > 35)).astype(bool)


def detect(weekly: pd.DataFrame, cfg: Config, score_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    det = cfg.detector
    k = det.confirm_weeks
    price = weekly["price"]
    armed = _armed(weekly, cfg, score_df)
    if not cfg.comparison.detector_enabled:  # ladder_only (D2): no episode, never blocks the reset
        armed = pd.Series(False, index=weekly.index)
    below_trend = _consecutive(price < weekly["trend_sma"], k)
    above_trend = _consecutive(price > weekly["trend_sma"], k)
    below_n2 = _consecutive(price < weekly["n2_sma"], k)
    trigger_cond = armed & below_trend & (price <= det.trigger_max_ratio_to_high52 * weekly["high52w"])
    n3_cond = price <= det.n3_max_ratio_to_high52 * weekly["high52w"]

    n = len(weekly)
    level = [0] * n
    triggered = [False] * n
    closing = [False] * n
    episode_id: List[Optional[int]] = [None] * n

    active = False
    cur_level = 0
    eid = 0
    for i in range(n):
        start_week = False
        if not active and bool(trigger_cond.iat[i]):
            active = True
            start_week = True
            eid += 1
            cur_level = 1
            triggered[i] = True
        if active:
            if cur_level == 1 and bool(below_n2.iat[i]):
                cur_level = 2
            if cur_level == 2 and bool(n3_cond.iat[i]):
                cur_level = 3
            level[i] = cur_level
            episode_id[i] = eid
            if not start_week and bool(above_trend.iat[i]):
                closing[i] = True
                active = False
                cur_level = 0

    out = pd.DataFrame(index=weekly.index)
    out["armed"] = armed
    out["triggered"] = triggered
    out["episode_id"] = pd.array(episode_id, dtype="Int64")
    out["episode_closing"] = closing
    out["level"] = level
    pct = [0.0] + list(det.levels)
    out["v_det"] = [pct[lv] for lv in level]
    return out


def episodes(detect_df: pd.DataFrame) -> List[Dict[str, Optional[object]]]:
    """Convert detector columns into the golden schema: start, n2, n3, end, max_level."""
    result = []
    ids = detect_df["episode_id"].dropna().unique()
    for eid in ids:
        rows = detect_df[detect_df["episode_id"] == eid]
        lv = rows["level"]

        def first(cond):
            idx = rows.index[cond.to_numpy()]
            return idx[0].date().isoformat() if len(idx) else None

        closed = rows["episode_closing"].any()
        result.append(
            {
                "start": rows.index[0].date().isoformat(),
                "n2": first(lv >= 2),
                "n3": first(lv >= 3),
                "end": rows.index[-1].date().isoformat() if closed else None,
                "max_level": int(lv.max()),
            }
        )
    return result
