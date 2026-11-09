"""S6: freeze-params and the single 2019+ recording (`backtest --window development --record`)."""

import argparse
import shutil
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

import pytest

from bitsignal import cli
from bitsignal import config as config_mod
from bitsignal.config import (
    DEFAULT_CONFIG_PATH,
    FrozenParams,
    apply_overrides,
    load_config,
    load_frozen_params,
    model_hash,
    model_payload,
    write_frozen_params,
)

CRITERIA = {
    "passed": {"equity_vs_bnh": True, "dd_improvement_pp": False, "equity_vs_uniform": True},
    "values": {"equity_vs_bnh": 0.95, "dd_improvement_pp": 4.0, "equity_vs_uniform": 1.01},
}


# ---------------------------------------------------------------- freeze-params


@pytest.fixture
def cfg_copy(tmp_path):
    p = tmp_path / "config.yaml"
    shutil.copy(DEFAULT_CONFIG_PATH, p)
    return p


def _freeze(out, cfg_path, tests_ok=True):
    args = argparse.Namespace(out=str(out), config_path=cfg_path)
    with mock.patch.object(cli, "_run_technical_tests", return_value=tests_ok), \
         mock.patch("bitsignal.data.history.load_frozen_history", return_value=SimpleNamespace(csv_sha256="abc")):
        cli.cmd_freeze_params(args)


def test_freeze_refuses_when_tests_fail(tmp_path, cfg_copy):
    out = tmp_path / "frozen.yaml"
    with pytest.raises(SystemExit):
        _freeze(out, cfg_copy, tests_ok=False)
    assert not out.exists()


def test_freeze_refuses_to_overwrite(tmp_path, cfg_copy):
    out = tmp_path / "frozen.yaml"
    out.write_text("existing", encoding="utf-8")
    with pytest.raises(SystemExit):
        _freeze(out, cfg_copy)
    assert out.read_text(encoding="utf-8") == "existing"


def test_freeze_writes_schema_and_points_config(tmp_path, cfg_copy):
    out = tmp_path / "frozen.yaml"
    _freeze(out, cfg_copy)
    frozen = load_frozen_params(out)
    cfg = load_config()
    assert frozen.approval is None
    assert frozen.model_hash == model_hash(cfg)
    assert frozen.model == model_payload(cfg)
    assert frozen.csv_sha256 == "abc"
    pointed = load_config(cfg_copy)
    assert pointed.backtest.frozen_params == str(out)
    assert model_hash(pointed) == frozen.model_hash  # the pointer is outside the hash
    assert "fora do model_hash" in cfg_copy.read_text(encoding="utf-8")  # comment kept


# ---------------------------------------------------------------- --record


@pytest.fixture
def frozen_setup(tmp_path):
    base = load_config("config/config_v1.yaml")  # the S6 record flow is the v1 one
    path = tmp_path / "frozen.yaml"
    cfg = apply_overrides(base, {"backtest": {"frozen_params": str(path)}})
    frozen = FrozenParams(frozen_at=datetime.now(timezone.utc), csv_sha256="abc",
                          model_hash=model_hash(cfg), model=model_payload(cfg))
    write_frozen_params(path, frozen)
    return cfg, path


def _record(cfg, window="development", record=True, committed=True):
    args = argparse.Namespace(window=window, no_sensitivities=True, record=record)
    fake_report = SimpleNamespace(criteria=CRITERIA)
    with mock.patch.object(config_mod, "load_config", return_value=cfg), \
         mock.patch("bitsignal.data.history.load_frozen_history", return_value=object()), \
         mock.patch.object(cli, "run_backtest", return_value=fake_report) as rb, \
         mock.patch("bitsignal.backtest.report.to_text", return_value="report"), \
         mock.patch.object(cli, "_git_committed_clean", return_value=committed):
        cli.cmd_backtest(args)
    return rb


def test_record_requires_development_window(frozen_setup):
    cfg, path = frozen_setup
    with pytest.raises(SystemExit):
        _record(cfg, window="calibration")
    assert load_frozen_params(path).approval is None


def test_record_refuses_uncommitted_frozen_file(frozen_setup):
    cfg, path = frozen_setup
    with pytest.raises(SystemExit):
        _record(cfg, committed=False)
    assert load_frozen_params(path).approval is None


def test_record_refuses_hash_mismatch(frozen_setup):
    cfg, path = frozen_setup
    changed = apply_overrides(cfg, {"cap": {"floor": 0.55}, "detector": {"levels": [0.10, 0.25, 0.45]}})
    with pytest.raises(SystemExit):
        _record(changed)
    assert load_frozen_params(path).approval is None


def test_record_happy_path_then_refuses_second_time(frozen_setup):
    cfg, path = frozen_setup
    rb = _record(cfg)
    assert rb.call_args.kwargs["window"] == "development"
    approval = load_frozen_params(path).approval
    assert approval is not None and approval.window == "development"
    assert approval.passed.dd_improvement_pp is False and approval.values.equity_vs_bnh == 0.95
    with pytest.raises(SystemExit):
        _record(cfg)  # approval already recorded: single evaluation
    assert load_frozen_params(path).approval == approval


def test_refusal_message_has_no_side_effect_without_frozen_file(tmp_path):
    cfg = apply_overrides(load_config(), {"backtest": {"frozen_params": str(tmp_path / "missing.yaml")}})
    with pytest.raises(SystemExit):
        _record(cfg)
    assert not (tmp_path / "missing.yaml").exists()


def test_git_check_rejects_untracked_and_accepts_committed(tmp_path):
    from bitsignal.config import REPO_ROOT

    untracked = tmp_path / "x.yaml"
    untracked.write_text("a: 1", encoding="utf-8")
    assert cli._git_committed_clean(untracked) is False
    assert cli._git_committed_clean(REPO_ROOT / "config" / "frozen" / "params_2026-11-09.yaml") is True
