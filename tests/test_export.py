"""CSV export for the spreadsheet: Brazilian and international formats."""

import csv
import io
from datetime import datetime, timezone

from bitsignal.config import load_config
from bitsignal.data.history import load_frozen_history
from bitsignal.engine.cycle import latest_verdict
from bitsignal.engine.pipeline import run_model
from bitsignal.ui.export import read_log, rows_to_csv
from bitsignal.verdict_log import COLUMNS, verdict_row

CFG = load_config()
NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
RESULT = run_model(load_frozen_history(CFG.data.csv_path), CFG)
ROW = verdict_row(RESULT, latest_verdict(RESULT, NOW, CFG), NOW)


def parse(data: bytes, delimiter: str):
    text = data.decode("utf-8")
    assert text.startswith("\ufeff")  # BOM: Excel shows the accents
    return list(csv.DictReader(io.StringIO(text[1:]), delimiter=delimiter))


def test_brazilian_format_uses_semicolon_and_decimal_comma_only_in_numbers():
    rows = parse(rows_to_csv([ROW, {**ROW, "buy_pct": "all_cash"}], brazil=True), ";")
    assert list(rows[0]) == COLUMNS
    r = rows[0]
    assert r["sell_target"] == "0,2500" and r["buy_pct"] == "0,0200" and r["price_usd"] == "74967,72"
    assert r["week"] == "2026-11-08" and r["model_hash"] == ROW["model_hash"]  # dates and hash untouched
    assert "score_max 15.5" in r["reason"]  # numbers inside text are not changed
    assert rows[1]["buy_pct"] == "all_cash"


def test_international_format_keeps_the_log_values():
    rows = parse(rows_to_csv([ROW], brazil=False), ",")
    assert rows[0] == ROW


def test_read_log(tmp_path):
    assert read_log(tmp_path / "missing.csv") is None
    rows = read_log("data/verdicts/weekly_verdicts.csv")
    assert rows and set(rows[0]) == set(COLUMNS)
