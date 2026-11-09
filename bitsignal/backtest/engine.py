"""Backtest orchestration (design §7, plan item 31).

Before the freeze (S6) only the calibration window is reported; the 2019+ criteria are computed
only with a frozen-parameters file whose ``model_hash`` matches the config in use.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Literal, Optional

import pandas as pd

from bitsignal.backtest import metrics as m
from bitsignal.backtest.benchmarks import buy_and_hold, uniform_complete
from bitsignal.backtest.portfolio import Simulation, ratchet_at, resolve_start, simulate
from bitsignal.config import Config, FrozenParams, apply_overrides, model_hash
from bitsignal.data.history import MarketHistory
from bitsignal.engine.pipeline import run_model

Window = Literal["calibration", "development"]


@dataclass
class BacktestReport:
    window: Window
    model_hash: str
    csv_sha256: Optional[str]
    start: date
    end: date
    strategy: Simulation
    bnh: Simulation
    uniform: Simulation
    criteria: Optional[Dict]
    diagnostics: Dict[str, object]
    false_resets: int
    reserve_usage: pd.DataFrame
    events: list
    weeks: pd.DataFrame
    sensitivities: Dict[str, Dict] = field(default_factory=dict)


def _summary(sim: Simulation) -> Dict[str, float]:
    eq = sim.equity["equity_usd"]
    return {"equity_end_usd": float(eq.dropna().iloc[-1]), "max_dd_pp": m.max_drawdown(eq)}


def _run_core(history: MarketHistory, cfg: Config, window: Window, start_override=None):
    result = run_model(history, cfg)
    price = history.daily["price"]
    last = price.dropna().index[-1].date()
    end = m.window_end(cfg, window, last)
    start_week = resolve_start(result, cfg, start_override)
    if start_week.date() > end:
        return None
    r0 = ratchet_at(result, start_week)
    strat = simulate(result, price, cfg, start_week.date(), r0, end)
    bnh = buy_and_hold(price, cfg, start_week.date(), end)
    uni = uniform_complete(history, cfg, start_week.date(), r0, end)
    return result, start_week, end, strat, bnh, uni


def run_backtest(
    history: MarketHistory,
    cfg: Config,
    window: Window = "calibration",
    frozen: Optional[FrozenParams] = None,
    sensitivities: bool = True,
) -> BacktestReport:
    if window == "development":
        if frozen is None:
            raise ValueError("window='development' requires the frozen parameters file (S6)")
        if frozen.model_hash != model_hash(cfg):
            raise ValueError("parameters in use differ from the frozen ones (model_hash mismatch)")
    elif window != "calibration":
        raise ValueError(f"unknown window {window!r}")

    core = _run_core(history, cfg, window)
    if core is None:
        raise ValueError("start of the portfolio falls after the end of the window")
    result, start_week, end, strat, bnh, uni = core
    price = history.daily["price"]

    crit = None
    if window == "development":
        crit = m.criteria(strat.equity["equity_usd"], bnh.equity["equity_usd"], uni.equity["equity_usd"], cfg)

    weeks = result.weeks.loc[start_week: pd.Timestamp(end)]
    diagnostics = {
        "summary": {"strategy": _summary(strat), "bnh": _summary(bnh), "uniform": _summary(uni)},
        "premature_sales": m.premature_sales(strat.trades, price),
        "false_sells": m.false_sells(strat.trades, price),
        "per_cycle": m.per_cycle(strat.trades, weeks, price),
        "events": m.event_diagnostics(strat.trades, price, cfg.backtest.events, strat.equity, strat.reserve_usd),
    }
    usage = m.reserve_usage(strat.trades, weeks, strat.reserve_usd, float(strat.equity["cash"].iloc[-1]))
    events = [e for e in result.events if e.date <= end]

    sens: Dict[str, Dict] = {}
    if sensitivities:
        for name, override in cfg.backtest.sensitivities.items():
            scfg = apply_overrides(cfg, override)
            sc = _run_core(history, scfg, window, scfg.backtest.start)
            if sc is None:
                sens[name] = {"applicable": False, "reason": "não aplicável: início depois do fim da janela"}
                continue
            _, s_start, _, s_strat, s_bnh, s_uni = sc
            entry = {"applicable": True, "start": s_start.date(), "strategy": _summary(s_strat),
                     "bnh": _summary(s_bnh), "uniform": _summary(s_uni)}
            if window == "development":
                entry["criteria"] = m.criteria(
                    s_strat.equity["equity_usd"], s_bnh.equity["equity_usd"], s_uni.equity["equity_usd"], scfg
                )
            sens[name] = entry

    return BacktestReport(
        window=window,
        model_hash=model_hash(cfg),
        csv_sha256=history.csv_sha256,
        start=start_week.date(),
        end=end,
        strategy=strat,
        bnh=bnh,
        uniform=uni,
        criteria=crit,
        diagnostics=diagnostics,
        false_resets=m.false_resets(result.events, end),
        reserve_usage=usage,
        events=events,
        weeks=weeks,
        sensitivities=sens,
    )


def _variant_entry(history: MarketHistory, vcfg: Config, window: Window) -> Dict:
    core = _run_core(history, vcfg, window)
    if core is None:
        return {"applicable": False}
    result, _, end, strat, bnh, uni = core
    trades = strat.trades
    done = trades[trades["status"] == "done"] if len(trades) else trades
    last = strat.equity.dropna().iloc[-1]
    entry = {
        "applicable": True,
        "strategy": _summary(strat),
        "bnh": _summary(bnh),
        "uniform": _summary(uni),
        "btc_end": float(last["btc"]),
        "cash_end": float(last["cash"]),
        "n_sells": int((done["side"] == "sell").sum()) if len(done) else 0,
        "n_cycles": sum(1 for e in result.events if e.type.value == "CYCLE_START" and strat.start < e.date <= end),
    }
    if window == "development":
        entry["criteria"] = m.criteria(
            strat.equity["equity_usd"], bnh.equity["equity_usd"], uni.equity["equity_usd"], vcfg
        )
    return entry


def run_variants(history: MarketHistory, cfg: Config, window: Window = "calibration",
                 frozen: Optional[FrozenParams] = None) -> Dict[str, Dict[str, Dict]]:
    """Phase 2: the default model and every catalog variant on the same window (comparison only).

    Same guard as ``run_backtest`` for the development window (frozen file with the same hash);
    the variants themselves are never frozen and never recorded.
    """
    from bitsignal.backtest.variants import POST_HOC, pre_registered

    if window == "development":
        if frozen is None or frozen.model_hash != model_hash(cfg):
            raise ValueError("window='development' requires the frozen parameters of the default model")
    elif window != "calibration":
        raise ValueError(f"unknown window {window!r}")
    out: Dict[str, Dict[str, Dict]] = {"default": {"default": _variant_entry(history, cfg, window)}}
    out["pre_registered"] = {n: _variant_entry(history, apply_overrides(cfg, o), window)
                             for n, o in pre_registered(cfg).items()}
    out["post_hoc"] = {n: _variant_entry(history, apply_overrides(cfg, o), window) for n, o in POST_HOC.items()}
    return out
