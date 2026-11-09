"""S5: portfolio simulation, benchmarks and metrics (synthetic series + frozen CSV)."""

from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import pytest

from bitsignal.backtest import metrics as m
from bitsignal.backtest.benchmarks import buy_and_hold, uniform_complete
from bitsignal.backtest.engine import run_backtest
from bitsignal.backtest.portfolio import _check_identity, ratchet_at, resolve_start, simulate
from bitsignal.config import FrozenParams, apply_overrides, load_config, model_hash, model_payload
from bitsignal.data.history import load_frozen_history
from bitsignal.engine.pipeline import run_model
from bitsignal.models import Event, EventType, ReplayResult

CFG = load_config()
SUN = pd.Timestamp("2020-01-05")  # Sunday


def daily(prices, start=SUN):
    return pd.Series(prices, index=pd.date_range(start, periods=len(prices), freq="D"), dtype="float64")


def result(rows):
    """rows: list of dicts with ratchet_sell, buy_pct, cycle_id (one per week from SUN)."""
    idx = pd.date_range(SUN, periods=len(rows), freq="7D")
    df = pd.DataFrame(rows, index=idx)
    for col, default in (("ratchet_sell", 0.0), ("buy_pct", 0.0), ("cycle_id", 0), ("phase", "HOLD"),
                         ("reset_pending", False)):
        df[col] = df[col].fillna(default) if col in df else default
    return ReplayResult(weeks=df, events=[], as_of=idx[-1].date(), model_hash="x")


def cfg_with(**backtest):
    return apply_overrides(CFG, {"backtest": backtest})


def test_identity_examples_from_the_design():
    fee = 0.003
    _check_identity(-1000.0, 1000.0 * (1 - fee) / 50.0, 50.0, -fee * 1000.0)  # buy: −3,00
    _check_identity(0.1 * 50000 * (1 - fee), -0.1, 50000.0, -fee * 0.1 * 50000)  # sell: −15,00
    with pytest.raises(AssertionError):
        _check_identity(-1000.0, 1000.0 / 50.0, 50.0, -fee * 1000.0)  # no fee charged -> wrong


def test_sell_with_fee_on_monday_after_signal():
    price = daily([100.0] * 30)
    cfg = cfg_with(reserve_btc_equiv=0.0)
    sim = simulate(result([{}, {"ratchet_sell": 0.10}, {"ratchet_sell": 0.10}]), price, cfg, SUN.date(), 0.0)
    sells = sim.trades[sim.trades["side"] == "sell"]
    assert len(sells) == 1  # ratchet stays at 10%: one sale only
    assert sells.iloc[0]["exec_date"] == (SUN + pd.Timedelta(days=8)).date()  # Sunday wk1 + 1 day
    assert sells.iloc[0]["btc"] == pytest.approx(0.10)
    assert sim.equity["cash"].iloc[-1] == pytest.approx(0.10 * 100 * (1 - cfg.backtest.fee))


def test_execution_fallback_and_skip():
    prices = [100.0] * 40
    prices[8] = np.nan  # Monday after week 1 -> executes Tuesday
    price = daily(prices)
    sim = simulate(result([{}, {"ratchet_sell": 0.10}]), price, cfg_with(reserve_btc_equiv=0.0), SUN.date(), 0.0)
    assert sim.trades.iloc[0]["exec_date"] == (SUN + pd.Timedelta(days=9)).date()

    prices2 = [100.0] * 40
    for i in range(8, 16):
        prices2[i] = np.nan  # no price for 8 days after the Sunday -> skipped
    sim2 = simulate(result([{}, {"ratchet_sell": 0.10}]), daily(prices2), cfg_with(reserve_btc_equiv=0.0), SUN.date(), 0.0)
    assert sim2.trades.iloc[0]["status"] == "skipped"
    assert sim2.equity["btc"].iloc[-1] == 1.0


def test_buy_limited_to_cash_and_reserve_not_renewed_by_new_cycle():
    price = daily([100.0] * 40)
    cfg = cfg_with(reserve_btc_equiv=0.5)
    rows = [{}, {"buy_pct": 0.7, "phase": "ACCUMULATE"}, {"buy_pct": 0.7, "phase": "ACCUMULATE"},
            {"cycle_id": 1}, {"cycle_id": 1, "buy_pct": 0.7, "phase": "ACCUMULATE"}]
    sim = simulate(result(rows), price, cfg, SUN.date(), 0.0)
    buys = sim.trades[sim.trades["side"] == "buy"]
    assert buys["usd"].sum() == pytest.approx(sim.reserve_usd)  # 70% + 30% (limited), then nothing
    assert len(buys) == 2
    cash = sim.equity["cash"]
    trade_days = set(pd.to_datetime(sim.trades["exec_date"]))
    increases = cash.diff().fillna(0) > 1e-9
    assert all(d in trade_days for d in cash.index[increases])  # cash only moves on trade days


def test_conservation_over_many_trades():
    rng = np.random.default_rng(7)
    price = daily(100 * np.exp(np.cumsum(rng.normal(0, 0.02, 400))))
    rows = []
    ratchet, cid = 0.0, 0
    for i in range(55):
        if i in (20, 40):
            cid += 1
            ratchet = 0.0
        ratchet = max(ratchet, [0, 0.05, 0.15, 0.3, 0.5][rng.integers(0, 5)])
        rows.append({"ratchet_sell": ratchet, "cycle_id": cid, "buy_pct": 0.02 if i % 3 == 0 else 0.0})
    sim = simulate(result(rows), price, CFG, SUN.date(), 0.0)
    t = sim.trades[sim.trades["status"] == "done"]
    buys, sells = t[t["side"] == "buy"], t[t["side"] == "sell"]
    assert sim.equity["cash"].iloc[-1] == pytest.approx(sim.reserve_usd - buys["usd"].sum() + sells["usd"].sum())
    assert sim.equity["btc"].iloc[-1] == pytest.approx(1.0 + buys["btc"].sum() - sells["btc"].sum())
    assert buys["usd"].sum() <= sim.reserve_usd + sells["usd"].sum() + 1e-9


def test_ratchet_at_start_prevents_retroactive_sales():
    price = daily([100.0] * 40)
    rows = [{"ratchet_sell": 0.30}, {"ratchet_sell": 0.30}, {"ratchet_sell": 0.50}]
    sim = simulate(result(rows), price, cfg_with(reserve_btc_equiv=0.0), SUN.date(), ratchet_at_start=0.30)
    sells = sim.trades[sim.trades["side"] == "sell"]
    assert len(sells) == 1 and sells.iloc[0]["btc"] == pytest.approx(0.20)  # only the increment


def test_buy_and_hold_uses_all_capital():
    price = daily([100.0] * 20)
    sim = buy_and_hold(price, CFG, SUN.date())
    assert sim.equity["cash"].iloc[-1] == 0.0
    assert sim.equity["btc"].iloc[-1] == pytest.approx(1.0 + 0.5 * 100 * (1 - CFG.backtest.fee) / 100)


def test_drawdown_rebase_and_criteria_by_hand():
    idx = pd.date_range("2018-12-30", periods=5, freq="D")
    strat = pd.Series([100, 100, 150, 120, 140.0], index=idx)  # dd 20%
    bnh = pd.Series([100, 100, 200, 100, 150.0], index=idx)  # dd 50%
    uni = pd.Series([100, 100, 150, 120, 130.0], index=idx)
    assert m.max_drawdown(bnh) == pytest.approx(50.0)
    rb = m.rebase(strat, "2018-12-31")
    assert rb.index[0] == pd.Timestamp("2018-12-31") and rb.iloc[0] == 100.0
    cfg = apply_overrides(CFG, {"backtest": {"approval_window_start": date(2018, 12, 31), "calibration_end": date(2018, 12, 30)}})
    c = m.criteria(strat, bnh, uni, cfg)
    assert c["values"]["equity_vs_bnh"] == pytest.approx(140 / 150)
    assert c["values"]["dd_improvement_pp"] == pytest.approx(30.0)
    assert c["values"]["equity_vs_uniform"] == pytest.approx(140 / 130)
    assert c["passed"] == {"equity_vs_bnh": True, "dd_improvement_pp": True, "equity_vs_uniform": True}


def _trades(rows):
    return pd.DataFrame(rows).assign(status="done")


def test_diagnostics_by_hand():
    price = daily([100.0] * 10 + [200.0] * 500)
    sell = _trades([{"exec_date": SUN.date(), "side": "sell", "btc": 1.0, "price": 100.0, "usd": 100.0}])
    assert m.premature_sales(sell, price)["pct_btc_premature"] == 100.0  # 100 <= 2/3 * 200
    fs = m.false_sells(sell, price)
    assert fs["count"] == 1 and fs["cost_btc"] == pytest.approx(0.5)  # 1 * (1 - 100/200)
    late = _trades([{"exec_date": (SUN + pd.Timedelta(days=400)).date(), "side": "sell", "btc": 1.0,
                     "price": 200.0, "usd": 200.0}])
    assert m.false_sells(late, price)["excluded"] == 1  # less than 365 days ahead
    evs = [Event(date(2020, 1, 5), EventType.CYCLE_START, "score"),
           Event(date(2020, 6, 1), EventType.CYCLE_START, "score"),
           Event(date(2022, 1, 1), EventType.CYCLE_START, "score")]
    assert m.false_resets(evs) == 1


@pytest.fixture(scope="module")
def real():
    h = load_frozen_history(CFG.data.csv_path)
    return h, run_model(h, CFG)


def test_uniform_buys_one_52nd_every_accumulate_week(real):
    h, r = real
    start = resolve_start(r, CFG)
    sim = uniform_complete(h, CFG, start.date(), ratchet_at(r, start), CFG.backtest.calibration_end)
    buys = sim.trades[(sim.trades["side"] == "buy") & (sim.trades["status"] == "done")]
    assert len(buys) > 10
    full = buys[buys["usd"] < sim.reserve_usd / 52 + 1e-9]
    assert full["usd"].iloc[0] == pytest.approx(sim.reserve_usd / 52)


def test_development_window_requires_matching_frozen_params(real):
    h, _ = real
    with pytest.raises(ValueError):
        run_backtest(h, CFG, window="development", frozen=None, sensitivities=False)
    wrong = FrozenParams(frozen_at=datetime.now(timezone.utc), csv_sha256="x", model_hash="0" * 64,
                         model=model_payload(CFG))
    with pytest.raises(ValueError):
        run_backtest(h, CFG, window="development", frozen=wrong, sensitivities=False)
    ok = wrong.model_copy(update={"model_hash": model_hash(CFG)})
    rep = run_backtest(h, CFG, window="development", frozen=ok, sensitivities=False)
    assert rep.criteria is not None and set(rep.criteria["passed"]) == {"equity_vs_bnh", "dd_improvement_pp", "equity_vs_uniform"}


def test_calibration_has_no_criteria_and_late_entry_not_applicable(real):
    h, _ = real
    rep = run_backtest(h, CFG, window="calibration")
    assert rep.criteria is None
    assert rep.start == date(2014, 5, 11)
    assert rep.end == CFG.backtest.calibration_end
    assert rep.sensitivities["late_entry_2019"]["applicable"] is False
    assert rep.strategy.equity.index[-1] <= pd.Timestamp(CFG.backtest.calibration_end)
