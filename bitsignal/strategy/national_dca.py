"""Deterministic staged accumulation and distribution logic for Bitcoin cycle."""

from typing import List, Optional, Tuple
from bitsignal.strategy.models import StageType, StrategyPhase, TransactionType


def evaluate_cycle_stage(
    price_usd: float,
    cycle_ath_usd: float = 126000.0,
    mvrv_z_score: Optional[float] = None,
    sma_50w: Optional[float] = None,
    executed_stages: Optional[List[str]] = None,
    active_phase: StrategyPhase = StrategyPhase.ACCUMULATION,
) -> Optional[Tuple[StageType, TransactionType, float]]:
    """Determine if current market price triggers an entry or exit stage.

    Returns:
        Optional[Tuple[StageType, TransactionType, allocation_percentage]]
        where allocation_percentage is relative to Reserve R (for buys)
        or relative to initial Base Portfolio P0 (for sells).
    """
    history = set(executed_stages or [])

    # ==========================
    # 1. ACCUMULATION (BEAR MARKET)
    # ==========================
    if active_phase == StrategyPhase.ACCUMULATION:
        # C4: Confirmation of recovery (Close > 50w SMA after at least one accumulation stage)
        if (
            StageType.C4.value not in history
            and sma_50w is not None
            and price_usd > sma_50w
            and any(s in history for s in ["C0", "C1", "C2", "C3"])
        ):
            # 15% base + any unallocated stages from C1..C3
            unallocated = 0.15
            if "C1" not in history and price_usd <= 0.55 * cycle_ath_usd:
                unallocated += 0.15
            if "C2" not in history and price_usd <= 0.45 * cycle_ath_usd:
                unallocated += 0.20
            if "C3" not in history and (price_usd <= 0.35 * cycle_ath_usd or (mvrv_z_score is not None and mvrv_z_score <= 0.0)):
                unallocated += 0.20
            return StageType.C4, TransactionType.BUY, unallocated

        # C3: -65% drawdown (<= 0.35 * ATH) OR MVRV Z-Score <= 0.0
        if StageType.C3.value not in history:
            if price_usd <= 0.35 * cycle_ath_usd or (mvrv_z_score is not None and mvrv_z_score <= 0.0):
                return StageType.C3, TransactionType.BUY, 0.20

        # C2: -55% drawdown (<= 0.45 * ATH)
        if StageType.C2.value not in history and price_usd <= 0.45 * cycle_ath_usd:
            return StageType.C2, TransactionType.BUY, 0.20

        # C1: -45% drawdown (<= 0.55 * ATH)
        if StageType.C1.value not in history and price_usd <= 0.55 * cycle_ath_usd:
            return StageType.C1, TransactionType.BUY, 0.15

        # C0: -30% drawdown (<= 0.70 * ATH) - DCA Base (30% in DCA tranches)
        if StageType.C0.value not in history and price_usd <= 0.70 * cycle_ath_usd:
            return StageType.C0, TransactionType.BUY, 0.30

    # ==========================
    # 2. DISTRIBUTION (BULL MARKET)
    # ==========================
    elif active_phase == StrategyPhase.DISTRIBUTION:
        # V5: 2.5x ATH (>= 2.50 * ATH) -> 20%
        if StageType.V5.value not in history and price_usd >= 2.50 * cycle_ath_usd:
            return StageType.V5, TransactionType.SELL, 0.20

        # V4: 2.0x ATH (>= 2.00 * ATH) -> 20%
        if StageType.V4.value not in history and price_usd >= 2.00 * cycle_ath_usd:
            return StageType.V4, TransactionType.SELL, 0.20

        # V3: 1.6x ATH (>= 1.60 * ATH) -> 15%
        if StageType.V3.value not in history and price_usd >= 1.60 * cycle_ath_usd:
            return StageType.V3, TransactionType.SELL, 0.15

        # V2: 1.3x ATH (>= 1.30 * ATH) -> 15%
        if StageType.V2.value not in history and price_usd >= 1.30 * cycle_ath_usd:
            return StageType.V2, TransactionType.SELL, 0.15

        # V1: New ATH (price > 1.00 * ATH) -> 10%
        if StageType.V1.value not in history and price_usd > 1.00 * cycle_ath_usd:
            return StageType.V1, TransactionType.SELL, 0.10

    return None
