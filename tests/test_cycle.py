"""S4: cycle state machine, events and verdict (design §6, plan item 23)."""

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from bitsignal.config import apply_overrides, load_config
from bitsignal.engine.cycle import data_status, latest_verdict, replay, week_end
from bitsignal.models import DataStatus, EventType, Phase, ReplayResult, ScoreStatus

from engine_helpers import detector_frame, score_frame, weeks_index

CFG = load_config()
UNAV = ScoreStatus.UNAVAILABLE.value
OK = ScoreStatus.OK.value


def run(scores, levels=None, status=None, cfg=CFG, score_max=None):
    idx = weeks_index(len(scores))
    weekly = pd.DataFrame({"price": np.full(len(scores), 100.0)}, index=idx)
    out, events = replay(weekly, score_frame(idx, scores, score_max, status), detector_frame(idx, levels), cfg)
    return out, events


def test_ratchet_never_decreases_within_cycle():
    out, events = run([86, 91, 50, 70])
    assert out["ratchet_sell"].tolist() == [0.05, 0.15, 0.15, 0.15]
    assert [e.type for e in events] == [EventType.SELL_STEP, EventType.SELL_STEP]
    assert events[0].mechanism == "escada" and events[0].threshold == 85.0


def test_two_stage_reset_armed_on_2nd_week_effective_on_4th():
    out, events = run([15, 15, 35, 35])
    assert out["reset_pending"].tolist() == [False, True, True, False]
    assert out["cycle_id"].tolist() == [0, 0, 0, 1]
    assert out["cycle_start_date"].iloc[3] == out.index[3]
    assert [e.type for e in events] == [EventType.RESET_ARMED, EventType.CYCLE_START]


def test_unavailable_week_neither_counts_nor_resets():
    out, _ = run([15, np.nan, 15], status=[OK, UNAV, OK])
    assert out["reset_pending"].tolist() == [False, False, True]


def test_reset_only_without_active_detector_episode():
    out, _ = run([15, 15, 35, 35, 35], levels=[0, 0, 0, 1, 0])
    assert out["cycle_id"].tolist() == [0, 0, 0, 0, 1]  # blocked on the episode week


def test_reset_week_applies_neither_ladder_nor_detector():
    out, _ = run([15, 15, 90, 90])
    assert out["ratchet_sell"].iloc[2] == 0.15  # ladder still works while armed
    assert out["cycle_id"].iloc[3] == 1
    assert out["ratchet_sell"].iloc[3] == 0.0 and out["v_esc"].iloc[3] == 0.0


def test_detector_neutralized_while_accumulating():
    out, events = run([15, 15, 25, 25], levels=[0, 0, 2, 2])
    assert out["reset_pending"].iloc[2]
    assert out["v_det"].iloc[2] == CFG.detector.levels[1]
    assert out["v_det_eff"].iloc[2] == 0.0
    assert out["ratchet_sell"].iloc[2] == 0.0
    det = [e for e in events if e.type == EventType.DETECTOR_LEVEL]
    assert det and det[0].note == "neutralizado (ACUMULAR)"


def test_detector_raises_ratchet_outside_accumulation_and_respects_cap():
    out, events = run([50, 50, 95, 95], levels=[1, 3, 3, 3])
    assert out["ratchet_sell"].tolist() == [0.10, 0.50, 0.50, 0.50]
    assert out["ratchet_sell"].max() <= CFG.cap.cap
    steps = [e for e in events if e.type == EventType.SELL_STEP]
    assert [s.mechanism for s in steps] == ["detector", "detector"]


def test_buy_pct_by_score_and_independent_of_cycle():
    out, _ = run([8, 8, 15, 35, 35, 15, 15, 8], score_max=[8, 8, 15, 35, 35, 15, 15, 8])
    assert out["buy_pct"].tolist()[:3] == [0.0, 0.04, 0.02]  # armed on the 2nd week
    assert out["cycle_id"].iloc[4] == 1
    assert out["buy_pct"].tolist()[5:] == [0.0, 0.02, 0.04]  # same tiers in the next cycle


def test_uniform_branch_buys_even_when_score_unavailable():
    cfg = apply_overrides(CFG, {"buys": {"mode": "uniform"}})
    out, _ = run([15, 15, np.nan], status=[OK, OK, UNAV], cfg=cfg)
    assert out["buy_pct"].iloc[2] == pytest.approx(1 / 52)


def test_never_buy_and_sell_in_the_same_week():
    rng = np.random.default_rng(20261109)
    scores = rng.uniform(0, 100, 400)
    levels = rng.integers(0, 4, 400)
    out, _ = run(list(scores), levels=list(levels))
    rose = out["ratchet_sell"].diff().fillna(out["ratchet_sell"]) > 0
    assert not (rose & (out["buy_pct"] > 0)).any()


def test_score_unavailable_event_only_on_transition():
    _, events = run([50, np.nan, np.nan, 50, np.nan], status=[OK, UNAV, UNAV, OK, UNAV])
    assert sum(e.type == EventType.SCORE_UNAVAILABLE for e in events) == 2


def _result(scores, levels=None, status=None, score_max=None):
    out, events = run(scores, levels, status, score_max=score_max)
    return ReplayResult(weeks=out, events=events, as_of=out.index[-1].date(), model_hash="h")


def test_data_status_by_week_end():
    r = _result([50, 50])
    end = week_end(r.weeks.index[-1])
    assert data_status(r, end + timedelta(days=8), CFG) == DataStatus.OK
    assert data_status(r, end + timedelta(days=10), CFG) == DataStatus.STALE


def test_verdict_without_phase_when_stale():
    r = _result([50, 50])
    v = latest_verdict(r, week_end(r.weeks.index[-1]) + timedelta(days=10), CFG)
    assert v.data_status == DataStatus.STALE
    assert v.phase is None and v.sell_target is None and v.buy_pct is None


def test_verdict_reason_per_phase():
    now = lambda r: week_end(r.weeks.index[-1])  # noqa: E731
    dist = _result([86, 91])
    v = latest_verdict(dist, now(dist), CFG)
    assert v.phase == Phase.DISTRIBUTE and "escada" in v.reason and v.buy_pct is None

    acc = _result([15, 15, 8], score_max=[15, 15, 8])
    v = latest_verdict(acc, now(acc), CFG)
    assert v.phase == Phase.ACCUMULATE and v.buy_pct == 0.04 and "reinício armado" in v.reason

    hold = _result([50, 50])
    v = latest_verdict(hold, now(hold), CFG)
    assert v.phase == Phase.HOLD and "sem sinal" in v.reason and v.sell_target == 0.0

    interval = _result([50, 50], status=[OK, ScoreStatus.INTERVAL.value])
    assert "intervalo" in latest_verdict(interval, now(interval), CFG).reason


def test_verdict_now_is_timezone_aware():
    r = _result([50])
    assert latest_verdict(r, datetime.now(timezone.utc), CFG).week == r.weeks.index[-1].date()
