"""Unit tests for the SQLite storage layer."""

import os
import tempfile
import pytest
from bitsignal.models import (
    DailyCompositeResult,
    DailyMetrics,
    HysteresisState,
    SystemStatus,
)
from bitsignal.storage.db import (
    get_historical_scores,
    get_latest_hysteresis_state,
    get_latest_score,
    init_db,
    record_alert_dispatch,
    upsert_daily_metrics,
    upsert_daily_score,
)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database file for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)


def test_init_db(temp_db):
    """Verify tables are created upon initialization."""
    assert os.path.exists(temp_db)
    state = get_latest_hysteresis_state(temp_db)
    assert state == HysteresisState.NEUTRAL


def test_upsert_daily_metrics(temp_db):
    """Verify inserting and updating daily metrics."""
    metrics1 = DailyMetrics(
        date="2026-11-01",
        btc_price=68000.0,
        open=67500.0,
        high=68500.0,
        low=67000.0,
        volume=12000.0,
        sma_111=65000.0,
        sma_350=58000.0,
        sma_471=55000.0,
        ema_150=64000.0,
        sma_200w=38000.0,
        rsi_14w=65.0,
        mvrv_z=2.45,
        puell_multiple=1.20,
        hashrate=6.2e20,
        hash_ribbon_status="NORMAL",
    )
    upsert_daily_metrics(metrics1, temp_db)

    # Idempotent update for same date
    metrics2 = metrics1.model_copy(update={"btc_price": 69000.0})
    upsert_daily_metrics(metrics2, temp_db)


def test_upsert_and_get_daily_score(temp_db):
    """Verify inserting, retrieving, and updating daily composite scores."""
    score1 = DailyCompositeResult(
        date="2026-11-01",
        composite_score=78.5,
        mvrv_score=80.0,
        sma200w_score=75.0,
        puell_score=70.0,
        picycle_score=85.0,
        rsi_score=72.0,
        hashribbon_score=50.0,
        system_status=SystemStatus.HEALTHY,
        hysteresis_state=HysteresisState.NEUTRAL,
        stale_metrics=None,
    )
    upsert_daily_score(score1, temp_db)

    latest = get_latest_score(temp_db)
    assert latest is not None
    assert latest["date"] == "2026-11-01"
    assert latest["composite_score"] == 78.5
    assert latest["system_status"] == "HEALTHY"
    assert latest["hysteresis_state"] == "NEUTRAL"

    # Verify state transition
    score2 = score1.model_copy(
        update={
            "date": "2026-11-02",
            "composite_score": 82.0,
            "hysteresis_state": HysteresisState.TOP_TIER_1,
        }
    )
    upsert_daily_score(score2, temp_db)

    latest_state = get_latest_hysteresis_state(temp_db)
    assert latest_state == HysteresisState.TOP_TIER_1

    history = get_historical_scores(temp_db)
    assert len(history) == 2
    assert history[0]["date"] == "2026-11-01"
    assert history[1]["date"] == "2026-11-02"


def test_record_alert_dispatch(temp_db):
    """Verify logging alert dispatches."""
    alert_id = record_alert_dispatch(
        date="2026-11-02",
        alert_type="TOP_TIER_1",
        composite_score=82.0,
        payload="Alert payload content",
        delivered_telegram=True,
        db_path=temp_db,
    )
    assert alert_id == 1
