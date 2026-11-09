"""Forward evaluation of the v2 model (Phase 3 design, decision E4). Display only.

Window: from the first Sunday on or after the v2 freeze date until the first of
  * the first new cycle (CYCLE_START of v2) that follows a DISTRIBUTE phase inside the window, or
  * 2030-12-31,
or the last data available (window still open).
A new portfolio starts at the window start (1 BTC + 0.5 BTC in USD), inheriting the model state
as in Phase 1. Criteria: the three Q1 criteria rebased at the window start, plus v2 >= v1.
Before the window ends nothing is concluded; this module never writes anything.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Optional

import pandas as pd

from bitsignal.backtest import metrics as m
from bitsignal.backtest.benchmarks import buy_and_hold, uniform_complete
from bitsignal.backtest.portfolio import ratchet_at, resolve_start, simulate
from bitsignal.config import Config, apply_overrides
from bitsignal.data.history import MarketHistory
from bitsignal.engine.pipeline import run_model
from bitsignal.models import EventType, Phase

DEADLINE = date(2030, 12, 31)


def window_end(weeks: pd.DataFrame, events, start: pd.Timestamp, deadline: date = DEADLINE) -> Optional[date]:
    """Closing date of the window, or None while it is still open."""
    after = weeks.loc[start:]
    for e in events:
        if e.type != EventType.CYCLE_START or pd.Timestamp(e.date) <= start:
            continue
        before = after.loc[: pd.Timestamp(e.date) - pd.Timedelta(days=1)]
        if (before["phase"] == Phase.DISTRIBUTE.value).any():
            return min(e.date, deadline)
    last = weeks.index[-1].date()
    return deadline if last >= deadline else None


def forward_eval(history: MarketHistory, cfg_v2: Config, cfg_v1: Config, frozen_at: date,
                 deadline: date = DEADLINE) -> Dict:
    price = history.daily["price"]
    r2 = run_model(history, cfg_v2)
    r1 = run_model(history, cfg_v1)
    later = r2.weeks.index[r2.weeks.index >= pd.Timestamp(frozen_at)]
    if not len(later):
        return {"status": "no_weeks", "frozen_at": frozen_at, "last_week": r2.weeks.index[-1].date()}
    start = resolve_start(r2, cfg_v2, later[0].date())
    closed = window_end(r2.weeks, r2.events, start, deadline)
    end = closed if closed is not None else price.dropna().index[-1].date()

    s2 = simulate(r2, price, cfg_v2, start.date(), ratchet_at(r2, start), end)
    s1 = simulate(r1, price, cfg_v1, start.date(), ratchet_at(r1, start), end)
    bnh = buy_and_hold(price, cfg_v2, start.date(), end)
    uni = uniform_complete(history, cfg_v2, start.date(), ratchet_at(r2, start), end)

    rebased = apply_overrides(cfg_v2, {"backtest": {"approval_window_start": start.date().isoformat()}})
    crit = m.criteria(s2.equity["equity_usd"], bnh.equity["equity_usd"], uni.equity["equity_usd"], rebased)
    eq2 = float(s2.equity["equity_usd"].dropna().iloc[-1])
    eq1 = float(s1.equity["equity_usd"].dropna().iloc[-1])
    crit["values"]["v2_vs_v1"] = eq2 / eq1
    crit["passed"]["v2_vs_v1"] = eq2 >= eq1
    return {
        "status": "closed" if closed is not None else "open",
        "start": start.date(),
        "end": end,
        "criteria": crit,
        "equity": {"v2": eq2, "v1": eq1, "bnh": float(bnh.equity["equity_usd"].dropna().iloc[-1]),
                   "uniform": float(uni.equity["equity_usd"].dropna().iloc[-1])},
    }


def to_text(res: Dict) -> str:
    if res["status"] == "no_weeks":
        return (f"Avaliação futura do v2: ainda não há semana fechada depois do congelamento "
                f"({res['frozen_at']}; última semana com dados: {res['last_week']}).")
    v, p = res["criteria"]["values"], res["criteria"]["passed"]
    ok = lambda b: "atingido" if b else "não atingido"  # noqa: E731
    state = ("JANELA ENCERRADA" if res["status"] == "closed"
             else "janela em andamento: só exibição, nenhuma conclusão registrada")
    e = res["equity"]
    return "\n".join([
        f"Avaliação futura do v2 (Fase 3, E4): {res['start']} → {res['end']} · {state}",
        f"  1. patrimônio / comprar e segurar = {v['equity_vs_bnh']:.3f} (meta ≥ 0,90) → {ok(p['equity_vs_bnh'])}",
        f"  2. melhora da queda máxima = {v['dd_improvement_pp']:.1f} p.p. (meta ≥ 10) → {ok(p['dd_improvement_pp'])}",
        f"  3. patrimônio / DCA uniforme = {v['equity_vs_uniform']:.3f} (meta ≥ 1,00) → {ok(p['equity_vs_uniform'])}",
        f"  4. patrimônio v2 / v1 = {v['v2_vs_v1']:.3f} (meta ≥ 1,00) → {ok(p['v2_vs_v1'])}",
        f"  Patrimônio (USD): v2 {e['v2']:,.0f} · v1 {e['v1']:,.0f} · comprar e segurar {e['bnh']:,.0f} · "
        f"DCA uniforme {e['uniform']:,.0f}",
    ])
