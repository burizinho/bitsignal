"""S5: production detector vs the independent oracle (sev.py), offline on the frozen CSV."""

import json
from pathlib import Path

from bitsignal.config import load_config
from bitsignal.data.history import derive_daily, load_frozen_history
from bitsignal.engine.detector import detect, episodes
from bitsignal.engine.weekly import to_weekly

GOLDEN = Path(__file__).parent / "golden" / "detector_episodes.json"


def test_detector_matches_golden_episodes():
    cfg = load_config()
    h = load_frozen_history(cfg.data.csv_path)
    weekly = to_weekly(derive_daily(h, cfg), h.as_of, cfg)
    got = episodes(detect(weekly, cfg))
    expected = json.loads(GOLDEN.read_text(encoding="utf-8"))
    assert got == expected


def test_golden_contains_the_six_q5b_cases():
    eps = {e["start"][:7]: e["max_level"] for e in json.loads(GOLDEN.read_text(encoding="utf-8"))}
    # false positives stop at N1; real bear markets reach N3 (design Q5b)
    assert eps["2021-05"] == 1 and eps["2024-09"] == 1 and eps["2025-03"] == 1
    assert eps["2018-03"] == 3 and eps["2022-01"] == 3 and eps["2025-11"] == 3
