"""Unit tests for the alert dispatcher and Telegram markdown runbooks."""

from unittest.mock import patch
import pytest
from bitsignal.alerts.dispatcher import (
    build_telegram_message,
    process_and_dispatch_alerts,
)
from bitsignal.models import (
    AlertType,
    DailyCompositeResult,
    HysteresisState,
    SystemStatus,
)


@pytest.fixture
def sample_result():
    return DailyCompositeResult(
        date="2026-11-05",
        composite_score=83.5,
        mvrv_score=88.0,
        sma200w_score=85.0,
        puell_score=82.0,
        picycle_score=80.0,
        rsi_score=78.0,
        hashribbon_score=50.0,
        system_status=SystemStatus.HEALTHY,
        hysteresis_state=HysteresisState.TOP_TIER_1,
        stale_metrics=None,
        metric_attribution={
            "mvrv_score": 22.0,
            "sma200w_score": 17.0,
            "puell_score": 16.4,
        },
    )


def test_build_telegram_message_tier1(sample_result):
    """Verify Tier 1 alert contains exact standardized runbook values."""
    msg = build_telegram_message(sample_result, AlertType.TOP_TIER_1)
    assert "BITSIGNAL MACRO TOP WARNING (TIER 1)" in msg
    assert "20% divestment tranche" in msg
    assert "80%" in msg  # retained
    assert "60%" in msg  # permanent sovereign reserve


def test_build_telegram_message_tier2(sample_result):
    """Verify Tier 2 alert contains exact standardized runbook values."""
    msg = build_telegram_message(sample_result, AlertType.TOP_TIER_2)
    assert "BITSIGNAL MACRO TOP WARNING (TIER 2)" in msg
    assert "30% cumulative exit" in msg
    assert "70%" in msg


def test_build_telegram_message_tier3(sample_result):
    """Verify Tier 3 alert contains exact standardized runbook values."""
    msg = build_telegram_message(sample_result, AlertType.TOP_TIER_3)
    assert "MAXIMUM EUPHORIA WARNING (TIER 3)" in msg
    assert "40% cumulative exit maximum" in msg
    assert "CEASE FURTHER DIVESTMENT" in msg


def test_build_telegram_message_bottom(sample_result):
    """Verify bottom capitulation runbook message."""
    msg = build_telegram_message(sample_result, AlertType.BOTTOM_CAPITULATION)
    assert "MACRO BOTTOM ACCUMULATION" in msg
    assert "DCA" in msg


def test_build_telegram_message_circuit_breaker(sample_result):
    """Verify circuit breaker diagnostic message."""
    cb_result = sample_result.model_copy(
        update={
            "system_status": SystemStatus.CIRCUIT_BREAKER_TRIPPED,
            "stale_metrics": "mvrv_z",
        }
    )
    msg = build_telegram_message(cb_result, AlertType.CIRCUIT_BREAKER)
    assert "CIRCUIT BREAKER TRIPPED" in msg
    assert "FROZEN" in msg


@patch("bitsignal.alerts.dispatcher.dispatch_telegram_alert")
def test_process_and_dispatch_alerts_hysteresis_suppression(mock_dispatch, sample_result):
    """Verify that repeated calls in same hysteresis tier suppress duplicate alerts."""
    mock_dispatch.return_value = True

    # 1. First time entering TOP_TIER_1 from NEUTRAL -> should dispatch alert
    alert1 = process_and_dispatch_alerts(
        result=sample_result,
        previous_state=HysteresisState.NEUTRAL,
        bot_token="test_token",
        chat_id="test_chat",
        dry_run=True,
    )
    assert alert1 == AlertType.TOP_TIER_1

    # 2. Subsequent day still in TOP_TIER_1 -> should suppress alert
    alert2 = process_and_dispatch_alerts(
        result=sample_result,
        previous_state=HysteresisState.TOP_TIER_1,
        bot_token="test_token",
        chat_id="test_chat",
        dry_run=True,
    )
    assert alert2 is None
