"""Unit tests for weekly trailing stops evaluation."""

import pandas as pd
from bitsignal.strategy.models import StageType
from bitsignal.strategy.trailing_stops import (
    compute_weekly_indicators,
    evaluate_trailing_stops,
)


def test_compute_weekly_indicators():
    # 60 weekly candles
    closes = pd.Series([10000.0 + i * 500 for i in range(60)])
    ema_21, sma_50 = compute_weekly_indicators(closes)

    assert ema_21 is not None
    assert sma_50 is not None
    assert ema_21 > sma_50  # Upward trending


def test_evaluate_trailing_stops_no_breach():
    # Price above both 21w EMA and 50w SMA
    stage = evaluate_trailing_stops(
        weekly_close_price=100000.0,
        ema_21w=90000.0,
        sma_50w=70000.0,
        already_executed_stops=[],
    )
    assert stage is None


def test_evaluate_trailing_stops_stop1_breach():
    # Price below 21w EMA (90k) but above 50w SMA (70k)
    stage = evaluate_trailing_stops(
        weekly_close_price=85000.0,
        ema_21w=90000.0,
        sma_50w=70000.0,
        already_executed_stops=[],
    )
    assert stage == StageType.STOP_1

    # Should not re-fire if already executed
    assert evaluate_trailing_stops(85000.0, 90000.0, 70000.0, ["STOP_1"]) is None


def test_evaluate_trailing_stops_stop2_breach():
    # Price below 50w SMA (70k) -> Stop 2 takes precedence
    stage = evaluate_trailing_stops(
        weekly_close_price=65000.0,
        ema_21w=80000.0,
        sma_50w=70000.0,
        already_executed_stops=[],
    )
    assert stage == StageType.STOP_2

    # If Stop 1 was previously executed, Stop 2 still fires on deeper breakdown
    assert evaluate_trailing_stops(65000.0, 80000.0, 70000.0, ["STOP_1"]) == StageType.STOP_2
