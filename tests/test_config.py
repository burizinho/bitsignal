"""S2: config único validado (plan items 8–10)."""

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import yaml

from bitsignal.config import (
    DEFAULT_CONFIG_PATH,
    REPO_ROOT,
    Approval,
    ConfigError,
    FrozenParams,
    apply_overrides,
    config_from_dict,
    load_config,
    load_frozen_params,
    model_hash,
    model_payload,
    repo_path,
    validate_for_panel,
    write_frozen_params,
)


@pytest.fixture
def raw():
    with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def test_versioned_yaml_loads():
    cfg = load_config()
    assert cfg.cap.cap == 0.5
    assert cfg.backtest.start == "first_all_valid_week"
    assert cfg.backtest.calibration_end == date(2018, 12, 31)
    assert [e.name for e in cfg.backtest.events][0] == "fundo_2015"
    assert cfg.buys.mode == "score_dca"


def _error_path(raw_cfg):
    with pytest.raises(ConfigError) as exc:
        config_from_dict(raw_cfg)
    return exc.value.path


def test_unknown_key_is_rejected_with_path(raw):
    raw["detector"]["unexpected"] = 1
    assert _error_path(raw).startswith("detector")


def test_weights_must_sum_to_one(raw):
    raw["score"]["inputs"]["mvrv_z"]["weight"] = 0.30
    assert _error_path(raw).startswith("score")


def test_ladder_must_be_increasing(raw):
    raw["sell_ladder"] = [[90.0, 0.05], [85.0, 0.15], [93.0, 0.30]]
    assert _error_path(raw).startswith("sell_ladder")


def test_max_must_exceed_min(raw):
    raw["score"]["inputs"]["puell"]["max"] = 0.40
    assert _error_path(raw).startswith("score")


def test_levels_cannot_exceed_one_minus_floor(raw):
    raw["cap"]["floor"] = 0.60  # cap 0.40 < N3 0.50
    with pytest.raises(ConfigError) as exc:
        config_from_dict(raw)
    assert "detector.levels" in exc.value.message


def test_invalid_sensitivity_is_reported(tmp_path, raw):
    raw["backtest"]["sensitivities"]["broken"] = {"backtest": {"fee": 0.5}}
    p = tmp_path / "cfg.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_config(p)
    assert exc.value.path.startswith("backtest.sensitivities.broken")


def test_apply_overrides_deep_merges_replaces_lists_and_keeps_original():
    cfg = load_config()
    before = model_hash(cfg)
    new = apply_overrides(
        cfg,
        {"backtest": {"reserve_btc_equiv": 1.0}, "detector": {"levels": [0.05, 0.20, 0.40]}},
    )
    assert new.backtest.reserve_btc_equiv == 1.0
    assert new.backtest.fee == cfg.backtest.fee  # sibling kept (deep merge)
    assert new.detector.levels == [0.05, 0.20, 0.40]  # list replaced whole
    assert cfg.backtest.reserve_btc_equiv == 0.5
    assert model_hash(cfg) == before


def test_apply_overrides_revalidates():
    cfg = load_config()
    with pytest.raises(ConfigError):
        apply_overrides(cfg, {"cycle": {"arm_score": 40.0}})  # arm >= confirm


def test_model_hash_ignores_data_ui_and_frozen_pointer():
    cfg = load_config()
    h = model_hash(cfg)
    assert model_hash(apply_overrides(cfg, {"data": {"max_staleness_days": 30}})) == h
    assert model_hash(apply_overrides(cfg, {"ui": {"retry_cooldown_s": 5}})) == h
    assert model_hash(apply_overrides(cfg, {"backtest": {"frozen_params": "config/frozen/x.yaml"}})) == h
    assert model_hash(apply_overrides(cfg, {"backtest": {"start": date(2019, 1, 1)}})) == h


@pytest.mark.parametrize(
    "override",
    [
        {"sell_ladder": [[86.0, 0.05], [90.0, 0.15], [93.0, 0.30]]},
        {"detector": {"trend_sma_weeks": 20}},
        {"cap": {"floor": 0.4}},
        {"cycle": {"confirm_score": 31.0}},
        {"buys": {"uniform_weeks": 26}},
        {"score": {"picycle_bottom_factor": 0.75}},
        {"backtest": {"fee": 0.004}},
        {"backtest": {"criteria": {"equity_vs_bnh": 0.95}}},
        {"backtest": {"execution_lag_days": 2}},
        {"backtest": {"reserve_btc_equiv": 1.0}},
    ],
)
def test_model_hash_changes_with_model_payload(override):
    cfg = load_config()
    assert model_hash(apply_overrides(cfg, override)) != model_hash(cfg)


def test_model_payload_keys():
    payload = model_payload(load_config())
    assert set(payload) == {"score", "sell_ladder", "detector", "cap", "cycle", "buys", "backtest"}
    assert set(payload["backtest"]) == {
        "initial_btc", "reserve_btc_equiv", "execution_lag_days", "fee",
        "approval_window_start", "criteria",
    }


def test_frozen_params_roundtrip_preserves_hash(tmp_path):
    cfg = load_config()
    frozen = FrozenParams(
        frozen_at=datetime(2026, 11, 9, tzinfo=timezone.utc),
        csv_sha256="abc",
        model_hash=model_hash(cfg),
        model=model_payload(cfg),
    )
    path = write_frozen_params(tmp_path / "params.yaml", frozen)
    loaded = load_frozen_params(path)
    assert loaded is not None
    assert loaded.model_hash == model_hash(cfg)
    assert loaded.model == model_payload(cfg)
    assert loaded.approval is None

    with_approval = loaded.model_copy(
        update={
            "approval": Approval(
                run_at=datetime(2026, 11, 10, tzinfo=timezone.utc),
                window="development",
                passed={"equity_vs_bnh": True, "dd_improvement_pp": False, "equity_vs_uniform": True},
                values={"equity_vs_bnh": 0.93, "dd_improvement_pp": 4.2, "equity_vs_uniform": 1.02},
            )
        }
    )
    write_frozen_params(path, with_approval)
    again = load_frozen_params(path)
    assert again.approval is not None and again.approval.passed.dd_improvement_pp is False


def test_load_frozen_params_missing_returns_none(tmp_path):
    assert load_frozen_params(None) is None
    assert load_frozen_params(tmp_path / "nope.yaml") is None


def test_repo_path_resolves_against_repo_root():
    assert repo_path("data/historical/x.csv") == REPO_ROOT / "data" / "historical" / "x.csv"
    absolute = Path(REPO_ROOT) / "config"
    assert repo_path(absolute) == absolute


def test_validate_for_panel():
    cfg = load_config()
    validate_for_panel(cfg)  # default accepted
    with pytest.raises(ConfigError) as exc:
        validate_for_panel(apply_overrides(cfg, {"buys": {"mode": "uniform"}}))
    assert exc.value.path == "buys.mode"
