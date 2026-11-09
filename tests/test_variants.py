"""Phase 2: comparison options and catalog (design docs/designs/bitcoin_cycle_phase2_variants.md)."""

import numpy as np
import pandas as pd
import pytest

from bitsignal.backtest.minimal import replay_minimal
from bitsignal.backtest.portfolio import simulate
from bitsignal.backtest.variants import (
    POST_HOC,
    POST_HOC_NAMES,
    PRE_REGISTERED_NAMES,
    pre_registered,
)
from bitsignal.config import ConfigError, apply_overrides, load_config, load_frozen_params, model_hash, validate_for_panel
from bitsignal.engine.detector import detect

from engine_helpers import score_frame, weekly_detector_frame
from test_backtest import SUN, daily, result

CFG = load_config()


def with_cmp(**cmp):
    return apply_overrides(CFG, {"comparison": cmp})


# --- config ------------------------------------------------------------------------------


def test_comparison_block_enters_the_hash_only_when_not_default():
    v1 = load_config("config/config_v1.yaml")
    frozen = load_frozen_params(v1.backtest.frozen_params)
    assert model_hash(v1) == frozen.model_hash  # default comparison block: v1 hash unchanged
    changed = apply_overrides(v1, {"comparison": {"buy_sizing": "cash", "floor_base": "initial"}})
    assert model_hash(changed) != frozen.model_hash  # a comparison model has its own identity


@pytest.mark.parametrize("cmp", [
    {"model": "minimal"}, {"detector_enabled": False}, {"detector_arming": "score60"},
    {"leftover_on_reset": True}, {"buy_sizing": "cash"}, {"floor_base": "initial"},
    {"minimal": {"sell_step": 0.2}},
])
def test_dashboard_rejects_any_comparison_option(cmp):
    validate_for_panel(CFG)
    with pytest.raises(ConfigError) as exc:
        validate_for_panel(with_cmp(**cmp))
    assert exc.value.path.startswith("comparison.")


# --- catalog -----------------------------------------------------------------------------


def test_catalog_names_are_fixed_and_every_override_is_valid():
    cat = pre_registered(CFG)
    assert tuple(cat) == PRE_REGISTERED_NAMES
    assert tuple(POST_HOC) == POST_HOC_NAMES
    assert "norm_hybrid" not in cat and "reset_dd60" not in cat  # D3, D5
    for override in list(cat.values()) + list(POST_HOC.values()):
        apply_overrides(CFG, override)  # raises ConfigError if invalid


def test_threshold_shift_moves_every_score_threshold():
    plus = apply_overrides(CFG, pre_registered(CFG)["thr_plus5"])
    assert [t for t, _ in plus.sell_ladder] == [90.0, 95.0, 98.0]
    assert (plus.cycle.arm_score, plus.cycle.confirm_score) == (25.0, 35.0)
    assert [t for t, _ in plus.buys.tiers] == [15.0, 25.0]
    assert [p for _, p in plus.sell_ladder] == [p for _, p in CFG.sell_ladder]


def test_floor60_caps_the_detector_at_the_new_cap():
    f60 = apply_overrides(CFG, pre_registered(CFG)["floor60"])
    assert f60.cap.cap == pytest.approx(0.40)
    assert max(f60.detector.levels) == pytest.approx(0.40)


# --- detector ----------------------------------------------------------------------------


def _armed_episode_frame(n=12):
    f = weekly_detector_frame(n)
    a = f["new_ath"].to_numpy().copy()
    a[0] = True
    f["new_ath"] = a
    p = f["price"].to_numpy().copy()
    p[5:8] = 75.0  # below trend (90) and <= 80% of high52w for 2 weeks -> trigger at week 6
    f["price"] = p
    return f


def test_detector_disabled_never_opens_an_episode():
    f = _armed_episode_frame()
    assert detect(f, CFG)["level"].max() == 1
    off = detect(f, with_cmp(detector_enabled=False))
    assert off["level"].sum() == 0 and not off["armed"].any()


def test_score_arming_modes():
    f = weekly_detector_frame(40)
    idx = f.index
    smin = np.full(40, 30.0)
    smax = np.full(40, 30.0)
    smax[3] = 60.0  # one week with score_max >= 60
    smin[10] = 36.0  # one week with score_min > 35
    status = ["OK"] * 40
    status[20] = "UNAVAILABLE"
    smin[20] = smax[20] = 99.0  # unavailable: never arms
    s = score_frame(idx, smin, smax, status)

    a60 = detect(f, with_cmp(detector_arming="score60"), s)["armed"].to_numpy()
    assert not a60[:3].any() and a60[3:29].all() and not a60[29:].any()  # 26 weeks from week 3

    a35 = detect(f, with_cmp(detector_arming="score35"), s)["armed"].to_numpy()
    assert a35.tolist() == [i == 10 for i in range(40)]

    with pytest.raises(ValueError):
        detect(f, with_cmp(detector_arming="score35"))  # needs the score


# --- portfolio ---------------------------------------------------------------------------


def test_buy_sizing_cash_uses_current_cash():
    price = daily([100.0] * 40)
    rows = [{}, {"buy_pct": 0.5}, {"buy_pct": 0.5}]
    cfg = apply_overrides(CFG, {"backtest": {"reserve_btc_equiv": 1.0}, "comparison": {"buy_sizing": "cash"}})
    buys = simulate(result(rows), price, cfg, SUN.date(), 0.0).trades
    assert buys["usd"].tolist() == pytest.approx([50.0, 25.0])  # 50% of 100, then 50% of 50
    base = simulate(result(rows), price, apply_overrides(cfg, {"comparison": {"buy_sizing": "reserve"}}),
                    SUN.date(), 0.0).trades
    assert base["usd"].tolist() == pytest.approx([50.0, 50.0])


def test_leftover_on_reset_buys_all_cash_at_the_new_cycle():
    price = daily([100.0] * 40)
    rows = [{}, {"ratchet_sell": 0.5}, {"ratchet_sell": 0.5}, {"cycle_id": 1}]
    cfg = apply_overrides(CFG, {"backtest": {"reserve_btc_equiv": 0.0}, "comparison": {"leftover_on_reset": True}})
    sim = simulate(result(rows), price, cfg, SUN.date(), 0.0)
    buys = sim.trades[sim.trades["side"] == "buy"]
    assert len(buys) == 1 and buys.iloc[0]["week"] == (SUN + pd.Timedelta(days=21)).date()
    assert sim.equity["cash"].iloc[-1] == pytest.approx(0.0)


def test_floor_initial_never_sells_below_the_initial_floor():
    price = daily([100.0] * 60)
    # cycle 0 sells 50%; cycle 1 (base 0.5 BTC) wants 50% more -> blocked at 0.5 BTC = floor x 1 BTC
    rows = [{}, {"ratchet_sell": 0.5}, {"cycle_id": 1}, {"cycle_id": 1, "ratchet_sell": 0.5}]
    cfg = apply_overrides(CFG, {"backtest": {"reserve_btc_equiv": 0.0}})
    per_cycle = simulate(result(rows), price, cfg, SUN.date(), 0.0)
    assert per_cycle.equity["btc"].iloc[-1] == pytest.approx(0.25)
    initial = simulate(result(rows), price, apply_overrides(cfg, {"comparison": {"floor_base": "initial"}}),
                       SUN.date(), 0.0)
    assert initial.equity["btc"].iloc[-1] == pytest.approx(0.5)

    # The blocked part is dropped: later buys in the same cycle are not sold back.
    rows2 = rows + [{"cycle_id": 1, "ratchet_sell": 0.5, "buy_pct": 0.1}] * 3
    cfg2 = apply_overrides(CFG, {"backtest": {"reserve_btc_equiv": 1.0}, "comparison": {"floor_base": "initial"}})
    tr = simulate(result(rows2), price, cfg2, SUN.date(), 0.0).trades
    assert (tr["side"] == "sell").sum() == 1  # only the cycle-0 sale
    assert (tr["side"] == "buy").sum() == 3


# --- minimal -----------------------------------------------------------------------------


def _minimal_frame(prices, sma, ratio=None, spread=None):
    n = len(prices)
    idx = pd.date_range(SUN, periods=n, freq="7D")
    price = pd.Series(prices, index=idx, dtype="float64")
    return pd.DataFrame({
        "price": price,
        "sma200w": pd.Series(sma, index=idx, dtype="float64"),
        "price_to_sma200w": pd.Series(ratio if ratio is not None else [1.0] * n, index=idx, dtype="float64"),
        "picycle_spread": pd.Series(spread if spread is not None else [0.5] * n, index=idx, dtype="float64"),
        "ath": price.cummax(),
    })


def test_minimal_sales_once_per_trigger_and_capped():
    w = _minimal_frame([100.0] * 6, [50.0] * 6, ratio=[1, 3.6, 3.7, 1, 3.6, 1], spread=[0.5, 0.5, 1.1, 1.2, 0.5, 0.5])
    weeks, events = replay_minimal(w, CFG)
    assert weeks["ratchet_sell"].tolist() == pytest.approx([0, 0.15, 0.30, 0.30, 0.30, 0.30])
    assert weeks["phase"].tolist()[:4] == ["HOLD", "DISTRIBUTE", "DISTRIBUTE", "DISTRIBUTE"]
    assert sum(e.type.value == "SELL_STEP" for e in events) == 2


def test_minimal_cycle_and_buys_in_accumulate():
    # ATH 100; weeks 2-6 below the SMA (ACCUMULATE): first week 40%, dd >= 50% 30%, dd >= 70% 30%
    prices = [100.0, 90.0, 60.0, 45.0, 40.0, 25.0, 80.0, 60.0]
    sma = [70.0] * 8
    weeks, events = replay_minimal(_minimal_frame(prices, sma), CFG)
    assert weeks["buy_pct"].tolist() == pytest.approx([0, 0, 0.40, 0.30, 0, 0.30, 0, 0.40])
    assert weeks["cycle_id"].tolist() == [0, 0, 1, 1, 1, 1, 1, 2]  # new cycle at each ACCUMULATE entry
    assert weeks["reset_pending"].tolist() == [p < 70.0 for p in prices]
    assert [e.date for e in events if e.type.value == "CYCLE_START"] == [weeks.index[2].date(), weeks.index[7].date()]

    uni = replay_minimal(_minimal_frame(prices, sma), apply_overrides(CFG, {"buys": {"mode": "uniform"}}))[0]
    acc = uni["reset_pending"]
    assert np.allclose(uni.loc[acc, "buy_pct"], 1 / CFG.buys.uniform_weeks)
    assert (uni.loc[~acc, "buy_pct"] == 0).all()


def test_minimal_waits_for_the_sma200w():
    w = _minimal_frame([10.0, 5.0], [np.nan, np.nan])
    weeks, _ = replay_minimal(w, CFG)
    assert weeks["phase"].tolist() == ["HOLD", "HOLD"] and weeks["buy_pct"].sum() == 0


# --- engine and CLI ----------------------------------------------------------------------


def test_default_row_matches_the_official_backtest():
    from bitsignal.backtest.engine import run_backtest, run_variants
    from bitsignal.data.history import load_frozen_history

    h = load_frozen_history(CFG.data.csv_path)
    res = run_variants(h, CFG, "calibration")
    rep = run_backtest(h, CFG, "calibration", sensitivities=False)
    assert res["default"]["default"]["strategy"] == rep.diagnostics["summary"]["strategy"]
    assert set(res["pre_registered"]) == set(PRE_REGISTERED_NAMES)
    assert set(res["post_hoc"]) == set(POST_HOC_NAMES)
    with pytest.raises(ValueError):
        run_variants(h, CFG, "development", frozen=None)


def test_cli_refuses_record_with_variants(capsys):
    import argparse

    from bitsignal import cli

    args = argparse.Namespace(window="development", no_sensitivities=True, record=True, variants=True)
    with pytest.raises(SystemExit) as exc:
        cli.cmd_backtest(args)
    assert exc.value.code == 1
    assert "variantes nunca são gravadas" in capsys.readouterr().out
