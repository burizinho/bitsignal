"""Pydantic V2 data models for BitSignal."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class HashRibbonState(str, Enum):
    NORMAL = "NORMAL"
    CAPITULATION = "CAPITULATION"
    BUY_RECOVERY = "BUY_RECOVERY"


class MetricStaleness(str, Enum):
    FRESH = "FRESH"
    STALE = "STALE"
    EXPIRED = "EXPIRED"


class SystemStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CIRCUIT_BREAKER_TRIPPED = "CIRCUIT_BREAKER_TRIPPED"


class HysteresisState(str, Enum):
    NEUTRAL = "NEUTRAL"
    TOP_TIER_1 = "TOP_TIER_1"
    TOP_TIER_2 = "TOP_TIER_2"
    TOP_TIER_3 = "TOP_TIER_3"
    BOTTOM_CAPITULATION = "BOTTOM_CAPITULATION"


class AlertType(str, Enum):
    TOP_TIER_1 = "TOP_TIER_1"
    TOP_TIER_2 = "TOP_TIER_2"
    TOP_TIER_3 = "TOP_TIER_3"
    BOTTOM_CAPITULATION = "BOTTOM_CAPITULATION"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"


class MarketCandle(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataSnapshot(BaseModel):
    date: str
    daily_candles: List[MarketCandle]
    weekly_candles: List[MarketCandle]


class MiningDataSnapshot(BaseModel):
    date: str
    hashrate: float
    hashrate_30d: float
    hashrate_60d: float
    status: HashRibbonState


class OnChainSnapshot(BaseModel):
    date: str
    mvrv_z: Optional[float] = None
    puell_multiple: Optional[float] = None
    timestamp: Optional[int] = None


class DailyMetrics(BaseModel):
    date: str
    btc_price: float
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None
    sma_111: Optional[float] = None
    sma_350: Optional[float] = None
    sma_471: Optional[float] = None
    ema_150: Optional[float] = None
    sma_200w: Optional[float] = None
    rsi_14w: Optional[float] = None
    mvrv_z: Optional[float] = None
    puell_multiple: Optional[float] = None
    hashrate: Optional[float] = None
    hash_ribbon_status: Optional[str] = None


class NormalizedMetricScore(BaseModel):
    raw_value: Optional[float] = None
    sub_score: float = Field(ge=0.0, le=100.0)
    applied_weight: float = Field(ge=0.0, le=1.0)
    staleness: MetricStaleness = MetricStaleness.FRESH


class DailyCompositeResult(BaseModel):
    date: str
    composite_score: float = Field(ge=0.0, le=100.0)
    mvrv_score: float = Field(ge=0.0, le=100.0)
    sma200w_score: float = Field(ge=0.0, le=100.0)
    puell_score: float = Field(ge=0.0, le=100.0)
    picycle_score: float = Field(ge=0.0, le=100.0)
    rsi_score: float = Field(ge=0.0, le=100.0)
    hashribbon_score: float = Field(ge=0.0, le=100.0)
    system_status: SystemStatus
    hysteresis_state: HysteresisState
    stale_metrics: Optional[str] = None
    metric_attribution: Dict[str, float] = Field(default_factory=dict)
