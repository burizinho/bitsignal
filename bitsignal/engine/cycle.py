"""Cycle state machine: ratchet, reset and buys (design §6, plan item 23).

Implements steps 1–5 of the §6 pseudocode in order. Nothing is persisted: the state is
rebuilt week by week from the history on every call.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import pandas as pd

from bitsignal.config import Config
from bitsignal.models import DataStatus, Event, EventType, Phase, ReplayResult, ScoreStatus, Verdict

UNAVAILABLE = ScoreStatus.UNAVAILABLE.value


def _ladder(score_min: float, cfg: Config) -> Tuple[float, Optional[float]]:
    """(v_esc, threshold reached) for a ``score_min``; (0, None) below the first step or NaN."""
    v, thr = 0.0, None
    if pd.isna(score_min):
        return v, thr
    for threshold, pct in cfg.sell_ladder:
        if score_min >= threshold:
            v, thr = pct, threshold
    return v, thr


def _buy_pct(score_max: float, cfg: Config) -> float:
    if pd.isna(score_max):
        return 0.0
    for limit, pct in cfg.buys.tiers:  # ascending limits: first tier with score_max <= limit
        if score_max <= limit:
            return pct
    return 0.0


def replay(weekly: pd.DataFrame, score_df: pd.DataFrame, detector_df: pd.DataFrame, cfg: Config) -> Tuple[pd.DataFrame, List[Event]]:
    cap = cfg.cap.cap
    levels = [0.0] + list(cfg.detector.levels)
    cyc = cfg.cycle

    cycle_id = 0
    cycle_start = weekly.index[0] if len(weekly) else None
    ratchet = 0.0
    reset_pending = False
    arm_count = confirm_count = 0
    prev_status: Optional[str] = None
    prev_level = 0
    events: List[Event] = []
    rows = []

    for t in weekly.index:
        d = t.date()
        # 1. score and detector of the week
        status = score_df.at[t, "status"]
        smin = score_df.at[t, "score_min"]
        smax = score_df.at[t, "score_max"]
        level = int(detector_df.at[t, "level"])
        v_det = levels[level]

        if status == UNAVAILABLE and prev_status != UNAVAILABLE:
            events.append(Event(d, EventType.SCORE_UNAVAILABLE, "dados"))
        if level > prev_level:
            events.append(
                Event(d, EventType.DETECTOR_LEVEL, "detector", float(level), float(prev_level), float(level),
                      "neutralizado (ACUMULAR)" if reset_pending else "")
            )

        # 2. reset counters (unavailable weeks neither count nor reset)
        if status != UNAVAILABLE:
            arm_count = arm_count + 1 if smax <= cyc.arm_score else 0
            confirm_count = confirm_count + 1 if smin >= cyc.confirm_score else 0
        if not reset_pending and arm_count >= cyc.arm_weeks:
            reset_pending = True
            events.append(Event(d, EventType.RESET_ARMED, "score", cyc.arm_score))

        v_esc = v_det_eff = buy = 0.0
        # 3. effective reset: new cycle; no ladder/detector this week
        if reset_pending and confirm_count >= cyc.confirm_weeks and level == 0:
            events.append(Event(d, EventType.CYCLE_START, "score", cyc.confirm_score, ratchet, 0.0))
            ratchet = 0.0
            cycle_id += 1
            cycle_start = t
            reset_pending = False
            arm_count = confirm_count = 0
        else:
            # 4. ratchet
            if status != UNAVAILABLE:
                v_esc, thr = _ladder(smin, cfg)
            else:
                thr = None
            v_det_eff = 0.0 if reset_pending else v_det
            new = min(cap, max(ratchet, v_esc, v_det_eff))
            if new > ratchet + 1e-12:
                if min(cap, v_esc) >= new - 1e-12:
                    events.append(Event(d, EventType.SELL_STEP, "escada", thr, ratchet, new))
                else:
                    events.append(Event(d, EventType.SELL_STEP, "detector", float(level), ratchet, new))
                ratchet = new
            # 5. buys
            if reset_pending:
                if cfg.buys.mode == "uniform":
                    buy = 1.0 / cfg.buys.uniform_weeks
                elif status != UNAVAILABLE:
                    buy = _buy_pct(smax, cfg)

        phase = Phase.ACCUMULATE if reset_pending else (Phase.DISTRIBUTE if ratchet > 0 else Phase.HOLD)
        rows.append(
            {
                "v_esc": v_esc,
                "v_det": v_det,
                "v_det_eff": v_det_eff,
                "ratchet_sell": ratchet,
                "reset_pending": reset_pending,
                "cycle_id": cycle_id,
                "cycle_start_date": cycle_start,
                "phase": phase.value,
                "buy_pct": buy,
            }
        )
        prev_status = status
        prev_level = level

    state = pd.DataFrame(rows, index=weekly.index)
    out = pd.concat(
        [
            weekly,
            score_df[["score", "score_min", "score_max", "status"]],
            detector_df[["level", "armed", "episode_id", "episode_closing"]],
            state,
        ],
        axis=1,
    )
    return out, events


# --------------------------------------------------------------------------------------
# Verdict
# --------------------------------------------------------------------------------------


def week_end(week) -> datetime:
    """A W-SUN week ends at Sunday + 1 day, 00:00 UTC."""
    return datetime.combine(pd.Timestamp(week).date() + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)


def data_status(result: ReplayResult, now_utc: datetime, cfg: Config) -> DataStatus:
    if result.weeks is None or len(result.weeks) == 0:
        return DataStatus.STALE
    end = week_end(result.weeks.index[-1])
    if now_utc - end > timedelta(days=cfg.data.max_staleness_days):
        return DataStatus.STALE
    return DataStatus.OK


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def latest_verdict(result: ReplayResult, now_utc: datetime, cfg: Config) -> Verdict:
    ds = data_status(result, now_utc, cfg)
    weeks = result.weeks
    last_week = weeks.index[-1].date() if len(weeks) else None
    if ds != DataStatus.OK:
        return Verdict(week=last_week, data_status=ds, reason="dados desatualizados: sem veredito nesta carga")

    row = weeks.iloc[-1]
    phase = Phase(row["phase"])
    status = ScoreStatus(row["status"])
    cycle_start = pd.Timestamp(row["cycle_start_date"]).date()
    cycle_events = [e for e in result.events if e.date >= cycle_start]

    if phase == Phase.DISTRIBUTE:
        steps = [e for e in cycle_events if e.type == EventType.SELL_STEP]
        last = steps[-1] if steps else None
        if last is not None:
            limiar = f"score {last.threshold:.0f}" if last.mechanism == "escada" else f"nível N{int(last.threshold)}"
            reason = f"venda acumulada-alvo {_fmt_pct(row['ratchet_sell'])} desde {last.date.isoformat()} ({last.mechanism}, {limiar})"
        else:
            reason = f"venda acumulada-alvo {_fmt_pct(row['ratchet_sell'])}"
    elif phase == Phase.ACCUMULATE:
        armed = [e for e in result.events if e.type == EventType.RESET_ARMED]
        when = armed[-1].date.isoformat() if armed else "?"
        smax = row["score_max"]
        smax_txt = "—" if pd.isna(smax) else f"{smax:.1f}"
        reason = f"reinício armado em {when}; score_max {smax_txt} → compra {_fmt_pct(row['buy_pct'])}"
    else:
        reason = f"sem sinal no ciclo iniciado em {cycle_start.isoformat()}"
    if status == ScoreStatus.INTERVAL:
        reason += " · score em intervalo"
    elif status == ScoreStatus.UNAVAILABLE:
        reason += " · score indisponível"

    buy = None
    if phase == Phase.ACCUMULATE and status != ScoreStatus.UNAVAILABLE:
        buy = float(row["buy_pct"])
    return Verdict(
        week=last_week,
        data_status=ds,
        phase=phase,
        sell_target=float(row["ratchet_sell"]),
        cycle_start_date=cycle_start,
        buy_pct=buy,
        reason=reason,
        score_status=status,
    )
