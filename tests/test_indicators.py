"""Unit tests for mathematical indicator calculations."""

import numpy as np
import pandas as pd
from bitsignal.engine.indicators import (
    calculate_200w_sma_ratio,
    calculate_ema,
    calculate_picycle_top_ratio,
    calculate_rsi,
    calculate_sma,
    is_picycle_bottom_triggered,
)


def test_calculate_sma():
    """Verify Simple Moving Average."""
    series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    sma3 = calculate_sma(series, window=3)
    assert np.isnan(sma3.iloc[0])
    assert np.isnan(sma3.iloc[1])
    assert sma3.iloc[2] == 20.0
    assert sma3.iloc[4] == 40.0


def test_calculate_ema():
    """Verify Exponential Moving Average."""
    series = pd.Series([10.0, 20.0, 30.0, 40.0, 50.0])
    ema = calculate_ema(series, span=3)
    assert len(ema) == 5
    assert ema.iloc[-1] > ema.iloc[0]


def test_calculate_rsi():
    """Verify RSI calculation."""
    # Constantly rising prices -> RSI should approach 100
    rising = pd.Series([float(i) for i in range(1, 30)])
    rsi_rising = calculate_rsi(rising, period=14)
    assert rsi_rising.iloc[-1] > 90.0

    # Constantly falling prices -> RSI should approach 0
    falling = pd.Series([float(30 - i) for i in range(1, 30)])
    rsi_falling = calculate_rsi(falling, period=14)
    assert rsi_falling.iloc[-1] < 10.0


def test_picycle_top_and_bottom():
    """Verify Pi Cycle top ratio and bottom convergence trigger."""
    # Top ratio: SMA 111 / (2 * SMA 350)
    ratio = calculate_picycle_top_ratio(100.0, 50.0)
    assert ratio == 1.0  # Top cross threshold reached

    # Bottom convergence: EMA 150 * 0.745 <= SMA 471
    assert is_picycle_bottom_triggered(100.0, 80.0) is True  # 74.5 <= 80.0
    assert is_picycle_bottom_triggered(100.0, 70.0) is False  # 74.5 > 70.0


def test_calculate_200w_sma_ratio():
    """Verify Price / 200w SMA ratio."""
    ratio = calculate_200w_sma_ratio(70000.0, 35000.0)
    assert ratio == 2.0
