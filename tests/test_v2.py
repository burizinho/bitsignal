"""Phase 3: model v2 (buy all cash at a new cycle) next to the frozen v1, and the forward evaluation."""

import argparse
from datetime import date, datetime, timezone
from unittest import mock

import pandas as pd
import pytest

from bitsignal import cli
from bitsignal.backtest.engine import _run_core
from bitsignal.backtest.forward import forward_eval, window_end
from bitsignal.config import apply_overrides, load_config, load_frozen_params, model_hash, model_payload
from bitsignal.data.history import load_frozen_history
from bitsignal.engine.cycle import latest_verdict
from bitsignal.engine.pipeline import run_model
from bitsignal.models import DataStatus, Event, EventType, Phase, Verdict
from bitsignal.ui.app import top_line
from bitsignal.verdict_log import append_verdict, verdict_row

V1 = load_config("config/config_v1.yaml")
V2 = load_config()
HISTORY = load_frozen_history(V2.data.csv_path)


# --- config and hash ---------------------------------------------------------------------


def test_v1_hash_is_still_the_frozen_one():
    assert model_hash(V1) == load_frozen_params(V1.backtest.frozen_params).model_hash
    assert "on_reset" not in model_payload(V1)["buys"]


def test_v2_differs_from_v1_only_in_the_reset_buy():
    assert V2.buys.on_reset == "all_cash" and V1.buys.on_reset == "none"
    p1, p2 = model_payload(V1), model_payload(V2)
    assert p2["buys"].pop("on_reset") == "all_cash"
    assert p1 == p2
    assert model_hash(V2) != model_hash(V1)
    assert V2.data.verdict_log_path != V1.data.verdict_log_path


# --- replay, simulation, verdict ---------------------------------------------------------


def test_buy_all_cash_only_on_new_cycle_weeks_and_only_in_v2():
    r2, r1 = run_model(HISTORY, V2), run_model(HISTORY, V1)
    starts = {pd.Timestamp(e.date) for e in r2.events if e.type == EventType.CYCLE_START}
    flagged = set(r2.weeks.index[r2.weeks["buy_all_cash"]])
    assert flagged == starts and len(starts) >= 5
    assert not r1.weeks["buy_all_cash"].any()
    pd.testing.assert_series_equal(r2.weeks["ratchet_sell"], r1.weeks["ratchet_sell"])  # same sales


def test_v2_portfolio_equals_the_phase2_leftover_buy_variant():
    v2 = _run_core(HISTORY, V2, "development")[3]
    leftover = _run_core(HISTORY, apply_overrides(V1, {"comparison": {"leftover_on_reset": True}}), "development")[3]
    pd.testing.assert_frame_equal(v2.equity, leftover.equity)
    v1 = _run_core(HISTORY, V1, "development")[3]
    assert v2.equity["equity_usd"].iloc[-1] > v1.equity["equity_usd"].iloc[-1]


def test_verdict_on_a_new_cycle_week():
    h = HISTORY.truncate("2023-11-12")  # v1/v2 CYCLE_START
    now = datetime(2023, 11, 13, 12, tzinfo=timezone.utc)
    r2 = run_model(h, V2)
    v2 = latest_verdict(r2, now, V2)
    assert v2.buy_all_cash and "todo o caixa disponível" in v2.reason
    assert not latest_verdict(run_model(h, V1), now, V1).buy_all_cash
    assert verdict_row(r2, v2, now)["buy_pct"] == "all_cash"
    assert "todo o caixa disponível" in top_line(v2, V2)


def test_top_line_regular_week_keeps_the_reserve_percentage():
    v = Verdict(week=date(2026, 11, 8), data_status=DataStatus.OK, phase=Phase.ACCUMULATE, sell_target=0.25,
                cycle_start_date=date(2023, 11, 12), buy_pct=0.02, reason="x")
    assert "**2%** da reserva-base" in top_line(v, V2)


# --- CLI guards --------------------------------------------------------------------------


def test_record_is_refused_for_v2():
    frozen = mock.Mock(approval=None, model_hash=model_hash(V2))
    args = argparse.Namespace(window="development")
    assert "modelo v2" in cli._record_refusal(args, V2, frozen)


def test_one_log_file_never_mixes_models(tmp_path, capsys):
    out = tmp_path / "log.csv"
    now = datetime(2026, 11, 2, 12, tzinfo=timezone.utc)
    r1 = run_model(HISTORY.truncate("2026-11-01"), V1)
    append_verdict(out, verdict_row(r1, latest_verdict(r1, now, V1), now))
    with mock.patch("bitsignal.data.coinmetrics.fetch_coinmetrics", return_value=HISTORY.daily), \
            mock.patch.object(cli, "_now_utc", return_value=datetime(2026, 11, 9, 12, tzinfo=timezone.utc)), \
            pytest.raises(SystemExit) as exc:
        cli.cmd_record_verdict(argparse.Namespace(out=str(out), config=None))  # v2 into a v1 file
    assert exc.value.code == 1
    assert "outro modelo" in capsys.readouterr().out
    assert out.read_text(encoding="utf-8").count("\n") == 2  # header + the v1 row only


# --- forward evaluation ------------------------------------------------------------------


def _weeks(phases):
    idx = pd.date_range("2027-01-03", periods=len(phases), freq="7D")
    return pd.DataFrame({"phase": phases}, index=idx)


def test_window_closes_only_at_a_new_cycle_after_distribute():
    w = _weeks(["ACCUMULATE", "HOLD", "HOLD", "DISTRIBUTE", "HOLD", "ACCUMULATE", "HOLD", "HOLD"])
    start = w.index[0]
    early = Event(w.index[2].date(), EventType.CYCLE_START, "score")  # no DISTRIBUTE before it
    late = Event(w.index[6].date(), EventType.CYCLE_START, "score")
    assert window_end(w, [early], start) is None
    assert window_end(w, [early, late], start) == w.index[6].date()
    assert window_end(w, [early, late], start, deadline=date(2027, 1, 20)) == date(2027, 1, 20)
    assert window_end(w, [], start, deadline=date(2027, 2, 1)) == date(2027, 2, 1)  # deadline passed


def test_forward_eval_offline():
    res = forward_eval(HISTORY, V2, V1, date(2024, 1, 1), deadline=date(2025, 6, 30))
    assert res["status"] == "closed" and res["end"] == date(2025, 6, 30)
    # no new cycle inside this window: v2 and v1 make the same trades
    assert res["criteria"]["values"]["v2_vs_v1"] == pytest.approx(1.0)
    assert set(res["criteria"]["passed"]) == {"equity_vs_bnh", "dd_improvement_pp", "equity_vs_uniform", "v2_vs_v1"}

    assert forward_eval(HISTORY, V2, V1, date(2026, 12, 1))["status"] == "no_weeks"
    open_ = forward_eval(HISTORY, V2, V1, date(2026, 6, 1))
    assert open_["status"] == "open" and open_["end"] == date(2026, 11, 8)


# --- pre-registered minimal arm (Phase 3 addendum) ---------------------------------------

MIN = load_config("config/config_minimal.yaml")


def test_minimal_arm_has_its_own_identity_and_log():
    assert MIN.comparison.model == "minimal"
    assert len({model_hash(V1), model_hash(V2), model_hash(MIN)}) == 3
    assert MIN.data.verdict_log_path == "data/verdicts/weekly_verdicts_minimal.csv"
    assert MIN.backtest.frozen_params is None


def test_minimal_weekly_verdict_and_row():
    now = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
    r = run_model(HISTORY, MIN)
    v = latest_verdict(r, now, MIN)
    assert v.phase is not None and v.reason.startswith("minimal:")
    row = verdict_row(r, v, now)
    assert row["score"] == "" and row["score_status"] == ""  # the minimal model has no score
    assert row["model_hash"] == model_hash(MIN)


def test_forward_eval_reports_minimal_without_making_it_a_criterion():
    res = forward_eval(HISTORY, V2, V1, date(2024, 1, 1), deadline=date(2025, 6, 30), cfg_min=MIN)
    assert set(res["comparison"]) == {"minimal", "v2_vs_minimal"}
    assert "v2_vs_minimal" not in res["criteria"]["passed"]
    assert res["comparison"]["v2_vs_minimal"] == pytest.approx(res["equity"]["v2"] / res["comparison"]["minimal"])

