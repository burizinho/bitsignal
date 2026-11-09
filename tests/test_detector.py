"""S4: reversal detector on synthetic weekly series (design §5)."""

import numpy as np

from bitsignal.config import load_config
from bitsignal.engine.detector import detect, episodes

from engine_helpers import weekly_detector_frame

CFG = load_config()  # arming 52, trend SMA (given), confirm 2, trigger <= 0.80 * high, N3 <= 0.60 * high


def below_trend(frame, weeks, price):
    """Put the price below trend_sma (90) on the given weeks."""
    p = frame["price"].to_numpy().copy()
    for i in weeks:
        p[i] = price
    frame["price"] = p
    return frame


def ath_at(frame, i):
    a = frame["new_ath"].to_numpy().copy()
    a[i] = True
    frame["new_ath"] = a
    return frame


def test_episode_opens_only_when_armed():
    f = weekly_detector_frame(10)
    f = below_trend(f, [5, 6, 7], 75.0)  # 75 <= 80 and below trend for 2 weeks at week 6
    assert detect(f, CFG)["level"].sum() == 0  # never armed
    f = ath_at(f, 0)
    d = detect(f, CFG)
    assert d["triggered"].tolist().index(True) == 6
    assert d["level"].iloc[6] == 1


def test_arming_expires_after_52_weeks_without_ath():
    f = ath_at(weekly_detector_frame(70), 0)
    f = below_trend(f, [60, 61], 75.0)
    assert detect(f, CFG)["level"].max() == 0  # week 61 is outside the 52-week window
    f2 = ath_at(weekly_detector_frame(70), 0)
    f2 = below_trend(f2, [40, 41], 75.0)
    assert detect(f2, CFG)["level"].iloc[41] == 1


def test_no_repeat_and_level_only_rises_and_survives_arming_expiry():
    f = ath_at(weekly_detector_frame(80), 0)
    f = below_trend(f, range(40, 75), 75.0)  # long episode, well past week 52
    d = detect(f, CFG)
    assert d["triggered"].sum() == 1
    lv = d["level"].iloc[41:75].to_numpy()
    assert (np.diff(lv) >= 0).all()
    assert (d["level"].iloc[53:75] >= 1).all()  # arming expired at week 52, episode continues


def test_closing_week_keeps_level_then_zero_and_end_is_closing_week():
    f = ath_at(weekly_detector_frame(20), 0)
    f = below_trend(f, [5, 6, 7], 75.0)  # trigger at 6; weeks 8, 9 above trend -> closes at 9
    d = detect(f, CFG)
    assert d["level"].iloc[9] == 1 and bool(d["episode_closing"].iloc[9])
    assert d["level"].iloc[10] == 0
    eps = episodes(d)
    assert eps == [{"start": f.index[6].date().isoformat(), "n2": None, "n3": None,
                    "end": f.index[9].date().isoformat(), "max_level": 1}]


def test_new_episode_needs_armed_trigger_but_not_new_ath():
    f = ath_at(weekly_detector_frame(30), 0)
    f = below_trend(f, [5, 6, 7], 75.0)  # episode 1: 6..9
    f = below_trend(f, [14, 15], 75.0)  # still armed (ATH at week 0), no new ATH since
    d = detect(f, CFG)
    assert d["triggered"].sum() == 2
    assert d["episode_id"].iloc[15] == 2


def test_n2_uses_previous_week_and_n3_only_after_n2():
    f = ath_at(weekly_detector_frame(20), 0)
    n2 = f["n2_sma"].to_numpy().copy()
    n2[5:8] = 85.0  # price 75 < 85 at weeks 5 and 6 -> N2 already true on trigger week 6
    f["n2_sma"] = n2
    f = below_trend(f, [5, 6, 7], 75.0)
    d = detect(f, CFG)
    assert d["level"].iloc[6] == 2  # N2 counted with the week before the trigger
    assert d["level"].iloc[7] == 2  # 75 > 60, no N3

    g = ath_at(weekly_detector_frame(20), 0)
    g = below_trend(g, [5, 6, 7], 55.0)  # <= 60 and price 55 < n2_sma 70: N2 and N3 same week
    dg = detect(g, CFG)
    assert dg["level"].iloc[6] == 3

    h = ath_at(weekly_detector_frame(20), 0)
    n2h = h["n2_sma"].to_numpy().copy()
    n2h[:] = 40.0  # never below n2_sma -> no N2 -> no N3 even at 55
    h["n2_sma"] = n2h
    h = below_trend(h, [5, 6, 7], 55.0)
    assert detect(h, CFG)["level"].max() == 1


def test_v_det_follows_levels():
    f = ath_at(weekly_detector_frame(10), 0)
    f = below_trend(f, [5, 6, 7], 55.0)
    d = detect(f, CFG)
    assert d["v_det"].iloc[6] == CFG.detector.levels[2]
    assert d["v_det"].iloc[0] == 0.0
