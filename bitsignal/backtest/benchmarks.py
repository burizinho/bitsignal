"""Q1 benchmarks (plan item 29): buy-and-hold and the complete uniform DCA."""

from __future__ import annotations

from datetime import date
from typing import Optional

import pandas as pd

from bitsignal.backtest.portfolio import EPS, Simulation, _check_identity, _equity, _exec_day, simulate
from bitsignal.config import Config, apply_overrides
from bitsignal.data.history import MarketHistory
from bitsignal.engine.pipeline import run_model


def buy_and_hold(daily_price: pd.Series, cfg: Config, start: date, end: Optional[date] = None) -> Simulation:
    """All capital in BTC: the reserve is converted at the execution of the first week."""
    bt = cfg.backtest
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end) if end is not None else daily_price.dropna().index[-1]
    btc = float(bt.initial_btc)
    reserve_usd = float(bt.reserve_btc_equiv) * float(daily_price.loc[start_ts])
    cash = reserve_usd
    changes = [(start_ts, btc, cash)]
    trades = []
    day = _exec_day(daily_price, start_ts, bt.execution_lag_days, end_ts)
    if day is not None and cash > EPS:
        price = float(daily_price.loc[day])
        d_btc = cash * (1.0 - bt.fee) / price
        _check_identity(-cash, d_btc, price, -bt.fee * cash)
        trades.append({"week": start_ts.date(), "exec_date": day.date(), "side": "buy", "btc": d_btc, "usd": cash,
                       "price": price, "fee_usd": bt.fee * cash, "status": "done", "cycle_id": None, "phase": None})
        btc += d_btc
        cash = 0.0
        changes.append((day, btc, cash))
    cols = ["week", "exec_date", "side", "btc", "usd", "price", "fee_usd", "status", "cycle_id", "phase"]
    return Simulation(pd.DataFrame(trades, columns=cols), _equity(daily_price, changes, start_ts, end_ts), reserve_usd, start_ts.date())


def uniform_complete(
    history: MarketHistory, cfg: Config, start: date, ratchet_at_start: float, end: Optional[date] = None
) -> Simulation:
    """Same sales (ladder + detector, same ratchet in % of the base position), uniform buys of
    1/uniform_weeks of the reserve every ACCUMULATE week (whatever the score status), same
    capital, start and leftover-cash policy. The uniform branch lives in ``replay()`` step 5."""
    ucfg = apply_overrides(cfg, {"buys": {"mode": "uniform"}})
    result = run_model(history, ucfg)
    return simulate(result, history.daily["price"], ucfg, start, ratchet_at_start, end)
