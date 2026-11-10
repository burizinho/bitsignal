"""Weekly verdict log (forward validation): append-only, one row per closed week, no network."""

import argparse
import csv
import io
from datetime import datetime, timezone
from unittest import mock

import pytest

from bitsignal import cli
from bitsignal.config import load_config
from bitsignal.data.history import load_frozen_history
from bitsignal.engine.cycle import latest_verdict
from bitsignal.engine.pipeline import run_model
from bitsignal.verdict_log import COLUMNS, append_verdict, last_recorded_week, verdict_row

CFG = load_config()
HISTORY = load_frozen_history(CFG.data.csv_path)  # as_of 2026-11-08 (Sunday)
NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)


def _row(history=HISTORY, now=NOW):
    result = run_model(history, CFG)
    return verdict_row(result, latest_verdict(result, now, CFG), now)


def _read(path):
    with io.open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_row_matches_verdict():
    row = _row()
    assert list(row) == COLUMNS
    assert row["week"] == "2026-11-08"
    assert row["phase"] == "ACCUMULATE"
    assert row["sell_target"] == "0.2500"
    assert row["buy_pct"] == "0.0200"
    assert row["cycle_start_date"] == "2023-11-12"
    assert row["recorded_at"] == "2026-11-09T12:00:00Z"
    assert len(row["model_hash"]) == 64


def test_append_creates_file_and_never_rewrites(tmp_path):
    path = tmp_path / "v" / "log.csv"
    older = _row(HISTORY.truncate("2026-11-01"), datetime(2026, 11, 2, 12, tzinfo=timezone.utc))
    assert append_verdict(path, older) is True
    assert append_verdict(path, _row()) is True
    before = path.read_bytes()

    changed = dict(_row(), phase="DISTRIBUTE")
    assert append_verdict(path, changed) is False  # same week: kept as recorded
    assert append_verdict(path, older) is False  # older week: never inserted
    assert path.read_bytes() == before
    rows = _read(path)
    assert [r["week"] for r in rows] == ["2026-11-01", "2026-11-08"]
    assert rows[-1]["phase"] == "ACCUMULATE"
    assert b"\r\n" not in before
    assert last_recorded_week(path) == "2026-11-08"


def _run_cli(tmp_path, now):
    out = tmp_path / "log.csv"
    with mock.patch("bitsignal.data.coinmetrics.fetch_coinmetrics", return_value=HISTORY.daily), \
            mock.patch.object(cli, "_now_utc", return_value=now):
        cli.cmd_record_verdict(argparse.Namespace(out=str(out)))
    return out


def test_cli_records_once(tmp_path, capsys):
    out = _run_cli(tmp_path, NOW)
    assert [r["week"] for r in _read(out)] == ["2026-11-08"]
    _run_cli(tmp_path, NOW)
    assert len(_read(out)) == 1
    assert "já estava gravada" in capsys.readouterr().out


def test_cli_stale_data_fails_without_writing(tmp_path):
    with pytest.raises(SystemExit) as exc:
        _run_cli(tmp_path, datetime(2026, 11, 30, tzinfo=timezone.utc))
    assert exc.value.code == 1
    assert not (tmp_path / "log.csv").exists()


def test_log_status_flags_missing_and_late_logs(tmp_path):
    from bitsignal.verdict_log import log_status

    path = tmp_path / "log.csv"
    append_verdict(path, _row())  # week 2026-11-08, ends Monday 2026-11-09 00:00 UTC
    logs = {"v2": path, "v1": tmp_path / "missing.csv"}
    fresh, missing = log_status(logs, datetime(2026, 11, 10, tzinfo=timezone.utc), 9)
    assert fresh.model == "v2" and str(fresh.last_week) == "2026-11-08" and not fresh.late
    assert missing.last_week is None and missing.late
    (late,) = log_status({"v2": path}, datetime(2026, 11, 18, 1, tzinfo=timezone.utc), 9)
    assert late.late  # more than 9 days after the week ended: the weekly run probably failed
