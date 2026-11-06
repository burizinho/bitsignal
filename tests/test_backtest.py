"""Unit tests for the historical backtesting engine."""

import pandas as pd
from bitsignal.backtest.engine import run_backtest


def test_run_backtest_synthetic():
    """Verify backtesting engine executes without error across multi-cycle synthetic series."""
    dates = pd.date_range("2020-01-01", periods=1500, freq="D").strftime("%Y-%m-%d").tolist()

    # Generate synthetic price series with parabolic top in middle and bear crash later
    prices = []
    base = 10000.0
    for i in range(1500):
        if i < 400:
            base *= 1.004  # expansion
        elif i < 500:
            base *= 1.015  # parabolic top
        elif i < 900:
            base *= 0.995  # bear capitulation
        else:
            base *= 1.002  # recovery
        prices.append(base)

    df_synth = pd.DataFrame(
        {
            "date": dates,
            "close": prices,
            "open": prices,
            "high": prices,
            "low": prices,
            "volume": [1000.0] * 1500,
        }
    )

    report = run_backtest(df_synth)
    assert report is not None
    assert len(report.df_results) == 1500
    assert "composite_score" in report.df_results.columns
    assert "hysteresis_state" in report.df_results.columns

    summary_text = report.summary()
    assert "BITSIGNAL PHASE 1.5 BACKTEST VALIDATION REPORT" in summary_text
    assert "Drawdown Reduction:" in summary_text
