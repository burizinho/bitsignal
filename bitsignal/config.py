"""Single validated configuration for the unified cycle model (design §2–§8, plan item 8).

Every model uses ``extra="forbid"``: an unknown key is an error, not silently ignored.
Paths in the config are resolved against the repository root, never the current directory.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "config.yaml"

INPUT_KEYS = ("mvrv_z", "price_to_sma200w", "puell", "picycle", "rsi14w", "hash_ribbon")
HASH_RIBBON_STATES = ("NORMAL", "CAPITULATION", "BUY_RECOVERY")

MODEL_FIELDS = ("score", "sell_ladder", "detector", "cap", "cycle", "buys")
MODEL_BACKTEST_FIELDS = (
    "initial_btc",
    "reserve_btc_equiv",
    "execution_lag_days",
    "fee",
    "approval_window_start",
    "criteria",
)


class ConfigError(Exception):
    """Invalid configuration. ``path`` is the dotted path of the offending field."""

    def __init__(self, path: str, message: str):
        self.path = path
        self.message = message
        super().__init__(f"{path}: {message}" if path else message)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------------------
# Blocks
# --------------------------------------------------------------------------------------


class InputConfig(_Strict):
    weight: float = Field(gt=0, le=1)
    min: Optional[float] = None
    max: Optional[float] = None


class ScoreConfig(_Strict):
    inputs: Dict[str, InputConfig]
    hash_ribbon_points: Dict[str, float]
    picycle_bottom_factor: float = Field(gt=0, lt=1)
    essential: List[str]
    max_missing_weight: float = Field(gt=0, lt=1)

    @model_validator(mode="after")
    def _check(self) -> "ScoreConfig":
        keys = set(self.inputs)
        if keys != set(INPUT_KEYS):
            raise ValueError(f"inputs must be exactly {sorted(INPUT_KEYS)}, got {sorted(keys)}")
        total = sum(i.weight for i in self.inputs.values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"input weights must sum to 1.0, got {total}")
        for name, inp in self.inputs.items():
            if name == "hash_ribbon":
                if inp.min is not None or inp.max is not None:
                    raise ValueError("inputs.hash_ribbon has no min/max (discrete state)")
                continue
            if inp.min is None or inp.max is None:
                raise ValueError(f"inputs.{name} needs min and max")
            if not inp.max > inp.min:
                raise ValueError(f"inputs.{name}: max must be greater than min")
        if set(self.hash_ribbon_points) != set(HASH_RIBBON_STATES):
            raise ValueError(f"hash_ribbon_points must have exactly {list(HASH_RIBBON_STATES)}")
        unknown = set(self.essential) - keys
        if unknown:
            raise ValueError(f"essential has unknown inputs: {sorted(unknown)}")
        return self


class DetectorConfig(_Strict):
    arming_weeks: int = Field(gt=0)
    trend_sma_weeks: int = Field(gt=0)
    confirm_weeks: int = Field(gt=0)
    trigger_max_ratio_to_high52: float = Field(gt=0, le=1)
    n2_sma_weeks: int = Field(gt=0)
    n3_max_ratio_to_high52: float = Field(gt=0, le=1)
    levels: List[float]

    @field_validator("levels")
    @classmethod
    def _levels(cls, v: List[float]) -> List[float]:
        if len(v) != 3:
            raise ValueError("levels must have exactly 3 values (N1, N2, N3)")
        if not all(0 < x for x in v) or not all(a < b for a, b in zip(v, v[1:])):
            raise ValueError("levels must be positive and strictly increasing")
        return v


class CapConfig(_Strict):
    floor: float = Field(gt=0, lt=1)

    @property
    def cap(self) -> float:
        """Maximum cumulative sale as a fraction of the cycle base position (1 - floor)."""
        return 1.0 - self.floor


class CycleConfig(_Strict):
    arm_score: float = Field(ge=0, le=100)
    arm_weeks: int = Field(gt=0)
    confirm_score: float = Field(ge=0, le=100)
    confirm_weeks: int = Field(gt=0)

    @model_validator(mode="after")
    def _order(self) -> "CycleConfig":
        if not self.arm_score < self.confirm_score:
            raise ValueError("arm_score must be lower than confirm_score")
        return self


class BuysConfig(_Strict):
    mode: Literal["score_dca", "uniform"]
    tiers: List[Tuple[float, float]]
    uniform_weeks: int = Field(gt=0)

    @field_validator("tiers")
    @classmethod
    def _tiers(cls, v: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if not v:
            raise ValueError("tiers must not be empty")
        limits = [t[0] for t in v]
        if not all(a < b for a, b in zip(limits, limits[1:])):
            raise ValueError("tier limits must be strictly increasing")
        if not all(0 < t[1] <= 1 for t in v):
            raise ValueError("tier percentages must be in (0, 1]")
        return v


class CriteriaConfig(_Strict):
    equity_vs_bnh: float = Field(gt=0)
    dd_improvement_pp: float = Field(ge=0)
    equity_vs_uniform: float = Field(gt=0)


class EventConfig(_Strict):
    name: str
    kind: Literal["top", "bottom"]
    window: Tuple[date, date]

    @field_validator("window")
    @classmethod
    def _window(cls, v: Tuple[date, date]) -> Tuple[date, date]:
        if not v[0] < v[1]:
            raise ValueError("event window start must be before end")
        return v


class BacktestConfig(_Strict):
    initial_btc: float = Field(gt=0)
    reserve_btc_equiv: float = Field(ge=0)
    start: Union[Literal["first_all_valid_week"], date]
    execution_lag_days: int = Field(ge=1)
    fee: float = Field(ge=0, lt=0.1)
    calibration_end: date
    approval_window_start: date
    criteria: CriteriaConfig
    sensitivities: Dict[str, Dict[str, Any]]
    events: List[EventConfig]
    frozen_params: Optional[str] = None

    @model_validator(mode="after")
    def _dates(self) -> "BacktestConfig":
        if not self.calibration_end < self.approval_window_start:
            raise ValueError("calibration_end must be before approval_window_start")
        return self


class DataConfig(_Strict):
    csv_path: str
    max_staleness_days: int = Field(gt=0)


class UiConfig(_Strict):
    cache_ttl_coinmetrics: str
    cache_ttl_spot: str
    retry_cooldown_s: int = Field(ge=0)


class MinimalConfig(_Strict):
    """Pre-registered ``minimal`` model (Phase 2 design, D4). Comparison only."""

    distribute_ratio: float = 3.5  # price / SMA200w
    picycle_top_spread: float = 1.0  # SMA111 / (2 x SMA350)
    sell_step: float = 0.15  # per trigger, on the cycle base position
    sell_cap: float = 0.30
    buy_first_week: float = 0.40  # of the base reserve
    buy_dd50: float = 0.30
    buy_dd70: float = 0.30


class ComparisonConfig(_Strict):
    """Comparison-only options (Phase 2). Outside ``model_hash``; the dashboard rejects any
    non-default value (``validate_for_panel``)."""

    model: Literal["default", "minimal"] = "default"
    detector_enabled: bool = True  # False: level always 0 (also stops blocking the reset; D2)
    detector_arming: Literal["ath", "score60", "score35"] = "ath"
    leftover_on_reset: bool = False  # buy all remaining cash when a new cycle starts
    buy_sizing: Literal["reserve", "cash"] = "reserve"  # % of the base reserve or of current cash
    floor_base: Literal["cycle", "initial"] = "cycle"  # floor on the cycle base or the initial BTC
    minimal: MinimalConfig = Field(default_factory=MinimalConfig)


class Config(_Strict):
    score: ScoreConfig
    sell_ladder: List[Tuple[float, float]]
    detector: DetectorConfig
    cap: CapConfig
    cycle: CycleConfig
    buys: BuysConfig
    backtest: BacktestConfig
    data: DataConfig
    ui: UiConfig
    comparison: ComparisonConfig = Field(default_factory=ComparisonConfig)

    @field_validator("sell_ladder")
    @classmethod
    def _ladder(cls, v: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if not v:
            raise ValueError("sell_ladder must not be empty")
        thr = [s[0] for s in v]
        pct = [s[1] for s in v]
        if not all(a < b for a, b in zip(thr, thr[1:])):
            raise ValueError("sell_ladder thresholds must be strictly increasing")
        if not all(a < b for a, b in zip(pct, pct[1:])) or not all(0 < p for p in pct):
            raise ValueError("sell_ladder percentages must be positive and strictly increasing")
        return v

    @model_validator(mode="after")
    def _cross(self) -> "Config":
        cap = self.cap.cap
        if self.detector.levels[-1] > cap + 1e-12:
            raise ValueError(f"detector.levels must not exceed 1 - floor ({cap})")
        if self.sell_ladder[-1][1] > cap + 1e-12:
            raise ValueError(f"sell_ladder percentages must not exceed 1 - floor ({cap})")
        return self


# --------------------------------------------------------------------------------------
# Loading, overrides and paths
# --------------------------------------------------------------------------------------


def _wrap(exc: ValidationError) -> ConfigError:
    err = exc.errors()[0]
    path = ".".join(str(p) for p in err.get("loc", ()))
    return ConfigError(path, err.get("msg", str(exc)))


def config_from_dict(raw: Dict[str, Any]) -> Config:
    """Validate a raw dict (as read from YAML) into a ``Config``."""
    try:
        return Config.model_validate(raw)
    except ValidationError as exc:
        raise _wrap(exc) from None


def load_config(path: Optional[Union[str, Path]] = None) -> Config:
    """Load and validate the YAML config (default: ``<repo>/config/config.yaml``).

    Also checks that every ``backtest.sensitivities`` override produces a valid config.
    """
    p = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    with open(p, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    if not isinstance(raw, dict):
        raise ConfigError("", f"{p} is not a mapping")
    cfg = config_from_dict(raw)
    for name, override in cfg.backtest.sensitivities.items():
        try:
            apply_overrides(cfg, override)
        except ConfigError as exc:
            raise ConfigError(f"backtest.sensitivities.{name}.{exc.path}", exc.message) from None
    return cfg


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)  # scalars and lists replace
    return out


def apply_overrides(cfg: Config, overrides: Dict[str, Any]) -> Config:
    """Return a new validated ``Config`` with ``overrides`` deep-merged.

    Dictionaries merge recursively, lists are replaced whole, and the result is revalidated.
    ``cfg`` is never modified.
    """
    merged = _deep_merge(cfg.model_dump(mode="python"), overrides)
    return config_from_dict(merged)


def repo_path(relative: Union[str, Path]) -> Path:
    """Resolve a path from the config against the repository root."""
    p = Path(relative)
    return p if p.is_absolute() else REPO_ROOT / p


# --------------------------------------------------------------------------------------
# Model hash and frozen parameters
# --------------------------------------------------------------------------------------


def model_payload(cfg: Config) -> Dict[str, Any]:
    """The parameters that affect decisions: ``MODEL_FIELDS`` plus ``MODEL_BACKTEST_FIELDS``.

    ``data``, ``ui``, paths, ``backtest.frozen_params`` and the sensitivities stay out.
    """
    dumped = cfg.model_dump(mode="json")
    payload = {k: dumped[k] for k in MODEL_FIELDS}
    payload["backtest"] = {k: dumped["backtest"][k] for k in MODEL_BACKTEST_FIELDS}
    return payload


def model_hash(cfg: Config) -> str:
    """SHA-256 of the canonical JSON of ``model_payload`` (sorted keys, no spaces)."""
    canonical = json.dumps(model_payload(cfg), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CriteriaPassed(_Strict):
    equity_vs_bnh: bool
    dd_improvement_pp: bool
    equity_vs_uniform: bool


class CriteriaValues(_Strict):
    equity_vs_bnh: float
    dd_improvement_pp: float
    equity_vs_uniform: float


class Approval(_Strict):
    run_at: datetime
    window: Literal["development"]
    passed: CriteriaPassed
    values: CriteriaValues


class FrozenParams(_Strict):
    frozen_at: datetime
    csv_sha256: str
    model_hash: str
    model: Dict[str, Any]
    approval: Optional[Approval] = None


def load_frozen_params(path: Optional[Union[str, Path]]) -> Optional[FrozenParams]:
    """Load a frozen-parameters file; ``None`` when ``path`` is empty or the file does not exist."""
    if not path:
        return None
    p = repo_path(path)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    try:
        return FrozenParams.model_validate(raw)
    except ValidationError as exc:
        raise _wrap(exc) from None


def write_frozen_params(path: Union[str, Path], frozen: FrozenParams) -> Path:
    """Write the frozen parameters as YAML with sorted keys."""
    p = repo_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump(frozen.model_dump(mode="json"), fh, sort_keys=True, allow_unicode=True)
    return p


def validate_for_panel(cfg: Config) -> None:
    """Reject comparison-only options in the config used for the dashboard verdict.

    Comparison options: ``buys.mode = "uniform"`` (uniform benchmark) and the whole
    ``comparison`` block (Phase 2 variants).
    """
    if cfg.buys.mode != "score_dca":
        raise ConfigError("buys.mode", "opção só para backtest")
    default = ComparisonConfig().model_dump()
    for key, value in cfg.comparison.model_dump().items():
        if value != default[key]:
            raise ConfigError(f"comparison.{key}", "opção só para backtest")
