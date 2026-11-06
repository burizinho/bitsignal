"""Unit tests for the data integrity monitor and circuit breaker."""

from bitsignal.integrity import (
    evaluate_system_integrity,
    evaluate_timestamp_staleness,
)
from bitsignal.models import MetricStaleness, SystemStatus


def test_evaluate_timestamp_staleness():
    """Verify staleness classification based on elapsed hours."""
    now_ts = 1700000000

    # 10 hours ago -> FRESH (<= 36h)
    fresh_ts = now_ts - 10 * 3600
    assert evaluate_timestamp_staleness(fresh_ts, reference_timestamp=now_ts) == MetricStaleness.FRESH

    # 40 hours ago -> STALE (> 36h and <= 48h)
    stale_ts = now_ts - 40 * 3600
    assert evaluate_timestamp_staleness(stale_ts, reference_timestamp=now_ts) == MetricStaleness.STALE

    # 55 hours ago -> EXPIRED (> 48h)
    expired_ts = now_ts - 55 * 3600
    assert evaluate_timestamp_staleness(expired_ts, reference_timestamp=now_ts) == MetricStaleness.EXPIRED

    # None -> EXPIRED
    assert evaluate_timestamp_staleness(None, reference_timestamp=now_ts) == MetricStaleness.EXPIRED


def test_evaluate_system_integrity_healthy():
    """Verify system is HEALTHY when all metrics are fresh."""
    now_ts = 1700000000
    timestamps = {
        "mvrv_z": now_ts - 5 * 3600,
        "sma200w_ratio": now_ts - 5 * 3600,
        "puell_multiple": now_ts - 5 * 3600,
        "picycle": now_ts - 5 * 3600,
        "weekly_rsi": now_ts - 5 * 3600,
        "hash_ribbon": now_ts - 5 * 3600,
    }
    status, staleness_map, missing_weight = evaluate_system_integrity(
        timestamps, reference_timestamp=now_ts
    )
    assert status == SystemStatus.HEALTHY
    assert missing_weight == 0.0
    assert all(v == MetricStaleness.FRESH for v in staleness_map.values())


def test_evaluate_system_integrity_degraded():
    """Verify system enters DEGRADED when missing weight is <= 20%."""
    now_ts = 1700000000
    timestamps = {
        "mvrv_z": now_ts - 5 * 3600,
        "sma200w_ratio": now_ts - 5 * 3600,
        "puell_multiple": now_ts - 5 * 3600,
        "picycle": now_ts - 5 * 3600,
        "weekly_rsi": now_ts - 55 * 3600,  # EXPIRED (weight: 0.10)
        "hash_ribbon": now_ts - 5 * 3600,
    }
    status, staleness_map, missing_weight = evaluate_system_integrity(
        timestamps, reference_timestamp=now_ts
    )
    assert status == SystemStatus.DEGRADED
    assert missing_weight == 0.10
    assert staleness_map["weekly_rsi"] == MetricStaleness.EXPIRED


def test_evaluate_system_integrity_circuit_breaker_tripped():
    """Verify circuit breaker trips when missing weight > 20%."""
    now_ts = 1700000000
    timestamps = {
        "mvrv_z": now_ts - 55 * 3600,  # EXPIRED (weight: 0.25 > 0.20)
        "sma200w_ratio": now_ts - 5 * 3600,
        "puell_multiple": now_ts - 5 * 3600,
        "picycle": now_ts - 5 * 3600,
        "weekly_rsi": now_ts - 5 * 3600,
        "hash_ribbon": now_ts - 5 * 3600,
    }
    status, staleness_map, missing_weight = evaluate_system_integrity(
        timestamps, reference_timestamp=now_ts
    )
    assert status == SystemStatus.CIRCUIT_BREAKER_TRIPPED
    assert missing_weight == 0.25
    assert staleness_map["mvrv_z"] == MetricStaleness.EXPIRED
