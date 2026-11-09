"""Phase 2 comparison catalog (design: docs/designs/bitcoin_cycle_phase2_variants.md).

Each variant is a config override applied to the default model. ``PRE_REGISTERED`` is the catalog
fixed in the Phase 1 design (§7) before any result was seen; ``POST_HOC`` (decision D1) was chosen
after the decomposition of the default model and is reported apart. None of them can replace the
default model, and every window is already known: these are diagnostics, not approvals.

Out of the executable set: ``norm_hybrid`` (D3) and ``reset_dd60`` (D5).
"""

from __future__ import annotations

from typing import Dict

from bitsignal.config import Config


def threshold_shift(cfg: Config, delta: float) -> dict:
    """``thr_plus5`` / ``thr_minus5``: every score threshold shifted by ``delta`` points (sell
    ladder, reset arm/confirm and buy tiers). Percentages do not change."""
    return {
        "sell_ladder": [[thr + delta, pct] for thr, pct in cfg.sell_ladder],
        "cycle": {"arm_score": cfg.cycle.arm_score + delta, "confirm_score": cfg.cycle.confirm_score + delta},
        "buys": {"tiers": [[thr + delta, pct] for thr, pct in cfg.buys.tiers]},
    }


def pre_registered(cfg: Config) -> Dict[str, dict]:
    return {
        "ladder_only": {"comparison": {"detector_enabled": False}},
        "arm_score60": {"comparison": {"detector_arming": "score60"}},
        "arm_score35": {"comparison": {"detector_arming": "score35"}},
        "det_sma20": {"detector": {"trend_sma_weeks": 20}},
        "norm_high": {"score": {"inputs": {
            "mvrv_z": {"max": 7.0},
            "price_to_sma200w": {"max": 5.0},
            "puell": {"max": 3.5},
            "rsi14w": {"max": 85.0},
        }}},
        "minimal": {"comparison": {"model": "minimal"}},
        "floor40": {"cap": {"floor": 0.40}},
        # Design §7: "o N3 de 50% fica limitado a 40%" (the config forbids levels above the cap).
        "floor60": {"cap": {"floor": 0.60},
                    "detector": {"levels": [min(lv, 0.40) for lv in cfg.detector.levels]}},
        "leftover_buy": {"comparison": {"leftover_on_reset": True}},
        "thr_plus5": threshold_shift(cfg, 5.0),
        "thr_minus5": threshold_shift(cfg, -5.0),
    }


POST_HOC: Dict[str, dict] = {
    "proceeds_dca": {"comparison": {"buy_sizing": "cash"}},
    "floor_initial": {"comparison": {"floor_base": "initial"}},
}

PRE_REGISTERED_NAMES = (
    "ladder_only", "arm_score60", "arm_score35", "det_sma20", "norm_high", "minimal",
    "floor40", "floor60", "leftover_buy", "thr_plus5", "thr_minus5",
)
POST_HOC_NAMES = ("proceeds_dca", "floor_initial")
