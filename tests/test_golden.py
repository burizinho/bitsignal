"""S5: calibration-window regression against tests/golden/replay_summary.json (no network).

Regenerate on purpose, in a separate commit:
    python -m bitsignal.backtest.report --golden tests/golden/replay_summary.json
"""

import json
import math
from pathlib import Path

from bitsignal.backtest.engine import run_backtest
from bitsignal.backtest.report import golden_summary
from bitsignal.config import load_config
from bitsignal.data.history import load_frozen_history

GOLDEN = Path(__file__).parent / "golden" / "replay_summary.json"


def test_calibration_matches_golden():
    cfg = load_config()
    rep = run_backtest(load_frozen_history(cfg.data.csv_path), cfg, window="calibration", sensitivities=False)
    got = golden_summary(rep)
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert got["cycle_starts"] == expected["cycle_starts"]
    assert got["sell_steps"] == expected["sell_steps"]
    for key, value in expected["calibration"].items():
        assert math.isclose(got["calibration"][key], value, rel_tol=1e-9), key
    assert rep.criteria is None  # no 2019+ criteria before the freeze
