"""``minimal`` comparison model (Phase 2 design, D4; rule pre-registered in the Phase 1 §7).

Phase: ACCUMULATE if the weekly close < SMA200w; DISTRIBUTE if price/SMA200w >= 3.5 or Pi Cycle
Top (spread >= 1.0); HOLD otherwise (also while the SMA200w is warming up).
* New cycle at each entry into ACCUMULATE (sales reset to 0).
* Sales on the cycle base position: +15% the first week of the cycle with price/SMA200w >= 3.5 and
  +15% the first week with Pi Cycle Top (cap 30%).
* Buys only in ACCUMULATE, on the base reserve, once per ACCUMULATE phase each: 40% in the first
  week, 30% in the first week with a drawdown >= 50% of the reference ATH, 30% in the first week
  with >= 70% (both can fall in the same week).
* ``buys.mode = "uniform"`` (benchmark): 1/uniform_weeks of the reserve every ACCUMULATE week.

Produces the same columns ``simulate()`` reads, so the portfolio, the benchmarks and the
metrics run unchanged. Never used by the dashboard.
"""

from __future__ import annotations

from typing import List

import pandas as pd

from bitsignal.config import Config, model_hash
from bitsignal.data.history import MarketHistory, derive_daily
from bitsignal.engine.weekly import to_weekly
from bitsignal.models import Event, EventType, Phase, ReplayResult


def run_minimal(history: MarketHistory, cfg: Config) -> ReplayResult:
    weekly = to_weekly(derive_daily(history, cfg), history.as_of, cfg)
    weeks, events = replay_minimal(weekly, cfg)
    return ReplayResult(weeks=weeks, events=events, as_of=history.as_of, model_hash=model_hash(cfg))


def replay_minimal(weekly: pd.DataFrame, cfg: Config):
    mc = cfg.comparison.minimal
    uniform = cfg.buys.mode == "uniform"
    cycle_id = 0
    cycle_start = weekly.index[0] if len(weekly) else None
    ratchet = 0.0
    sold_ratio = sold_pi = False
    bought_first = bought_50 = bought_70 = False
    prev_acc = False
    rows: List[dict] = []
    events: List[Event] = []

    for t, w in weekly.iterrows():
        d = t.date()
        sma = w["sma200w"]
        ratio = w["price_to_sma200w"]
        spread = w["picycle_spread"]
        acc = bool(pd.notna(sma) and w["price"] < sma)
        ratio_hit = bool(pd.notna(ratio) and ratio >= mc.distribute_ratio)
        pi_hit = bool(pd.notna(spread) and spread >= mc.picycle_top_spread)

        if acc and not prev_acc:  # entry into ACCUMULATE: new cycle
            cycle_id += 1
            cycle_start = t
            ratchet = 0.0
            sold_ratio = sold_pi = False
            bought_first = bought_50 = bought_70 = False
            events.append(Event(d, EventType.CYCLE_START, "minimal", note="fechamento < SMA200w"))

        for hit, done, label in ((ratio_hit, sold_ratio, "preço/SMA200w"), (pi_hit, sold_pi, "Pi Cycle Top")):
            if hit and not done:
                new = min(mc.sell_cap, ratchet + mc.sell_step)
                if new > ratchet + 1e-12:
                    events.append(Event(d, EventType.SELL_STEP, "minimal", None, ratchet, new, note=label))
                    ratchet = new
        sold_ratio = sold_ratio or ratio_hit
        sold_pi = sold_pi or pi_hit

        buy = 0.0
        if acc:
            if uniform:
                buy = 1.0 / cfg.buys.uniform_weeks
            else:
                dd = 1.0 - float(w["price"]) / float(w["ath"])
                if not bought_first:
                    buy += mc.buy_first_week
                    bought_first = True
                if dd >= 0.50 and not bought_50:
                    buy += mc.buy_dd50
                    bought_50 = True
                if dd >= 0.70 and not bought_70:
                    buy += mc.buy_dd70
                    bought_70 = True

        if acc:
            phase = Phase.ACCUMULATE
        elif ratio_hit or pi_hit:
            phase = Phase.DISTRIBUTE
        else:
            phase = Phase.HOLD
        rows.append({
            "level": 0,
            "ratchet_sell": ratchet,
            "reset_pending": acc,
            "cycle_id": cycle_id,
            "cycle_start_date": cycle_start,
            "phase": phase.value,
            "buy_pct": buy,
        })
        prev_acc = acc

    state = pd.DataFrame(rows, index=weekly.index)
    return pd.concat([weekly, state], axis=1), events
