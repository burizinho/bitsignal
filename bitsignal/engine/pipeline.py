"""Single entry point of the model (plan item 24), used by the dashboard, backtest and CLI."""

from __future__ import annotations

from bitsignal.config import Config, model_hash
from bitsignal.data.history import MarketHistory, derive_daily
from bitsignal.engine.cycle import replay
from bitsignal.engine.detector import detect
from bitsignal.engine.score import score_weekly
from bitsignal.engine.weekly import to_weekly
from bitsignal.models import ReplayResult


def run_model(history: MarketHistory, cfg: Config) -> ReplayResult:
    daily = derive_daily(history, cfg)
    weekly = to_weekly(daily, history.as_of, cfg)
    score_df = score_weekly(weekly, cfg)
    detector_df = detect(weekly, cfg)
    weeks, events = replay(weekly, score_df, detector_df, cfg)
    return ReplayResult(weeks=weeks, events=events, as_of=history.as_of, model_hash=model_hash(cfg))
