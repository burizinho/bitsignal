"""Data integrity, staleness monitoring, and circuit breaker mechanics."""

from datetime import datetime, timezone
from typing import Dict, Optional, Tuple
from bitsignal.models import MetricStaleness, SystemStatus

DEFAULT_WEIGHTS = {
    "mvrv_z": 0.25,
    "sma200w_ratio": 0.20,
    "puell_multiple": 0.20,
    "picycle": 0.15,
    "weekly_rsi": 0.10,
    "hash_ribbon": 0.10,
}


def evaluate_timestamp_staleness(
    metric_timestamp: Optional[int],
    reference_timestamp: Optional[int] = None,
    fresh_hours: float = 36.0,
    expired_hours: float = 48.0,
) -> MetricStaleness:
    """Classify metric staleness based on elapsed time."""
    if metric_timestamp is None:
        return MetricStaleness.EXPIRED

    now_ts = reference_timestamp or int(datetime.now(timezone.utc).timestamp())
    elapsed_hours = (now_ts - metric_timestamp) / 3600.0

    if elapsed_hours <= fresh_hours:
        return MetricStaleness.FRESH
    elif elapsed_hours <= expired_hours:
        return MetricStaleness.STALE
    else:
        return MetricStaleness.EXPIRED


def evaluate_system_integrity(
    metric_timestamps: Dict[str, Optional[int]],
    weights: Optional[Dict[str, float]] = None,
    reference_timestamp: Optional[int] = None,
    max_missing_tolerance: float = 0.20,
) -> Tuple[SystemStatus, Dict[str, MetricStaleness], float]:
    """Audit metric freshness, calculate missing weight, and determine system status."""
    applied_weights = weights or DEFAULT_WEIGHTS
    staleness_map: Dict[str, MetricStaleness] = {}
    missing_weight = 0.0

    for metric_name, weight in applied_weights.items():
        ts = metric_timestamps.get(metric_name)
        staleness = evaluate_timestamp_staleness(ts, reference_timestamp=reference_timestamp)
        staleness_map[metric_name] = staleness

        if staleness == MetricStaleness.EXPIRED:
            missing_weight += weight

    if missing_weight == 0.0:
        # Check if any are simply STALE (warning only)
        has_stale = any(s == MetricStaleness.STALE for s in staleness_map.values())
        status = SystemStatus.DEGRADED if has_stale else SystemStatus.HEALTHY
    elif missing_weight <= max_missing_tolerance:
        status = SystemStatus.DEGRADED
    else:
        status = SystemStatus.CIRCUIT_BREAKER_TRIPPED

    return status, staleness_map, round(missing_weight, 4)
