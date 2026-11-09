"""Data types for the unified cycle model (Phase 1, plan item 19).

Codes in English; screen labels in Portuguese.
"""

from dataclasses import dataclass, field as dc_field
from datetime import date as _date
from enum import Enum
from typing import Any, List, Optional


class HashRibbonState(str, Enum):
    NORMAL = "NORMAL"
    CAPITULATION = "CAPITULATION"
    BUY_RECOVERY = "BUY_RECOVERY"


class _Labeled(str, Enum):
    @property
    def label(self) -> str:
        return _LABELS[self.value]


class ScoreStatus(_Labeled):
    OK = "OK"
    INTERVAL = "INTERVAL"
    UNAVAILABLE = "UNAVAILABLE"


class InputState(_Labeled):
    PRESENT = "PRESENT"
    WARMUP = "WARMUP"
    MISSING = "MISSING"


class DataStatus(_Labeled):
    OK = "DATA_OK"
    STALE = "STALE"
    UNAVAILABLE = "SOURCE_UNAVAILABLE"


class Phase(_Labeled):
    ACCUMULATE = "ACCUMULATE"
    HOLD = "HOLD"
    DISTRIBUTE = "DISTRIBUTE"


class EventType(str, Enum):
    SELL_STEP = "SELL_STEP"
    DETECTOR_LEVEL = "DETECTOR_LEVEL"
    RESET_ARMED = "RESET_ARMED"
    CYCLE_START = "CYCLE_START"
    SCORE_UNAVAILABLE = "SCORE_UNAVAILABLE"


_LABELS = {
    "OK": "ok",
    "INTERVAL": "intervalo",
    "UNAVAILABLE": "indisponível",
    "PRESENT": "presente",
    "WARMUP": "aquecimento",
    "MISSING": "ausente",
    "DATA_OK": "ok",
    "STALE": "desatualizado",
    "SOURCE_UNAVAILABLE": "fonte indisponível",
    "ACCUMULATE": "ACUMULAR",
    "HOLD": "MANTER",
    "DISTRIBUTE": "DISTRIBUIR",
}


@dataclass(frozen=True)
class Event:
    date: _date
    type: EventType
    mechanism: str
    threshold: Optional[float] = None
    before: Optional[float] = None
    after: Optional[float] = None
    note: str = ""


@dataclass(frozen=True)
class Verdict:
    week: Optional[_date]
    data_status: DataStatus
    phase: Optional[Phase] = None
    sell_target: Optional[float] = None  # = ratchet_sell of the last week
    cycle_start: Optional[_date] = None  # = cycle_start_date
    buy_pct: Optional[float] = None  # None shows as "—"
    reason: str = ""
    score_status: Optional[ScoreStatus] = None  # = status column of the last week


@dataclass
class ReplayResult:
    weeks: Any  # pandas.DataFrame indexed by Sunday (W-SUN)
    events: List[Event] = dc_field(default_factory=list)
    as_of: Optional[_date] = None
    model_hash: str = ""
