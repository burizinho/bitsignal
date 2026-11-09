"""Portfolio simulation (design §7, plan item 28).

Executes the weekly targets of the replay on daily prices, without future information:
the operation of week W (Sunday D) uses the price of D + ``execution_lag_days`` (or the first
day with a price within 7 days; otherwise the operation is skipped and recorded).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

import pandas as pd

from bitsignal.config import Config
from bitsignal.models import ReplayResult

EPS = 1e-12
FALLBACK_DAYS = 7


@dataclass
class Simulation:
    trades: pd.DataFrame  # one row per executed/skipped operation
    equity: pd.DataFrame  # daily: btc, cash, equity_usd
    reserve_usd: float
    start: date


def _exec_day(daily_price: pd.Series, sunday: pd.Timestamp, lag: int, end: pd.Timestamp) -> Optional[pd.Timestamp]:
    target = sunday + pd.Timedelta(days=lag)
    window = daily_price.loc[target : min(target + pd.Timedelta(days=FALLBACK_DAYS), end)].dropna()
    return window.index[0] if len(window) else None


def _check_identity(d_cash: float, d_btc: float, price: float, expected: float) -> None:
    notional = abs(d_btc * price)
    if abs((d_cash + d_btc * price) - expected) > 1e-9 * max(1.0, notional):
        raise AssertionError(f"conservation violated: Δcash={d_cash} Δbtc·p={d_btc * price} expected={expected}")


def simulate(
    result: ReplayResult,
    daily_price: pd.Series,
    cfg: Config,
    start: date,
    ratchet_at_start: float,
    end: Optional[date] = None,
) -> Simulation:
    """Simulate the continuous portfolio from ``start`` (a W-SUN Sunday) until ``end``."""
    bt = cfg.backtest
    cmp_ = cfg.comparison  # Phase 2 options; defaults reproduce the model exactly
    fee = bt.fee
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end) if end is not None else daily_price.dropna().index[-1]
    weeks = result.weeks.loc[start_ts:end_ts]

    btc = float(bt.initial_btc)
    reserve_usd = float(bt.reserve_btc_equiv) * float(daily_price.loc[start_ts])
    cash = reserve_usd
    floor_btc = cfg.cap.floor * btc  # floor_base = "initial": never sell below this

    cycle_id = int(weeks["cycle_id"].iloc[0]) if len(weeks) else 0
    base_btc = btc
    baseline = float(ratchet_at_start)
    sold_in_cycle = 0.0

    trades: List[dict] = []
    changes = [(start_ts, btc, cash)]

    for sunday, row in weeks.iterrows():
        new_cycle = int(row["cycle_id"]) != cycle_id
        if new_cycle:  # a new cycle starts at this Sunday's close
            cycle_id = int(row["cycle_id"])
            base_btc = btc
            baseline = 0.0
            sold_in_cycle = 0.0

        target_btc = max(0.0, float(row["ratchet_sell"]) - baseline) * base_btc
        q_wanted = target_btc - sold_in_cycle
        if cmp_.floor_base == "initial" and q_wanted > EPS:
            allowed = min(q_wanted, max(0.0, btc - floor_btc))
            sold_in_cycle += q_wanted - allowed  # blocked by the floor: dropped, never deferred
            q_wanted = allowed
        sizing_base = cash if cmp_.buy_sizing == "cash" else reserve_usd
        usd_wanted = float(row["buy_pct"]) * sizing_base
        if new_cycle and cmp_.leftover_on_reset:
            usd_wanted = cash
        if q_wanted <= EPS and usd_wanted <= EPS:
            continue

        day = _exec_day(daily_price, sunday, bt.execution_lag_days, end_ts)
        base = {"week": sunday.date(), "cycle_id": cycle_id, "phase": row["phase"]}
        if day is None:
            if sunday + pd.Timedelta(days=bt.execution_lag_days) <= end_ts:
                side = "sell" if q_wanted > EPS else "buy"
                trades.append({**base, "exec_date": None, "side": side, "btc": 0.0, "usd": 0.0,
                               "price": float("nan"), "fee_usd": 0.0, "status": "skipped"})
            continue
        price = float(daily_price.loc[day])

        if q_wanted > EPS:
            q = min(q_wanted, btc)
            if q > EPS:
                d_btc, d_cash = -q, q * price * (1.0 - fee)
                _check_identity(d_cash, d_btc, price, -fee * q * price)
                btc += d_btc
                cash += d_cash
                sold_in_cycle += q
                trades.append({**base, "exec_date": day.date(), "side": "sell", "btc": q, "usd": d_cash,
                               "price": price, "fee_usd": fee * q * price, "status": "done"})
        if usd_wanted > EPS:
            usd = min(usd_wanted, cash)
            if usd > EPS:
                d_cash, d_btc = -usd, usd * (1.0 - fee) / price
                _check_identity(d_cash, d_btc, price, -fee * usd)
                btc += d_btc
                cash += d_cash
                trades.append({**base, "exec_date": day.date(), "side": "buy", "btc": d_btc, "usd": usd,
                               "price": price, "fee_usd": fee * usd, "status": "done"})
        changes.append((day, btc, cash))

    equity = _equity(daily_price, changes, start_ts, end_ts)
    cols = ["week", "exec_date", "side", "btc", "usd", "price", "fee_usd", "status", "cycle_id", "phase"]
    return Simulation(pd.DataFrame(trades, columns=cols), equity, reserve_usd, start_ts.date())


def _equity(daily_price: pd.Series, changes, start_ts, end_ts) -> pd.DataFrame:
    idx = daily_price.loc[start_ts:end_ts].index
    hold = pd.DataFrame(changes, columns=["date", "btc", "cash"]).groupby("date").last()
    hold = hold.reindex(idx.union(hold.index)).ffill().reindex(idx)
    hold["equity_usd"] = hold["btc"] * daily_price.loc[start_ts:end_ts] + hold["cash"]
    return hold


def resolve_start(result: ReplayResult, cfg: Config, start=None) -> pd.Timestamp:
    """``first_all_valid_week`` = first week with the six inputs PRESENT; a date = first Sunday >= date."""
    weeks = result.weeks
    value = cfg.backtest.start if start is None else start
    if value == "first_all_valid_week":
        states = weeks.filter(like="state_")
        ok = (states == "PRESENT").all(axis=1)
        if not ok.any():
            raise ValueError("no week with all six inputs present")
        return ok.idxmax()
    later = weeks.index[weeks.index >= pd.Timestamp(value)]
    if not len(later):
        raise ValueError(f"no week on or after {value}")
    return later[0]


def ratchet_at(result: ReplayResult, week: pd.Timestamp) -> float:
    return float(result.weeks.at[week, "ratchet_sell"])
