"""S4: valuation score states (design §4)."""

import numpy as np
import pytest

from bitsignal.config import load_config
from bitsignal.engine.score import normalize_linear, score_weekly
from bitsignal.models import InputState, ScoreStatus

from engine_helpers import score_input_frame

CFG = load_config()
MISSING = InputState.MISSING.value


def test_all_present_is_ok_and_midpoints_give_50():
    s = score_weekly(score_input_frame({}), CFG).iloc[0]
    assert s["status"] == ScoreStatus.OK.value
    # every continuous input at the midpoint (50) and hash ribbon NORMAL (50) -> 50
    assert s["score"] == pytest.approx(50.0)
    assert s["score_min"] == s["score_max"] == s["score"]


def test_picycle_bottom_forces_zero():
    s = score_weekly(score_input_frame({"picycle_bottom": True}), CFG).iloc[0]
    assert s["pts_picycle"] == 0.0


def test_interval_with_10_percent_continuous_missing_is_10_points_wide():
    df = score_input_frame({"rsi14w": np.nan}, {"rsi14w": MISSING})
    s = score_weekly(df, CFG).iloc[0]
    assert s["status"] == ScoreStatus.INTERVAL.value
    assert np.isnan(s["score"])
    assert s["score_max"] - s["score_min"] == pytest.approx(10.0)


def test_hash_ribbon_missing_uses_its_real_domain():
    df = score_input_frame({"hash_ribbon": np.nan}, {"hash_ribbon": MISSING})
    s = score_weekly(df, CFG).iloc[0]
    assert s["status"] == ScoreStatus.INTERVAL.value
    assert s["score_max"] - s["score_min"] == pytest.approx(0.10 * (50.0 - 10.0))


def test_essential_missing_is_unavailable():
    df = score_input_frame({"mvrv_z": np.nan}, {"mvrv_z": MISSING})
    s = score_weekly(df, CFG).iloc[0]
    assert s["status"] == ScoreStatus.UNAVAILABLE.value
    assert np.isnan(s["score"]) and np.isnan(s["score_min"]) and np.isnan(s["score_max"])


def test_more_than_20_percent_missing_is_unavailable():
    df = score_input_frame(
        {"picycle_spread": np.nan, "rsi14w": np.nan}, {"picycle": MISSING, "rsi14w": MISSING}
    )  # 15% + 10% = 25%
    assert score_weekly(df, CFG).iloc[0]["status"] == ScoreStatus.UNAVAILABLE.value


def test_nan_never_becomes_50():
    s = normalize_linear(__import__("pandas").Series([np.nan, -1.0, 10.0]), 0.0, 5.0)
    assert np.isnan(s.iloc[0])
    assert s.iloc[1] == 0.0 and s.iloc[2] == 100.0
