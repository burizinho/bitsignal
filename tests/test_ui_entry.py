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
    from streamlit.testing.v1 import AppTest

    import bitsignal.ui.app as app

    old_cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        # Usa o SQLite versionado sem disparar o pipeline de rede.
        with mock.patch.object(app, "ensure_data_available", app.load_data):
            at = AppTest.from_file(str(ENTRY), default_timeout=60).run()
            first_titles = [t.value for t in at.title]
            first_warnings = [w.value for w in at.warning]
            at.run()
            rerun_titles = [t.value for t in at.title]
            rerun_warnings = [w.value for w in at.warning]
    finally:
        os.chdir(old_cwd)

    assert not at.exception
    assert first_titles and rerun_titles == first_titles
    assert app.OLD_PANEL_WARNING in first_warnings
    assert app.OLD_PANEL_WARNING in rerun_warnings
