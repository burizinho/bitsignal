"""Weekly trailing stop evaluator for Bitcoin macro cycle protection."""

from typing import Optional, Tuple
import pandas as pd
from bitsignal.engine.indicators import calculate_ema, calculate_sma
from bitsignal.strategy.models import StageType


def compute_weekly_indicators(weekly_closes: pd.Series) -> Tuple[Optional[float], Optional[float]]:
    """Calculate 21-week EMA and 50-week SMA from weekly candle series.

    Reuses validated indicators from bitsignal.engine.indicators.
    """
    if len(weekly_closes) == 0:
        return None, None

    ema_21w = (
        float(calculate_ema(weekly_closes, 21).iloc[-1])
        if len(weekly_closes) >= 21
        else None
    )
    sma_50w = (
        float(calculate_sma(weekly_closes, 50).iloc[-1])
        if len(weekly_closes) >= 50
        else None
    )
    return ema_21w, sma_50w


def evaluate_trailing_stops(
    weekly_close_price: float,
    ema_21w: Optional[float],
    sma_50w: Optional[float],
    already_executed_stops: Optional[list] = None,
) -> Optional[StageType]:
    """Evaluate whether Sunday weekly close breaches key trailing supports.

    Precedence:
    - Stop 2 (Weekly Close < 50w SMA): Severe breakdown -> Exit 100% remaining balance (except Moonbag)
    - Stop 1 (Weekly Close < 21w EMA): Bull support loss -> Exit 50% remaining balance
    """
    executed = already_executed_stops or []

    # Stop 2 takes precedence if 50w SMA is breached and not yet executed
    if sma_50w is not None and weekly_close_price < sma_50w:
        if StageType.STOP_2.value not in executed and StageType.STOP_2 not in executed:
            return StageType.STOP_2

    # Stop 1 fires if 21w EMA is breached and neither Stop 1 nor Stop 2 was executed
    if ema_21w is not None and weekly_close_price < ema_21w:
        if (
            StageType.STOP_1.value not in executed
            and StageType.STOP_1 not in executed
            and StageType.STOP_2.value not in executed
            and StageType.STOP_2 not in executed
        ):
            return StageType.STOP_1

    return None
