"""Unit tests for normalization and composite scoring engine."""

import pytest
from bitsignal.engine.normalizer import (
    calculate_composite_score,
    clamp,
    evaluate_hysteresis_state,
    normalize_linear,
    normalize_picycle,
    score_hash_ribbon,
)
from bitsignal.models import HysteresisState, MetricStaleness, SystemStatus


def test_clamp():
    """Verify clamping helper."""
    assert clamp(5.0, 0.0, 10.0) == 5.0
    assert clamp(-2.0, 0.0, 10.0) == 0.0
    assert clamp(15.0, 0.0, 10.0) == 10.0


def test_normalize_linear():
    """Verify clamped linear normalization."""
    # Min -> 0
    assert normalize_linear(0.15, 0.15, 5.0) == 0.0
    # Below Min -> 0
    assert normalize_linear(0.05, 0.15, 5.0) == 0.0
    # Max -> 100
    assert normalize_linear(5.0, 0.15, 5.0) == 100.0
    # Above Max -> 100
    assert normalize_linear(6.5, 0.15, 5.0) == 100.0
    # Midpoint
    mid = 0.15 + (5.0 - 0.15) / 2
    assert pytest.approx(normalize_linear(mid, 0.15, 5.0), 0.1) == 50.0


def test_normalize_picycle():
    """Verify Pi Cycle normalization logic."""
    # Bottom cross active overrides to 0
    assert normalize_picycle(0.95, is_bottom_active=True) == 0.0

    # Normal mapping between 0.70 and 1.00
    assert normalize_picycle(0.70, is_bottom_active=False) == 0.0
    assert normalize_picycle(1.00, is_bottom_active=False) == 100.0
    assert pytest.approx(normalize_picycle(0.85, is_bottom_active=False), 0.1) == 50.0


def test_score_hash_ribbon():
    """Verify discrete Hash Ribbon state sub-scores."""
    assert score_hash_ribbon("NORMAL") == 50.0
    assert score_hash_ribbon("CAPITULATION") == 20.0
    assert score_hash_ribbon("BUY_RECOVERY") == 10.0


def test_evaluate_hysteresis_state_deadbands():
    """Verify multi-tier alert hysteresis deadbands."""
    # Escalate to Tier 1
    state = evaluate_hysteresis_state(82.0, HysteresisState.NEUTRAL)
    assert state == HysteresisState.TOP_TIER_1

    # Fluctuating within deadband (78.0) retains Tier 1
    state = evaluate_hysteresis_state(78.0, HysteresisState.TOP_TIER_1)
    assert state == HysteresisState.TOP_TIER_1

    # Dropping strictly below 75 resets to NEUTRAL
    state = evaluate_hysteresis_state(74.5, HysteresisState.TOP_TIER_1)
    assert state == HysteresisState.NEUTRAL

    # Escalate to Tier 2
    state = evaluate_hysteresis_state(86.0, HysteresisState.TOP_TIER_1)
    assert state == HysteresisState.TOP_TIER_2

    # Fluctuating within Tier 2 deadband (83.0) retains Tier 2
    state = evaluate_hysteresis_state(83.0, HysteresisState.TOP_TIER_2)
    assert state == HysteresisState.TOP_TIER_2

    # Escalate to Tier 3
    state = evaluate_hysteresis_state(92.0, HysteresisState.TOP_TIER_2)
    assert state == HysteresisState.TOP_TIER_3

    # Bottom Capitulation trigger and deadband
    b_state = evaluate_hysteresis_state(18.0, HysteresisState.NEUTRAL)
    assert b_state == HysteresisState.BOTTOM_CAPITULATION

    # Rise into deadband (23.0) retains BOTTOM_CAPITULATION
    b_state = evaluate_hysteresis_state(23.0, HysteresisState.BOTTOM_CAPITULATION)
    assert b_state == HysteresisState.BOTTOM_CAPITULATION

    # Rise strictly above 25 resets to NEUTRAL
    b_state = evaluate_hysteresis_state(26.0, HysteresisState.BOTTOM_CAPITULATION)
    assert b_state == HysteresisState.NEUTRAL


def test_calculate_composite_score_with_imputation():
    """Verify composite calculation and neutral imputation under degraded state."""
    # When all are neutral/baseline
    res = calculate_composite_score(
        date="2026-11-05",
        mvrv_z=2.575,  # mid -> 50
        sma200w_ratio=2.25,  # mid -> 50
        puell_multiple=1.325,  # mid -> 50
        picycle_spread=0.85,  # mid -> 50
        is_picycle_bottom=False,
        weekly_rsi=56.0,  # mid -> 50
        hash_ribbon_status="NORMAL",  # 50
        system_status=SystemStatus.HEALTHY,
    )
    assert pytest.approx(res.composite_score, 0.5) == 50.0

    # Impute missing metric (e.g. weekly_rsi expired, weight 10%)
    staleness_map = {"weekly_rsi": MetricStaleness.EXPIRED}
    res_degraded = calculate_composite_score(
        date="2026-11-05",
        mvrv_z=2.575,
        sma200w_ratio=2.25,
        puell_multiple=1.325,
        picycle_spread=0.85,
        is_picycle_bottom=False,
        weekly_rsi=None,  # missing
        hash_ribbon_status="NORMAL",
        system_status=SystemStatus.DEGRADED,
        staleness_map=staleness_map,
    )
    # Neutral imputation should keep composite score at 50
    assert pytest.approx(res_degraded.composite_score, 0.5) == 50.0
    assert res_degraded.rsi_score == 50.0
