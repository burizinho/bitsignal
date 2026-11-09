"""Synthetic frames shared by the engine tests."""

import numpy as np
import pandas as pd

from bitsignal.config import INPUT_KEYS
from bitsignal.models import InputState, ScoreStatus

SUNDAY0 = pd.Timestamp("2020-01-05")  # a Sunday


def weeks_index(n):
    return pd.date_range(SUNDAY0, periods=n, freq="7D", name="week")


def weekly_detector_frame(n, **cols):
    """Weekly frame with the columns the detector reads. Defaults: calm market, no ATH."""
    idx = weeks_index(n)
    base = {
        "price": np.full(n, 100.0),
        "trend_sma": np.full(n, 90.0),
        "n2_sma": np.full(n, 70.0),
        "high52w": np.full(n, 100.0),
        "new_ath": np.zeros(n, dtype=bool),
    }
    for k, v in cols.items():
        base[k] = v
    return pd.DataFrame(base, index=idx)


def score_frame(index, score_min, score_max=None, status=None):
    score_min = pd.Series(score_min, index=index, dtype="float64")
    score_max = score_min if score_max is None else pd.Series(score_max, index=index, dtype="float64")
    status = pd.Series(status if status is not None else [ScoreStatus.OK.value] * len(index), index=index)
    return pd.DataFrame(
        {"score": score_min.where(status == ScoreStatus.OK.value), "score_min": score_min,
         "score_max": score_max, "status": status},
        index=index,
    )


def detector_frame(index, levels=None):
    levels = list(levels) if levels is not None else [0] * len(index)
    return pd.DataFrame(
        {"level": levels, "armed": [False] * len(index),
         "episode_id": pd.array([None] * len(index), dtype="Int64"),
         "episode_closing": [False] * len(index)},
        index=index,
    )


def score_input_frame(values, states=None):
    """One-row weekly frame with raw input values and states for score tests."""
    idx = weeks_index(1)
    row = {
        "mvrv_z": values.get("mvrv_z", 2.575),
        "price_to_sma200w": values.get("price_to_sma200w", 2.25),
        "puell": values.get("puell", 1.325),
        "picycle_spread": values.get("picycle_spread", 0.85),
        "picycle_bottom": values.get("picycle_bottom", False),
        "rsi14w": values.get("rsi14w", 56.0),
        "hash_ribbon": values.get("hash_ribbon", "NORMAL"),
    }
    df = pd.DataFrame({k: [v] for k, v in row.items()}, index=idx)
    df["picycle_bottom"] = df["picycle_bottom"].astype("boolean")
    states = states or {}
    for name in INPUT_KEYS:
        df[f"state_{name}"] = states.get(name, InputState.PRESENT.value)
    return df
