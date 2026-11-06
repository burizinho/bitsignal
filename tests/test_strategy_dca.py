"""Unit tests for staged accumulation and distribution logic."""

from bitsignal.strategy.models import StageType, StrategyPhase, TransactionType
from bitsignal.strategy.national_dca import evaluate_cycle_stage

CYCLE_ATH = 126000.0


def test_accumulation_stages():
    # Price $95,000 (above -30% = $88,200) -> None
    assert evaluate_cycle_stage(95000.0, CYCLE_ATH, active_phase=StrategyPhase.ACCUMULATION) is None

    # Price $85,000 (below -30%) -> C0 (30%)
    res0 = evaluate_cycle_stage(85000.0, CYCLE_ATH, active_phase=StrategyPhase.ACCUMULATION)
    assert res0 == (StageType.C0, TransactionType.BUY, 0.30)

    # Price $68,000 (below -45% = $69,300) with C0 already executed -> C1 (15%)
    res1 = evaluate_cycle_stage(68000.0, CYCLE_ATH, executed_stages=["C0"], active_phase=StrategyPhase.ACCUMULATION)
    assert res1 == (StageType.C1, TransactionType.BUY, 0.15)

    # Price $55,000 (below -55% = $56,700) -> C2 (20%)
    res2 = evaluate_cycle_stage(55000.0, CYCLE_ATH, executed_stages=["C0", "C1"], active_phase=StrategyPhase.ACCUMULATION)
    assert res2 == (StageType.C2, TransactionType.BUY, 0.20)

    # Price $42,000 (below -65% = $44,100) -> C3 (20%)
    res3 = evaluate_cycle_stage(42000.0, CYCLE_ATH, executed_stages=["C0", "C1", "C2"], active_phase=StrategyPhase.ACCUMULATION)
    assert res3 == (StageType.C3, TransactionType.BUY, 0.20)

    # C3 triggered via MVRV Z-Score <= 0 even if price is above -65%
    res3_mvrv = evaluate_cycle_stage(
        50000.0, CYCLE_ATH, mvrv_z_score=-0.1, executed_stages=["C0", "C1", "C2"], active_phase=StrategyPhase.ACCUMULATION
    )
    assert res3_mvrv == (StageType.C3, TransactionType.BUY, 0.20)

    # C4 triggered on recovery above 50w SMA (e.g. 50w SMA = $48k, price = $50k)
    res4 = evaluate_cycle_stage(
        50000.0, CYCLE_ATH, sma_50w=48000.0, executed_stages=["C0", "C1", "C2", "C3"], active_phase=StrategyPhase.ACCUMULATION
    )
    assert res4 == (StageType.C4, TransactionType.BUY, 0.15)


def test_distribution_stages():
    # V1: Breaks ATH (> $126,000)
    res_v1 = evaluate_cycle_stage(128000.0, CYCLE_ATH, active_phase=StrategyPhase.DISTRIBUTION)
    assert res_v1 == (StageType.V1, TransactionType.SELL, 0.10)

    # V2: >= 1.3x ATH ($163,800)
    res_v2 = evaluate_cycle_stage(165000.0, CYCLE_ATH, executed_stages=["V1"], active_phase=StrategyPhase.DISTRIBUTION)
    assert res_v2 == (StageType.V2, TransactionType.SELL, 0.15)

    # V3: >= 1.6x ATH ($201,600)
    res_v3 = evaluate_cycle_stage(205000.0, CYCLE_ATH, executed_stages=["V1", "V2"], active_phase=StrategyPhase.DISTRIBUTION)
    assert res_v3 == (StageType.V3, TransactionType.SELL, 0.15)

    # V4: >= 2.0x ATH ($252,000)
    res_v4 = evaluate_cycle_stage(255000.0, CYCLE_ATH, executed_stages=["V1", "V2", "V3"], active_phase=StrategyPhase.DISTRIBUTION)
    assert res_v4 == (StageType.V4, TransactionType.SELL, 0.20)

    # V5: >= 2.5x ATH ($315,000)
    res_v5 = evaluate_cycle_stage(320000.0, CYCLE_ATH, executed_stages=["V1", "V2", "V3", "V4"], active_phase=StrategyPhase.DISTRIBUTION)
    assert res_v5 == (StageType.V5, TransactionType.SELL, 0.20)
