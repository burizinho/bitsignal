"""Command Line Interface for BitSignal."""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
import pandas as pd
import yaml
from dotenv import load_dotenv

from bitsignal.alerts.dispatcher import process_and_dispatch_alerts
from bitsignal.backtest.engine import run_backtest
from bitsignal.engine.indicators import (
    calculate_200w_sma_ratio,
    calculate_ema,
    calculate_picycle_top_ratio,
    calculate_rsi,
    calculate_sma,
    is_picycle_bottom_triggered,
)
from bitsignal.engine.normalizer import calculate_composite_score
from bitsignal.ingestion import (
    fetch_market_data,
    fetch_mempool_data,
    fetch_onchain_data,
)
from bitsignal.integrity import evaluate_system_integrity
from bitsignal.models import DailyMetrics
from bitsignal.storage.db import (
    get_latest_hysteresis_state,
    init_db,
    upsert_daily_metrics,
    upsert_daily_score,
)

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def load_config(config_path: str = "./config/config.yaml") -> dict:
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def cmd_db_init(args):
    """Initialize database tables."""
    db_path = args.db_path or os.getenv("DATABASE_PATH", "./data/bitsignal.db")
    init_db(db_path)
    print(f"[OK] BitSignal database initialized at: {db_path}")


def cmd_run_daily(args):
    """Execute complete daily monitoring pipeline."""
    db_path = args.db_path or os.getenv("DATABASE_PATH", "./data/bitsignal.db")
    dry_run = args.dry_run
    init_db(db_path)

    print("=" * 60)
    print(f"  BitSignal Daily Pipeline [{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}]")
    print("=" * 60)

    # 1. Ingestion
    print("1. Ingesting market, mining, and on-chain datasets...")
    market_snapshot = fetch_market_data()
    mining_snapshot = fetch_mempool_data()
    onchain_snapshot = fetch_onchain_data(
        dune_api_key=os.getenv("DUNE_API_KEY"),
        query_id=os.getenv("DUNE_QUERY_ID"),
    )

    date = market_snapshot.date
    daily_closes = pd.Series([c.close for c in market_snapshot.daily_candles])
    weekly_closes = pd.Series([c.close for c in market_snapshot.weekly_candles])
    latest_close = float(daily_closes.iloc[-1])

    # 2. Indicator Calculation
    print("2. Calculating technical and on-chain indicators...")
    sma_111 = float(calculate_sma(daily_closes, 111).iloc[-1]) if len(daily_closes) >= 111 else None
    sma_350 = float(calculate_sma(daily_closes, 350).iloc[-1]) if len(daily_closes) >= 350 else None
    sma_471 = float(calculate_sma(daily_closes, 471).iloc[-1]) if len(daily_closes) >= 471 else None
    ema_150 = float(calculate_ema(daily_closes, 150).iloc[-1]) if len(daily_closes) >= 150 else None

    sma_200w = float(calculate_sma(weekly_closes, 200).iloc[-1]) if len(weekly_closes) >= 200 else None
    rsi_14w = float(calculate_rsi(weekly_closes, 14).iloc[-1]) if len(weekly_closes) >= 14 else None

    picycle_spread = calculate_picycle_top_ratio(sma_111, sma_350) if sma_111 and sma_350 else None
    picycle_bottom = is_picycle_bottom_triggered(ema_150, sma_471) if ema_150 and sma_471 else False
    sma200w_ratio = calculate_200w_sma_ratio(latest_close, sma_200w) if sma_200w else None

    # Persist daily metrics
    metrics = DailyMetrics(
        date=date,
        btc_price=latest_close,
        open=market_snapshot.daily_candles[-1].open,
        high=market_snapshot.daily_candles[-1].high,
        low=market_snapshot.daily_candles[-1].low,
        volume=market_snapshot.daily_candles[-1].volume,
        sma_111=sma_111,
        sma_350=sma_350,
        sma_471=sma_471,
        ema_150=ema_150,
        sma_200w=sma_200w,
        rsi_14w=rsi_14w,
        mvrv_z=onchain_snapshot.mvrv_z,
        puell_multiple=onchain_snapshot.puell_multiple,
        hashrate=mining_snapshot.hashrate,
        hash_ribbon_status=mining_snapshot.status.value,
    )
    upsert_daily_metrics(metrics, db_path)

    # 3. Integrity and Staleness Audit
    print("3. Auditing data timestamps and circuit breaker...")
    timestamps = {
        "mvrv_z": onchain_snapshot.timestamp,
        "sma200w_ratio": int(datetime.now(timezone.utc).timestamp()),
        "puell_multiple": onchain_snapshot.timestamp,
        "picycle": int(datetime.now(timezone.utc).timestamp()),
        "weekly_rsi": int(datetime.now(timezone.utc).timestamp()),
        "hash_ribbon": int(datetime.now(timezone.utc).timestamp()),
    }
    system_status, staleness_map, missing_weight = evaluate_system_integrity(timestamps)
    print(f"   Status: {system_status.value} (Missing Weight: {missing_weight*100:.1f}%)")

    # 4. Composite Scoring
    print("4. Normalizing indicators and computing Composite Cycle Score...")
    prev_state = get_latest_hysteresis_state(db_path)
    result = calculate_composite_score(
        date=date,
        mvrv_z=onchain_snapshot.mvrv_z,
        sma200w_ratio=sma200w_ratio,
        puell_multiple=onchain_snapshot.puell_multiple,
        picycle_spread=picycle_spread,
        is_picycle_bottom=picycle_bottom,
        weekly_rsi=rsi_14w,
        hash_ribbon_status=mining_snapshot.status.value,
        system_status=system_status,
        current_hysteresis=prev_state,
        staleness_map=staleness_map,
    )
    upsert_daily_score(result, db_path)

    print("-" * 60)
    print(f"  BTC Price:            ${latest_close:,.2f}")
    print(f"  Composite Cycle Score: {result.composite_score:.2f} / 100")
    print(f"  Hysteresis State:      {result.hysteresis_state.value}")
    print("  Component Scores:")
    print(f"    - MVRV Z-Score (25%):   {result.mvrv_score:.1f}")
    print(f"    - 200w SMA Ratio (20%): {result.sma200w_score:.1f}")
    print(f"    - Puell Multiple (20%): {result.puell_score:.1f}")
    print(f"    - Pi Cycle (15%):       {result.picycle_score:.1f}")
    print(f"    - Weekly RSI (10%):     {result.rsi_score:.1f}")
    print(f"    - Hash Ribbon (10%):    {result.hashribbon_score:.1f}")
    print("-" * 60)

    # 5. Alerting
    print("5. Checking alert triggers and multi-tier hysteresis...")
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    dispatched_alert = process_and_dispatch_alerts(
        result=result,
        previous_state=prev_state,
        bot_token=bot_token,
        chat_id=chat_id,
        db_path=db_path,
        dry_run=dry_run,
    )
    if dispatched_alert:
        print(f"   [ALERT] Alert Triggered: {dispatched_alert.value} (Dry Run: {dry_run})")
    else:
        print("   [OK] No alert trigger; state stable within neutral or deadband.")

    print("=" * 60)
    print("  Daily run complete.")
    print("=" * 60)


def cmd_backtest(args):
    """Execute Phase 1.5 Historical Backtest."""
    print("Running BitSignal Phase 1.5 Historical Backtest...")
    # Fetch historical daily data via yfinance or local dataset
    try:
        import yfinance as yf
        print("Ingesting historical BTC daily data from 2012 to present...")
        ticker = yf.Ticker("BTC-USD")
        df = ticker.history(start=args.start or "2012-01-01", end=args.end or None, interval="1d")
        if df.empty:
            raise ValueError("Empty historical dataset returned.")
        df = df.reset_index().rename(columns={"Date": "date", "Close": "close", "Open": "open", "High": "high", "Low": "low", "Volume": "volume"})
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        report = run_backtest(df)
        print(report.summary())
    except Exception as exc:
        print(f"Error executing backtest: {exc}")


def cmd_ui(args):
    """Launch Streamlit dashboard."""
    app_path = os.path.join(os.path.dirname(__file__), "ui", "app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])


def main():
    parser = argparse.ArgumentParser(
        prog="bitsignal",
        description="Bitcoin Macro Cycle Sentinel CLI",
    )
    parser.add_argument("--db-path", default=None, help="Path to SQLite database")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # db-init
    subparsers.add_parser("db-init", help="Initialize SQLite tables")

    # run-daily
    p_run = subparsers.add_parser("run-daily", help="Run daily monitoring and scoring cycle")
    p_run.add_argument("--dry-run", action="store_true", help="Calculate without sending real alerts")

    # backtest
    p_bt = subparsers.add_parser("backtest", help="Execute Phase 1.5 Historical Backtest")
    p_bt.add_argument("--start", default="2012-01-01", help="Start date (YYYY-MM-DD)")
    p_bt.add_argument("--end", default=None, help="End date (YYYY-MM-DD)")

    # ui
    subparsers.add_parser("ui", help="Launch Streamlit dashboard")

    args = parser.parse_args()

    if args.command == "db-init":
        cmd_db_init(args)
    elif args.command == "run-daily":
        cmd_run_daily(args)
    elif args.command == "backtest":
        cmd_backtest(args)
    elif args.command == "ui":
        cmd_ui(args)


if __name__ == "__main__":
    main()
