"""Normalization and Composite Scoring Engine."""

from typing import Dict, Optional
from bitsignal.models import (
    DailyCompositeResult,
    HashRibbonState,
    HysteresisState,
    MetricStaleness,
    SystemStatus,
)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a floating point value between min_val and max_val."""
    return max(min_val, min(value, max_val))


def normalize_linear(value: Optional[float], min_val: float, max_val: float) -> float:
    """Normalize scalar value into 0 to 100 scale using clamped linear mapping."""
    if value is None:
        return 50.0
    if max_val <= min_val:
        return 50.0
    raw_norm = ((value - min_val) / (max_val - min_val)) * 100.0
    return clamp(raw_norm, 0.0, 100.0)


def normalize_picycle(
    spread_ratio: Optional[float],
    is_bottom_active: bool,
    min_ratio: float = 0.70,
    max_ratio: float = 1.00,
) -> float:
    """Normalize Pi Cycle indicators into 0 to 100 scale."""
    if is_bottom_active:
        return 0.0
    if spread_ratio is None:
        return 50.0
    return normalize_linear(spread_ratio, min_ratio, max_ratio)


def score_hash_ribbon(status: Optional[str]) -> float:
    """Map discrete Hash Ribbon state to sub-score."""
    if not status:
        return 50.0
    state_str = status.upper()
    if state_str == HashRibbonState.BUY_RECOVERY.value:
        return 10.0
    elif state_str == HashRibbonState.CAPITULATION.value:
        return 20.0
    return 50.0  # NORMAL


def calculate_composite_score(
    date: str,
    mvrv_z: Optional[float],
    sma200w_ratio: Optional[float],
    puell_multiple: Optional[float],
    picycle_spread: Optional[float],
    is_picycle_bottom: bool,
    weekly_rsi: Optional[float],
    hash_ribbon_status: Optional[str],
    system_status: SystemStatus = SystemStatus.HEALTHY,
    current_hysteresis: HysteresisState = HysteresisState.NEUTRAL,
    staleness_map: Optional[Dict[str, MetricStaleness]] = None,
) -> DailyCompositeResult:
    """Compute normalized sub-scores, apply weights, and compute composite score."""
    staleness = staleness_map or {}

    # 1. Compute sub-scores (or impute 50 if expired)
    def resolve_sub_score(metric_name: str, calculated_score: float) -> float:
        if staleness.get(metric_name) == MetricStaleness.EXPIRED:
            return 50.0
        return calculated_score

    s_mvrv = resolve_sub_score("mvrv_z", normalize_linear(mvrv_z, 0.15, 5.00))
    s_sma200w = resolve_sub_score("sma200w_ratio", normalize_linear(sma200w_ratio, 1.00, 3.50))
    s_puell = resolve_sub_score("puell_multiple", normalize_linear(puell_multiple, 0.45, 2.20))
    s_picycle = resolve_sub_score(
        "picycle", normalize_picycle(picycle_spread, is_picycle_bottom, 0.70, 1.00)
    )
    s_rsi = resolve_sub_score("weekly_rsi", normalize_linear(weekly_rsi, 32.0, 80.0))
    s_hashribbon = resolve_sub_score("hash_ribbon", score_hash_ribbon(hash_ribbon_status))

    # 2. Weighted Sum
    # Weights: MVRV 25%, 200w 20%, Puell 20%, Pi 15%, RSI 10%, Hash 10%
    weights = {
        "mvrv_score": 0.25,
        "sma200w_score": 0.20,
        "puell_score": 0.20,
        "picycle_score": 0.15,
        "rsi_score": 0.10,
        "hashribbon_score": 0.10,
    }

    sub_scores = {
        "mvrv_score": s_mvrv,
        "sma200w_score": s_sma200w,
        "puell_score": s_puell,
        "picycle_score": s_picycle,
        "rsi_score": s_rsi,
        "hashribbon_score": s_hashribbon,
    }

    composite_score = sum(weights[k] * sub_scores[k] for k in weights)
    composite_score = clamp(round(composite_score, 2), 0.0, 100.0)

    # Calculate metric attribution in points
    attribution = {k: round(weights[k] * sub_scores[k], 2) for k in weights}

    # Evaluate hysteresis state transition
    next_hysteresis = evaluate_hysteresis_state(composite_score, current_hysteresis)

    # Stale metric names
    stale_names = [k for k, v in staleness.items() if v != MetricStaleness.FRESH]
    stale_str = ", ".join(stale_names) if stale_names else None

    return DailyCompositeResult(
        date=date,
        composite_score=composite_score,
        mvrv_score=s_mvrv,
        sma200w_score=s_sma200w,
        puell_score=s_puell,
        picycle_score=s_picycle,
        rsi_score=s_rsi,
        hashribbon_score=s_hashribbon,
        system_status=system_status,
        hysteresis_state=next_hysteresis,
        stale_metrics=stale_str,
        metric_attribution=attribution,
    )


def evaluate_hysteresis_state(
    score: float, current_state: HysteresisState
) -> HysteresisState:
    """Evaluate state transition adhering to multi-tier deadbands."""
    # Top Escalation: Tier 3 (>=90) > Tier 2 (>=85) > Tier 1 (>=80)
    if score >= 90.0:
        return HysteresisState.TOP_TIER_3
    elif score >= 85.0:
        if current_state == HysteresisState.TOP_TIER_3 and score >= 87.0:
            return HysteresisState.TOP_TIER_3
        return HysteresisState.TOP_TIER_2
    elif score >= 80.0:
        if current_state == HysteresisState.TOP_TIER_3 and score >= 87.0:
            return HysteresisState.TOP_TIER_3
        elif current_state == HysteresisState.TOP_TIER_2 and score >= 82.0:
            return HysteresisState.TOP_TIER_2
        return HysteresisState.TOP_TIER_1

    # Between 75 and 80: deadband zone for Tier 1
    if 75.0 <= score < 80.0:
        if current_state in (
            HysteresisState.TOP_TIER_1,
            HysteresisState.TOP_TIER_2,
            HysteresisState.TOP_TIER_3,
        ):
            # Retain Tier 1 until strictly below 75
            return HysteresisState.TOP_TIER_1
        return HysteresisState.NEUTRAL

    # Bottom Capitulation (<=20) with deadband up to 25
    if score <= 20.0:
        return HysteresisState.BOTTOM_CAPITULATION
    elif 20.0 < score <= 25.0:
        if current_state == HysteresisState.BOTTOM_CAPITULATION:
            return HysteresisState.BOTTOM_CAPITULATION
        return HysteresisState.NEUTRAL

    # Default Neutral regime
    return HysteresisState.NEUTRAL
