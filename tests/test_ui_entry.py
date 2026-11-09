"""S0: entrypoint do painel e correção da página em branco (Q8)."""

import argparse
import os
import runpy
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "streamlit_app.py"


def test_streamlit_app_calls_main_on_every_execution():
    import bitsignal.ui.app as app

    with mock.patch.object(app, "main") as fake_main:
        runpy.run_path(str(ENTRY), run_name="__main__")
        runpy.run_path(str(ENTRY), run_name="__main__")

    assert fake_main.call_count == 2


def test_cmd_ui_runs_streamlit_app_entrypoint():
    from bitsignal import cli

    with mock.patch.object(cli.subprocess, "run") as fake_run:
        cli.cmd_ui(argparse.Namespace())

    cmd = fake_run.call_args.args[0]
    assert cmd[1:4] == ["-m", "streamlit", "run"]
    assert Path(cmd[4]).resolve() == ENTRY


def test_rerun_keeps_rendering_page():
    """Regressão da Q8: no rerun (clique em qualquer controle) a página não pode ficar em branco."""
    pytest.importorskip("streamlit")
    from datetime import datetime, timezone

    from streamlit.testing.v1 import AppTest

    import bitsignal.ui.app as app
    from bitsignal.config import load_config
    from bitsignal.data.history import load_frozen_history

    history = load_frozen_history(load_config().data.csv_path)
    now = datetime(2026, 11, 9, 12, tzinfo=timezone.utc)
    old_cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        with mock.patch.object(app, "load_history", lambda: history), \
                mock.patch.object(app, "now_utc", lambda: now), \
                mock.patch.object(app, "cached_spot", lambda: None):
            at = AppTest.from_file(str(ENTRY), default_timeout=120).run()
            first_titles = [t.value for t in at.title]
            first_md = [m.value for m in at.markdown]
            at.run()
            rerun_titles = [t.value for t in at.title]
            rerun_md = [m.value for m in at.markdown]
    finally:
        os.chdir(old_cwd)

    assert not at.exception
    assert first_titles and rerun_titles == first_titles
    assert any("Semana fechada" in m for m in first_md)
    assert any("Semana fechada" in m for m in rerun_md)


def test_app_py_as_main_file_renders_page():
    """Cloud's main file can be bitsignal/ui/app.py itself: running it directly must render."""
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    old_cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        # No network: the page title must render before any data is fetched.
        with mock.patch("bitsignal.data.coinmetrics.fetch_coinmetrics", side_effect=AssertionError("network")):
            at = AppTest.from_file(str(ROOT / "bitsignal" / "ui" / "app.py"), default_timeout=120)
            at.run()
    finally:
        os.chdir(old_cwd)

    assert [t.value for t in at.title], "running app.py directly rendered nothing"
