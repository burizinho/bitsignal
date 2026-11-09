"""S7: new dashboard smoke tests (streamlit AppTest), without network."""

import os
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

import bitsignal.ui.app as app  # noqa: E402
from bitsignal.config import (  # noqa: E402
    Approval,
    FrozenParams,
    apply_overrides,
    load_config,
    model_hash,
    model_payload,
)
from bitsignal.data.coinmetrics import DataUnavailable  # noqa: E402
from bitsignal.data.history import load_frozen_history  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ENTRY = str(ROOT / "streamlit_app.py")
CFG = load_config()
HISTORY = load_frozen_history(CFG.data.csv_path)
NOW_OK = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)  # history as_of 2026-11-08


def _raise():
    raise DataUnavailable("down")


def run_app(history=HISTORY, now=NOW_OK, cfg=CFG, frozen="real"):
    patches = [
        mock.patch.object(app, "load_history", (lambda: history) if not callable(history) else history),
        mock.patch.object(app, "now_utc", lambda: now),
        mock.patch.object(app, "get_config", lambda: cfg),
        mock.patch.object(app, "cached_spot", lambda: (75000.0, now)),
    ]
    if frozen != "real":
        patches.append(mock.patch.object(app, "load_frozen_params", lambda path: frozen))
    old_cwd = os.getcwd()
    os.chdir(ROOT)
    env = {k: v for k, v in os.environ.items() if k not in ("DUNE_API_KEY", "DUNE_QUERY_ID")}
    try:
        with mock.patch.dict(os.environ, env, clear=True):
            for p in patches:
                p.start()
            at = AppTest.from_file(ENTRY, default_timeout=120).run()
    finally:
        for p in reversed(patches):
            p.stop()
        os.chdir(old_cwd)
    return at


def texts(elements):
    return " | ".join(e.value for e in elements)


def test_top_line_and_experimental_badge():
    at = run_app()
    assert not at.exception
    assert "Semana fechada em 08/11/2026" in texts(at.markdown)
    assert "Venda acumulada-alvo no ciclo" in texts(at.markdown)
    assert "Experimental" in texts(at.warning)  # v2: no recorded evaluation
    assert "Janela de calibração" in texts(at.caption)
    assert "não alteram a posição-base" in texts(at.info)  # ACCUMULATE fixed notice
    assert "O que mudaria o veredito" in texts(at.markdown)
    assert "score mínimo ≥ 30 por 2 semanas" in texts(at.markdown)


def test_stale_data_shows_no_verdict():
    at = run_app(now=datetime(2026, 11, 30, tzinfo=timezone.utc))
    assert not at.exception
    assert "Dados desatualizados" in texts(at.error)
    assert "Semana fechada" not in texts(at.markdown)
    assert any(b.label == "Tentar de novo" for b in at.button)


def test_source_unavailable_shows_no_verdict():
    at = run_app(history=_raise)
    assert not at.exception
    assert "indisponíveis" in texts(at.error)
    assert "Semana fechada" not in texts(at.markdown)


def test_comparison_only_config_is_rejected():
    at = run_app(cfg=apply_overrides(CFG, {"buys": {"mode": "uniform"}}))
    assert "buys.mode" in texts(at.error)
    assert "Semana fechada" not in texts(at.markdown)


def test_without_frozen_file_shows_calibration_and_warning():
    at = run_app(frozen=None)
    assert not at.exception
    assert "Sem parâmetros congelados" in texts(at.warning)
    assert "Janela de calibração" in texts(at.caption)
    assert "Janela de desenvolvimento" not in texts(at.caption)  # 2019+ caption only with the 2019+ window


def test_approved_badge_when_all_criteria_passed():
    frozen = FrozenParams(
        frozen_at=NOW_OK, csv_sha256=HISTORY.csv_sha256, model_hash=model_hash(CFG), model=model_payload(CFG),
        approval=Approval(
            run_at=NOW_OK, window="development",
            passed={"equity_vs_bnh": True, "dd_improvement_pp": True, "equity_vs_uniform": True},
            values={"equity_vs_bnh": 1.0, "dd_improvement_pp": 20.0, "equity_vs_uniform": 1.1},
        ),
    )
    at = run_app(frozen=frozen)
    assert not at.exception
    assert "Desempenho histórico aprovado" in texts(at.success)
    assert "Janela de desenvolvimento (2019+)" in texts(at.caption)


def test_calculator_turns_percentages_into_amounts():
    at = run_app()
    at.number_input(key="calc_base_btc").set_value(1.0)
    at.number_input(key="calc_reserve_usd").set_value(1000.0)
    at.run()
    assert not at.exception
    md = texts(at.markdown)
    assert "**0.25000000 BTC**" in md  # 25% of 1 BTC
    assert "**US$ 20.00**" in md  # 2% of the 1,000 USD reserve (week 08/11/2026, ACCUMULATE)
