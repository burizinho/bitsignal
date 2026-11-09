"""Backtest metrics and diagnostics (design §7, plan item 30).

Diagnostics never decide approval; only ``criteria`` does (Q1). Operations without enough
forward data (180/365 days) are excluded from the diagnostics and counted in ``excluded``.
"""

from __future__ import annotations

from datetime import date
from typing import Dict, List

import pandas as pd

from bitsignal.config import Config, EventConfig
from bitsignal.models import Event, EventType


def max_drawdown(equity: pd.Series) -> float:
    """Maximum drawdown in percentage points (positive number) of a daily equity curve."""
    s = equity.dropna()
    if s.empty:
        return float("nan")
    return float(((s.cummax() - s) / s.cummax()).max() * 100.0)


def rebase(equity: pd.Series, d) -> pd.Series:
    """Only the rows with date >= d, divided by the first of them and multiplied by 100."""
    s = equity.loc[pd.Timestamp(d):].dropna()
    return s / s.iloc[0] * 100.0


def criteria(strategy: pd.Series, bnh: pd.Series, uniform: pd.Series, cfg: Config) -> Dict[str, Dict]:
    """The three cumulative Q1 criteria on curves rebased at ``approval_window_start``."""
    d = cfg.backtest.approval_window_start
    s, b, u = rebase(strategy, d), rebase(bnh, d), rebase(uniform, d)
    values = {
        "equity_vs_bnh": float(s.iloc[-1] / b.iloc[-1]),
        "dd_improvement_pp": float(max_drawdown(b) - max_drawdown(s)),
        "equity_vs_uniform": float(s.iloc[-1] / u.iloc[-1]),
    }
    c = cfg.backtest.criteria
    passed = {
        "equity_vs_bnh": values["equity_vs_bnh"] >= c.equity_vs_bnh,
        "dd_improvement_pp": values["dd_improvement_pp"] >= c.dd_improvement_pp,
        "equity_vs_uniform": values["equity_vs_uniform"] >= c.equity_vs_uniform,
    }
    return {"passed": passed, "values": values}


def _done(trades: pd.DataFrame, side: str) -> pd.DataFrame:
    if trades.empty:
        return trades
    return trades[(trades["status"] == "done") & (trades["side"] == side)]


def _forward(daily_price: pd.Series, d, days: int):
    """Prices in (d, d + days]; None when the window goes past the data."""
    start = pd.Timestamp(d)
    stop = start + pd.Timedelta(days=days)
    if stop > daily_price.dropna().index[-1]:
        return None
    return daily_price.loc[start + pd.Timedelta(days=1): stop].dropna()


def premature_sales(trades: pd.DataFrame, daily_price: pd.Series) -> Dict[str, float]:
    """% of BTC sold at a price <= 2/3 of the maximum of the next 365 days."""
    total = prem = 0.0
    excluded = 0
    for _, t in _done(trades, "sell").iterrows():
        fwd = _forward(daily_price, t["exec_date"], 365)
        if fwd is None:
            excluded += 1
            continue
        total += t["btc"]
        if t["price"] <= (2.0 / 3.0) * fwd.max():
            prem += t["btc"]
    return {"pct_btc_premature": (prem / total * 100.0) if total else 0.0, "excluded": excluded}


def false_sells(trades: pd.DataFrame, daily_price: pd.Series) -> Dict[str, float]:
    """Unit = sell operation. False if the minimum of the next 180 days stays above 70% of the
    execution price. Cost in BTC = BTC sold × (1 − exec price / max of the next 365 days)."""
    count = 0
    cost = 0.0
    excluded = 0
    for _, t in _done(trades, "sell").iterrows():
        f180 = _forward(daily_price, t["exec_date"], 180)
        f365 = _forward(daily_price, t["exec_date"], 365)
        if f180 is None or f365 is None:
            excluded += 1
            continue
        if f180.min() > 0.70 * t["price"]:
            count += 1
            cost += t["btc"] * max(0.0, 1.0 - t["price"] / f365.max())
    return {"count": count, "cost_btc": cost, "excluded": excluded}


def false_resets(events: List[Event], end=None) -> int:
    """CYCLE_START less than 52 weeks after the previous CYCLE_START."""
    starts = [e.date for e in events if e.type == EventType.CYCLE_START and (end is None or e.date <= end)]
    return sum(1 for a, b in zip(starts, starts[1:]) if (b - a).days < 52 * 7)


def per_cycle(trades: pd.DataFrame, weeks: pd.DataFrame, daily_price: pd.Series) -> pd.DataFrame:
    """Per cycle: weighted sell price as % of the cycle peak and weighted buy price as a multiple
    of the trough of the ACCUMULATE phase that ends the cycle."""
    rows = []
    last_day = daily_price.dropna().index[-1]
    for cid, w in weeks.groupby("cycle_id"):
        c_start, c_end = w.index[0], w.index[-1] + pd.Timedelta(days=6)
        c_end = min(c_end, last_day)
        peak = daily_price.loc[c_start:c_end].max()
        acc = w[w["reset_pending"]]
        trough = daily_price.loc[acc.index[0]:c_end].min() if len(acc) else float("nan")
        sells = _done(trades, "sell")
        sells = sells[sells["cycle_id"] == cid] if len(sells) else sells
        buys = _done(trades, "buy")
        buys = buys[buys["cycle_id"] == cid] if len(buys) else buys
        sell_px = (sells["price"] * sells["btc"]).sum() / sells["btc"].sum() if len(sells) else float("nan")
        buy_px = buys["usd"].sum() / (buys["usd"] / buys["price"]).sum() if len(buys) else float("nan")
        rows.append(
            {
                "cycle_id": int(cid),
                "start": c_start.date(),
                "sell_avg_pct_of_peak": sell_px / peak * 100.0 if len(sells) else float("nan"),
                "buy_avg_multiple_of_trough": buy_px / trough if len(buys) else float("nan"),
            }
        )
    return pd.DataFrame(rows)


def event_diagnostics(trades: pd.DataFrame, daily_price: pd.Series, events_cfg: List[EventConfig],
                      sim_equity: pd.DataFrame, reserve_usd: float) -> pd.DataFrame:
    """Per configured event window: % sold (tops) or % of the reserve bought (bottoms), weighted
    price and opportunity cost."""
    rows = []
    for ev in events_cfg:
        a, b = pd.Timestamp(ev.window[0]), pd.Timestamp(ev.window[1])
        if b < sim_equity.index[0] or a > sim_equity.index[-1]:
            rows.append({"event": ev.name, "kind": ev.kind, "evaluable": False})
            continue
        side = "sell" if ev.kind == "top" else "buy"
        t = _done(trades, side)
        if len(t):
            t = t[(pd.to_datetime(t["exec_date"]) >= a) & (pd.to_datetime(t["exec_date"]) <= b)]
        window_px = daily_price.loc[a:b]
        row = {"event": ev.name, "kind": ev.kind, "evaluable": True}
        if ev.kind == "top":
            held = sim_equity["btc"].loc[a:].iloc[0] if len(sim_equity.loc[a:]) else float("nan")
            sold = t["btc"].sum() if len(t) else 0.0
            row["pct"] = sold / held * 100.0 if held else 0.0
            row["avg_price"] = (t["price"] * t["btc"]).sum() / sold if sold else float("nan")
            row["opportunity_cost_usd"] = float(((window_px.max() - t["price"]) * t["btc"]).sum()) if sold else 0.0
        else:
            spent = t["usd"].sum() if len(t) else 0.0
            bought = (t["usd"] / t["price"]).sum() if len(t) else 0.0
            row["pct"] = spent / reserve_usd * 100.0 if reserve_usd else 0.0
            row["avg_price"] = spent / bought if bought else float("nan")
            row["opportunity_cost_usd"] = float(((t["price"] - window_px.min()) * (t["usd"] / t["price"])).sum()) if len(t) else 0.0
        rows.append(row)
    return pd.DataFrame(rows)


def reserve_usage(trades: pd.DataFrame, weeks: pd.DataFrame, reserve_usd: float, final_cash: float) -> pd.DataFrame:
    """% of the reserve spent in each contiguous ACCUMULATE phase, plus the final cash."""
    acc = weeks["reset_pending"].astype(bool)
    block = (acc != acc.shift()).cumsum()[acc]
    buys = _done(trades, "buy")
    rows = []
    for _, w in weeks[acc].groupby(block):
        a, b = w.index[0], w.index[-1]
        spent = buys[(pd.to_datetime(buys["week"]) >= a) & (pd.to_datetime(buys["week"]) <= b)]["usd"].sum() if len(buys) else 0.0
        rows.append({"phase_start": a.date(), "phase_end": b.date(),
                     "pct_reserve_spent": spent / reserve_usd * 100.0 if reserve_usd else 0.0})
    df = pd.DataFrame(rows, columns=["phase_start", "phase_end", "pct_reserve_spent"])
    df.attrs["final_cash_usd"] = final_cash
    return df


def window_end(cfg: Config, window: str, last: date) -> date:
    return cfg.backtest.calibration_end if window == "calibration" else last
