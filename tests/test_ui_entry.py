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


def _run_app_header(loaded_at):
    """Run app.py's module body (not as __main__) with the package marked as imported at ``loaded_at``."""
    import sys

    import bitsignal
    import bitsignal.config

    snapshot = {k: v for k, v in sys.modules.items() if k == "bitsignal" or k.startswith("bitsignal.")}
    old_config = sys.modules["bitsignal.config"]
    original = bitsignal._LOADED_AT
    if loaded_at is None:
        del bitsignal._LOADED_AT
    else:
        bitsignal._LOADED_AT = loaded_at
    try:
        runpy.run_path(str(ROOT / "bitsignal" / "ui" / "app.py"), run_name="app_header_test")
        return sys.modules.get("bitsignal.config") is old_config
    finally:
        bitsignal._LOADED_AT = original
        for k in [k for k in sys.modules if k == "bitsignal" or k.startswith("bitsignal.")]:
            del sys.modules[k]
        sys.modules.update(snapshot)


def test_stale_modules_are_reloaded_after_a_redeploy():
    """Streamlit Cloud keeps imported modules across a redeploy: a source file newer than the import
    must force a fresh import (otherwise the old config.py rejects the new config.yaml)."""
    assert _run_app_header(loaded_at=0.0) is False  # files changed after "import": reloaded


def test_unchanged_modules_are_kept():
    import time

    assert _run_app_header(loaded_at=time.time() + 3600) is True  # nothing changed: same module


def test_package_without_load_time_is_treated_as_stale():
    """The version in memory before this fix has no _LOADED_AT: it must be reloaded too."""
    assert _run_app_header(loaded_at=None) is False
