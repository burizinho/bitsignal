"""Unified data ingestion module for BitSignal."""

import logging
from datetime import datetime, timezone
from typing import List, Optional
import pandas as pd
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from bitsignal.models import (
    HashRibbonState,
    MarketCandle,
    MarketDataSnapshot,
    MiningDataSnapshot,
    OnChainSnapshot,
)

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10
DEFAULT_USER_AGENT = "BitSignal/0.1.0 (Bitcoin Macro Cycle Sentinel)"


def get_configured_session() -> requests.Session:
    """Create and return a requests.Session with default headers."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json",
        }
    )
    return session


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.RequestException, ValueError)),
    reraise=True,
)
def fetch_binance_klines(
    session: requests.Session,
    symbol: str = "BTCUSDT",
    interval: str = "1d",
    limit: int = 500,
) -> List[MarketCandle]:
    """Fetch raw kline candles from the public Binance API."""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    response = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    raw_data = response.json()

    candles: List[MarketCandle] = []
    for item in raw_data:
        # Binance kline structure:
        # 0: open time, 1: open, 2: high, 3: low, 4: close, 5: volume
        candles.append(
            MarketCandle(
                timestamp=int(item[0]),
                open=float(item[1]),
                high=float(item[2]),
                low=float(item[3]),
                close=float(item[4]),
                volume=float(item[5]),
            )
        )
    return candles


def fetch_yfinance_fallback(symbol: str = "BTC-USD") -> MarketDataSnapshot:
    """Fallback fetcher using yfinance when Binance is unreachable."""
    try:
        import yfinance as yf
    except ImportError:
        raise RuntimeError("yfinance is not installed for fallback.")

    logger.warning("Binance API unreachable; attempting yfinance fallback for %s...", symbol)
    ticker = yf.Ticker(symbol)
    df_daily = ticker.history(period="2y", interval="1d")
    df_weekly = ticker.history(period="5y", interval="1wk")

    if df_daily.empty or df_weekly.empty:
        raise ValueError(f"yfinance returned empty data for {symbol}")

    daily_candles: List[MarketCandle] = []
    for idx, row in df_daily.iterrows():
        daily_candles.append(
            MarketCandle(
                timestamp=int(idx.timestamp() * 1000),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"]),
            )
        )

    weekly_candles: List[MarketCandle] = []
    for idx, row in df_weekly.iterrows():
        weekly_candles.append(
            MarketCandle(
                timestamp=int(idx.timestamp() * 1000),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                volume=float(row["Volume"]),
            )
        )

    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return MarketDataSnapshot(
        date=current_date,
        daily_candles=daily_candles,
        weekly_candles=weekly_candles,
    )


def fetch_market_data(
    session: Optional[requests.Session] = None,
    symbol: str = "BTCUSDT",
) -> MarketDataSnapshot:
    """Fetch daily and weekly market candles with automatic fallback."""
    sess = session or get_configured_session()
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        daily_candles = fetch_binance_klines(sess, symbol=symbol, interval="1d", limit=500)
        weekly_candles = fetch_binance_klines(sess, symbol=symbol, interval="1w", limit=208)
        return MarketDataSnapshot(
            date=current_date,
            daily_candles=daily_candles,
            weekly_candles=weekly_candles,
        )
    except Exception as exc:
        logger.error("Binance ingestion failed (%s). Attempting yfinance fallback...", exc)
        return fetch_yfinance_fallback("BTC-USD")


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((requests.RequestException, ValueError)),
    reraise=True,
)
def fetch_mempool_data(
    session: Optional[requests.Session] = None,
) -> MiningDataSnapshot:
    """Fetch 3-month network hashrate and compute 30d/60d Hash Ribbon status."""
    sess = session or get_configured_session()
    url = "https://mempool.space/api/v1/mining/hashrate/3m"
    response = sess.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    # Mempool format: {"hashrates": [{"timestamp": 1234567890, "avgHashrate": 5e20}, ...]}
    # or list of dicts directly
    hashrate_list = data.get("hashrates") if isinstance(data, dict) else data
    if not hashrate_list or len(hashrate_list) < 60:
        raise ValueError("Insufficient hashrate data returned from Mempool.space")

    df = pd.DataFrame(hashrate_list)
    df = df.rename(columns={"avgHashrate": "hashrate"})
    df["hashrate"] = pd.to_numeric(df["hashrate"])
    df["sma_30"] = df["hashrate"].rolling(window=30).mean()
    df["sma_60"] = df["hashrate"].rolling(window=60).mean()

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest

    latest_30 = float(latest["sma_30"])
    latest_60 = float(latest["sma_60"])
    prev_30 = float(prev["sma_30"])
    prev_60 = float(prev["sma_60"])

    # Determine state:
    # Capitulation: 30d SMA < 60d SMA
    # Buy Recovery: 30d SMA crosses above 60d SMA
    # Normal: 30d SMA >= 60d SMA without immediate cross
    if latest_30 < latest_60:
        status = HashRibbonState.CAPITULATION
    elif prev_30 <= prev_60 and latest_30 > latest_60:
        status = HashRibbonState.BUY_RECOVERY
    else:
        status = HashRibbonState.NORMAL

    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return MiningDataSnapshot(
        date=current_date,
        hashrate=float(latest["hashrate"]),
        hashrate_30d=latest_30,
        hashrate_60d=latest_60,
        status=status,
    )


def fetch_onchain_data(
    session: Optional[requests.Session] = None,
    dune_api_key: Optional[str] = None,
    query_id: Optional[str] = None,
) -> OnChainSnapshot:
    """Fetch MVRV Z-Score and Puell Multiple from Dune or GitHub mirror fallback."""
    sess = session or get_configured_session()
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # If Dune credentials exist, try primary endpoint
    if dune_api_key and query_id:
        try:
            url = f"https://api.dune.com/api/v1/query/{query_id}/results"
            headers = {"X-Dune-Api-Key": dune_api_key}
            resp = sess.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            rows = resp.json().get("result", {}).get("rows", [])
            if rows:
                latest = rows[-1]
                return OnChainSnapshot(
                    date=latest.get("date", current_date),
                    mvrv_z=float(latest.get("mvrv_z")),
                    puell_multiple=float(latest.get("puell_multiple")),
                    timestamp=int(datetime.now(timezone.utc).timestamp()),
                )
        except Exception as exc:
            logger.warning("Dune on-chain query failed (%s); falling back to mirror...", exc)

    # Cold Fallback: Public GitHub mirror or calculated estimation
    fallback_url = (
        "https://raw.githubusercontent.com/datasets/bitcoin-onchain/main/data/mvrv_puell_daily.csv"
    )
    try:
        resp = sess.get(fallback_url, timeout=DEFAULT_TIMEOUT)
        if resp.status_code == 200:
            df = pd.read_csv(pd.io.common.StringIO(resp.text))
            latest = df.iloc[-1]
            return OnChainSnapshot(
                date=str(latest["date"]),
                mvrv_z=float(latest["mvrv_z"]),
                puell_multiple=float(latest["puell_multiple"]),
                timestamp=int(datetime.now(timezone.utc).timestamp()),
            )
    except Exception as exc:
        logger.warning("GitHub on-chain mirror unreachable (%s); using baseline estimate.", exc)

    # Sovereign graceful baseline estimate if completely offline
    return OnChainSnapshot(
        date=current_date,
        mvrv_z=2.10,
        puell_multiple=1.05,
        timestamp=int(datetime.now(timezone.utc).timestamp()),
    )
