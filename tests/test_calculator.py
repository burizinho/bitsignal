"""Dashboard calculator: verdict percentages -> amounts (nothing is stored)."""

from datetime import date

import pytest

from bitsignal.models import DataStatus, Phase, Verdict
from bitsignal.ui.calculator import compute


def verdict(**kw):
    base = dict(week=date(2026, 11, 8), data_status=DataStatus.OK, phase=Phase.DISTRIBUTE,
                sell_target=0.25, cycle_start_date=date(2023, 11, 12), buy_pct=None, reason="x")
    base.update(kw)
    return Verdict(**base)


def test_nothing_informed_gives_nothing():
    a = compute(verdict(), price=50_000.0)
    assert a.sell_target_btc is None and a.buy_usd is None


def test_sell_target_and_remaining():
    a = compute(verdict(sell_target=0.25), price=50_000.0, base_btc=2.0, sold_btc=0.1)
    assert a.sell_target_btc == pytest.approx(0.5)
    assert a.to_sell_btc == pytest.approx(0.4)
    assert a.to_sell_usd == pytest.approx(20_000.0)
    done = compute(verdict(sell_target=0.25), price=50_000.0, base_btc=2.0, sold_btc=0.7)
    assert done.to_sell_btc == 0.0  # already sold more than the target: nothing left


def test_weekly_buy_on_the_reserve_limited_by_cash():
    v = verdict(phase=Phase.ACCUMULATE, buy_pct=0.04)
    a = compute(v, price=50_000.0, reserve_usd=10_000.0)
    assert a.buy_usd == pytest.approx(400.0) and a.buy_btc == pytest.approx(0.008)
    limited = compute(v, price=50_000.0, reserve_usd=10_000.0, cash_usd=250.0)
    assert limited.buy_usd == pytest.approx(250.0) and limited.buy_limited_by_cash


def test_new_cycle_buys_all_cash():
    v = verdict(phase=Phase.HOLD, sell_target=0.0, buy_all_cash=True)
    a = compute(v, price=50_000.0, reserve_usd=10_000.0, cash_usd=30_000.0)
    assert a.buy_usd == pytest.approx(30_000.0) and a.buy_btc == pytest.approx(0.6)
    assert compute(v, price=50_000.0).buy_usd is None  # cash not informed


def test_no_buy_outside_accumulate():
    assert compute(verdict(buy_pct=None), price=50_000.0, reserve_usd=10_000.0).buy_usd is None
