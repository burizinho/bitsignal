"""S4: the model never uses future data (frozen CSV, no network)."""

import numpy as np
import pandas as pd
import pytest

from bitsignal.config import load_config
from bitsignal.data.history import load_frozen_history
from bitsignal.engine.pipeline import run_model

CFG = load_config()


@pytest.fixture(scope="module")
def history():
    return load_frozen_history(CFG.data.csv_path)


@pytest.fixture(scope="module")
def full(history):
    return run_model(history, CFG)


def test_truncation_does_not_change_the_past(history, full):
    rng = np.random.default_rng(20261108)
    days = history.daily.index
    picks = rng.choice(np.arange(500, len(days)), size=20, replace=False)
    for i in sorted(picks):
        t = days[i]
        partial = run_model(history.truncate(t), CFG).weeks
        expected = full.weeks.loc[: partial.index[-1]] if len(partial) else full.weeks.iloc[:0]
        pd.testing.assert_frame_equal(partial, expected, check_freq=False, obj=f"weeks truncated at {t.date()}")


def test_events_before_t_are_identical(history, full):
    t = pd.Timestamp("2022-06-30")
    partial = run_model(history.truncate(t), CFG)
    last_week = partial.weeks.index[-1].date()
    assert partial.events == [e for e in full.events if e.date <= last_week]
