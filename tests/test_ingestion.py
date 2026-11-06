"""Unit tests for the data ingestion layer."""

from unittest.mock import MagicMock
import requests
from bitsignal.ingestion import (
    fetch_binance_klines,
    fetch_mempool_data,
    fetch_onchain_data,
)
from bitsignal.models import HashRibbonState


def test_fetch_binance_klines_success():
    """Verify Binance klines parsing."""
    mock_session = MagicMock(spec=requests.Session)
    mock_response = MagicMock()
    # Mock Binance kline array: [openTime, open, high, low, close, volume, ...]
    mock_response.json.return_value = [
        [1700000000000, "65000.0", "66000.0", "64500.0", "65800.0", "1200.5"],
        [1700086400000, "65800.0", "67200.0", "65500.0", "67000.0", "1500.2"],
    ]
    mock_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_response

    candles = fetch_binance_klines(mock_session, symbol="BTCUSDT", interval="1d", limit=2)
    assert len(candles) == 2
    assert candles[0].close == 65800.0
    assert candles[1].high == 67200.0
    assert candles[1].timestamp == 1700086400000


def test_fetch_mempool_data_normal_state():
    """Verify Mempool parsing and Hash Ribbon normal state calculation."""
    mock_session = MagicMock(spec=requests.Session)
    mock_response = MagicMock()

    # Generate 65 daily records with rising hashrate (30d > 60d => NORMAL)
    hashrates = []
    base_rate = 5.0e20
    for i in range(65):
        hashrates.append({"timestamp": 1700000000 + i * 86400, "avgHashrate": base_rate + i * 1e19})

    mock_response.json.return_value = hashrates
    mock_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_response

    snapshot = fetch_mempool_data(mock_session)
    assert snapshot.status == HashRibbonState.NORMAL
    assert snapshot.hashrate_30d > snapshot.hashrate_60d


def test_fetch_mempool_data_capitulation_state():
    """Verify Hash Ribbon capitulation state calculation (30d < 60d)."""
    mock_session = MagicMock(spec=requests.Session)
    mock_response = MagicMock()

    # Generate 65 daily records with falling hashrate
    hashrates = []
    base_rate = 8.0e20
    for i in range(65):
        hashrates.append({"timestamp": 1700000000 + i * 86400, "avgHashrate": base_rate - i * 1e19})

    mock_response.json.return_value = hashrates
    mock_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_response

    snapshot = fetch_mempool_data(mock_session)
    assert snapshot.status == HashRibbonState.CAPITULATION
    assert snapshot.hashrate_30d < snapshot.hashrate_60d


def test_fetch_onchain_data_fallback():
    """Verify on-chain fallback when Dune credentials are not supplied."""
    mock_session = MagicMock(spec=requests.Session)
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_session.get.return_value = mock_response

    snapshot = fetch_onchain_data(session=mock_session)
    assert snapshot.mvrv_z is not None
    assert snapshot.puell_multiple is not None
    assert snapshot.mvrv_z > 0
    assert snapshot.puell_multiple > 0
