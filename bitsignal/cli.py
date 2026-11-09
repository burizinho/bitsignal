"""Command Line Interface for BitSignal."""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
import pandas as pd
import yaml
from dotenv import load_dotenv

from bitsignal.alerts.dispatcher import process_and_dispatch_alerts, send_strategy_runbook
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
    get_executed_stages,
    get_latest_hysteresis_state,
    get_portfolio_summary,
    init_db,
    record_portfolio_transaction,
    upsert_daily_metrics,
    upsert_daily_score,
)
from bitsignal.strategy.models import (
    PortfolioTransaction,
    StageType,
    TransactionType,
)
from bitsignal.strategy.tax_br import (
    compute_darf_for_month,
    get_monthly_accumulated_alienation,
)
from bitsignal.strategy.weekly_evaluator import evaluate_weekly_strategy

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

    # 6. Weekly Execution Strategy Audit (Sundays 21:00 BRT / Mondays 00:00 UTC or 1st of month)
    now_utc = datetime.now(timezone.utc)
    config = load_config()
    if now_utc.weekday() == 0 or now_utc.day == 1:
        print("6. Auditing weekly national execution strategy (Domingos 21h BRT / Split)...")
        summary = get_portfolio_summary(db_path)
        runbook = evaluate_weekly_strategy(
            db_path=db_path,
            config=config,
            current_time=now_utc,
            weekly_closes=weekly_closes,
            spot_price_usd=latest_close,
            mvrv_z=onchain_snapshot.mvrv_z,
        )
        if runbook:
            print(f"   [STRATEGY TRIGGER] Stage: {runbook.stage.value} ({runbook.action_type.value})")
            print(f"   Order Collar Price: R$ {runbook.collar_price_brl:,.2f} | Amount: {runbook.amount_btc:.8f} BTC (R$ {runbook.amount_brl:,.2f})")
            print(f"   Tax Status: {runbook.tax_plan.status.value} (DARF: R$ {runbook.tax_plan.darf_amount:,.2f})")
            if not dry_run:
                sent = send_strategy_runbook(
                    runbook=runbook,
                    bot_token=bot_token,
                    chat_id=chat_id,
                    current_cmp_brl=summary.current_cmp_brl,
                    db_path=db_path,
                    dry_run=False,
                )
                print(f"   [STRATEGY PUSH] Runbook dispatched to Telegram: {sent}")
        else:
            print("   [OK] Weekly strategy evaluated: no execution threshold triggered.")

    print("=" * 60)
    print("  Daily run complete.")
    print("=" * 60)


def cmd_backtest(args):
    """S5: backtest of the default model against the two Q1 benchmarks, offline (frozen CSV).

    Default window: calibration (no 2019+ criteria). ``--window development`` needs the frozen
    parameters file with a matching model_hash (S6).
    """
    from bitsignal.backtest.report import to_text
    from bitsignal.config import load_config, load_frozen_params
    from bitsignal.data.history import load_frozen_history

    cfg = load_config()
    frozen = load_frozen_params(cfg.backtest.frozen_params)
    history = load_frozen_history(cfg.data.csv_path)
    try:
        report = run_backtest(
            history, cfg, window=args.window, frozen=frozen, sensitivities=not args.no_sensitivities
        )
    except ValueError as exc:
        print(f"[ERRO] {exc}")
        sys.exit(1)
    print(to_text(report))
    if args.window == "development" and frozen is not None and frozen.approval is not None:
        a = frozen.approval
        print("")
        print(f"Approval gravado no S6 ({a.run_at:%Y-%m-%d}): {a.passed.model_dump()} {a.values.model_dump()}")
        print("O recálculo acima é só exibição; o resultado oficial é o gravado.")


def cmd_ui(args):
    """Launch Streamlit dashboard through the same entrypoint used by Streamlit Cloud."""
    app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "streamlit_app.py")
    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])


def cmd_fetch_history(args):
    """S3: download CoinMetrics history and write the frozen CSV + meta (offline afterwards)."""
    from bitsignal.config import load_config, repo_path
    from bitsignal.data.coinmetrics import check_catalog, fetch_coinmetrics
    from bitsignal.data.history import compare_histories, from_frame, load_frozen_history, write_frozen_history

    cfg = load_config()
    out = args.out or cfg.data.csv_path

    catalog = check_catalog()
    missing = [m for m, ok in catalog.items() if not ok]
    if missing:
        print(f"[ERRO] Métricas fora do plano Community da CoinMetrics: {missing}")
        sys.exit(1)

    df = fetch_coinmetrics()
    live = from_frame(df, source="coinmetrics_live")

    previous = repo_path(out)
    if previous.exists():
        diffs = compare_histories(live, load_frozen_history(previous))
        if diffs.empty:
            print("[OK] Histórico ao vivo igual ao CSV anterior na janela comum.")
        else:
            print(f"[AVISO] {len(diffs)} diferença(s) contra o CSV anterior (revisão da CoinMetrics?):")
            print(diffs.head(20).to_string(index=False))

    meta = write_frozen_history(df, out)
    print(f"[OK] {meta['rows']} linhas gravadas em {out} (as_of {meta['last_date']}, sha256 {meta['sha256'][:12]}…)")
    if meta["gaps"]:
        for col, dates in meta["gaps"].items():
            print(f"     lacuna em {col}: {len(dates)} dia(s), primeiro {dates[0]}")


def cmd_strategy_status(args):
    """Display current portfolio balance, CMP, and monthly tax alienation status."""
    db_path = args.db_path or os.getenv("DATABASE_PATH", "./data/bitsignal.db")
    init_db(db_path)

    summary = get_portfolio_summary(db_path)
    stages = get_executed_stages(db_path)
    now_str = datetime.now(timezone.utc).strftime("%Y-%m")
    monthly_alienation = get_monthly_accumulated_alienation(month_year=now_str, db_path=db_path)
    exemption_remaining = max(0.0, 35000.0 - monthly_alienation)

    print("=" * 65)
    print("  CARTEIRA ESTRATÉGICA BITCOIN — STATUS OPERACIONAL & FISCAL")
    print("=" * 65)
    print(f"  Saldo Atual em Custódia:    {summary.current_btc_balance:.8f} BTC")
    print(f"  Custo Médio Ponderado (CMP): R$ {summary.current_cmp_brl:,.2f} / BTC")
    print(f"  Total Aportado Histórico:   R$ {summary.total_invested_brl:,.2f}")
    print(f"  Total Retirado Histórico:   R$ {summary.total_withdrawn_brl:,.2f}")
    print(f"  Total Taxas Pagas:          R$ {summary.total_fees_brl:,.2f}")
    print(f"  Degraus Já Executados:      {', '.join(stages) if stages else 'Nenhum'}")
    print("-" * 65)
    print(f"  Alienação no Mês Civil ({now_str}): R$ {monthly_alienation:,.2f}")
    print("  Teto de Isenção RFB:                 R$ 35,000.00")
    print(f"  Margem Isenta Restante:              R$ {exemption_remaining:,.2f}")
    print(f"  Enquadramento Tributário:            {'100% ISENTO' if monthly_alienation <= 35000.0 else 'TRIBUTÁVEL (15% GCAP)'}")
    print("=" * 65)


def cmd_strategy_record_tx(args):
    """Record a manual execution in portfolio_transactions ledger."""
    db_path = args.db_path or os.getenv("DATABASE_PATH", "./data/bitsignal.db")
    init_db(db_path)

    tx_type = TransactionType(args.type.upper())
    stage = StageType(args.stage.upper())
    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    price_usd = args.price_usd
    if price_usd is None:
        price_usd = round(args.price_brl / 5.80, 2)

    tx = PortfolioTransaction(
        date=date_str,
        tx_type=tx_type,
        stage=stage,
        amount_btc=args.btc,
        price_brl=args.price_brl,
        price_usd=price_usd,
        fee_brl=args.fee_brl,
        exchange=args.exchange,
        tx_hash=args.tx_hash,
        notes=args.notes,
    )

    tx_id = record_portfolio_transaction(tx, db_path=db_path)
    summary = get_portfolio_summary(db_path)

    print(f"[OK] Transação registrada com sucesso (ID: {tx_id})")
    print(f"     Tipo: {tx_type.value} | Degrau: {stage.value} | Qtd: {args.btc:.8f} BTC | Preço: R$ {args.price_brl:,.2f}")
    print(f"     Novo Saldo: {summary.current_btc_balance:.8f} BTC | Novo CMP: R$ {summary.current_cmp_brl:,.2f} / BTC")


def cmd_strategy_eval(args):
    """Evaluate strategy triggers right now."""
    db_path = args.db_path or os.getenv("DATABASE_PATH", "./data/bitsignal.db")
    init_db(db_path)
    config = load_config()

    print("Avaliando gatilhos de estratégia e trailing stops...")
    summary = get_portfolio_summary(db_path)
    runbook = evaluate_weekly_strategy(
        db_path=db_path,
        config=config,
        spot_price_usd=args.spot_usd,
        spot_price_brl=args.spot_brl,
    )

    if runbook:
        print("=" * 65)
        print(f"  [GATILHO ACIONADO]: {runbook.action_type.value} {runbook.stage.value}")
        print(f"  Cotação BTC/BRL: R$ {runbook.price_brl:,.2f} | USD: ${runbook.price_usd:,.2f}")
        print(f"  Ordem Limitada:  R$ {runbook.collar_price_brl:,.2f}")
        print(f"  Volume:          {runbook.amount_btc:.8f} BTC (R$ {runbook.amount_brl:,.2f})")
        print(f"  Status Fiscal:   {runbook.tax_plan.status.value}")
        print(f"  DARF Estimada:   R$ {runbook.tax_plan.darf_amount:,.2f}")
        print("  Instruções de Execução:")
        for idx, inst in enumerate(runbook.instructions, 1):
            print(f"    {idx}. {inst}")
        print("=" * 65)

        if not args.dry_run:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("TELEGRAM_CHAT_ID")
            sent = send_strategy_runbook(
                runbook=runbook,
                bot_token=bot_token,
                chat_id=chat_id,
                current_cmp_brl=summary.current_cmp_brl,
                db_path=db_path,
                dry_run=False,
            )
            print(f"  Alerta despachado no Telegram: {sent}")
    else:
        print("[OK] Condições normais: nenhum gatilho de compra, venda ou trailing stop acionado.")


def cmd_strategy_tax_report(args):
    """Compute and display monthly DARF tax report."""
    db_path = args.db_path or os.getenv("DATABASE_PATH", "./data/bitsignal.db")
    init_db(db_path)
    month = args.month or datetime.now(timezone.utc).strftime("%Y-%m")

    report = compute_darf_for_month(month_year=month, db_path=db_path)

    print("=" * 65)
    print(f"  RELATÓRIO FISCAL RFB (IN 1.888 / GCAP) — {month}")
    print("=" * 65)
    print(f"  Total de Alienações no Mês: R$ {report['total_alienated_brl']:,.2f}")
    print(f"  Ganho de Capital Líquido:   R$ {report['total_gain_brl']:,.2f}")
    status_str = "ISENTO (0% de imposto)" if report['is_exempt'] else "TRIBUTÁVEL (15% GCAP)"
    print(f"  Status de Isenção:          {status_str}")
    print(f"  Imposto Devido (DARF 15%):  R$ {report['darf_due_brl']:,.2f}")
    if not report['is_exempt']:
        print("  Código da Receita:          4600 (Ganhos de Capital na Alienação de Criptoativos)")
        print("  Data Limite de Pagamento:   Último dia útil do mês seguinte")
    print("=" * 65)


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
    p_bt = subparsers.add_parser("backtest", help="Backtest the default model vs Q1 benchmarks (offline)")
    p_bt.add_argument("--window", choices=["calibration", "development"], default="calibration",
                      help="calibration (default, no 2019+ criteria) or development (needs frozen params)")
    p_bt.add_argument("--no-sensitivities", action="store_true", help="Skip the sensitivities")

    # ui
    subparsers.add_parser("ui", help="Launch Streamlit dashboard")

    # fetch-history (S3)
    p_fh = subparsers.add_parser("fetch-history", help="Download CoinMetrics history into the frozen CSV")
    p_fh.add_argument("--out", default=None, help="CSV path (default: data.csv_path from config)")

    # strategy-status
    subparsers.add_parser("strategy-status", help="Show current portfolio balance, CMP, and tax status")

    # strategy-record-tx
    p_rec = subparsers.add_parser("strategy-record-tx", help="Record a portfolio buy/sell transaction")
    p_rec.add_argument("--type", required=True, choices=["BUY", "SELL", "buy", "sell"], help="Transaction type (BUY or SELL)")
    p_rec.add_argument("--stage", required=True, help="Strategy stage (e.g. C0, C1, V1, STOP_1, SPLIT_PART_2)")
    p_rec.add_argument("--btc", required=True, type=float, help="Amount in BTC")
    p_rec.add_argument("--price-brl", required=True, type=float, help="Execution price in BRL")
    p_rec.add_argument("--price-usd", type=float, default=None, help="Spot price in USD at execution")
    p_rec.add_argument("--fee-brl", type=float, default=0.0, help="Brokerage and network fee in BRL")
    p_rec.add_argument("--exchange", default="Bipa", help="National exchange name (default: Bipa)")
    p_rec.add_argument("--tx-hash", default=None, help="On-chain transaction hash")
    p_rec.add_argument("--notes", default=None, help="Operational execution notes")
    p_rec.add_argument("--date", default=None, help="Execution date ISO format")

    # strategy-eval
    p_eval = subparsers.add_parser("strategy-eval", help="Evaluate weekly strategy and trailing stops")
    p_eval.add_argument("--spot-usd", type=float, default=None, help="Override spot price USD")
    p_eval.add_argument("--spot-brl", type=float, default=None, help="Override spot price BRL")
    p_eval.add_argument("--dry-run", action="store_true", help="Do not dispatch alert to Telegram")

    # strategy-tax-report
    p_tax = subparsers.add_parser("strategy-tax-report", help="Generate monthly RFB DARF tax report")
    p_tax.add_argument("--month", default=None, help="Month in format YYYY-MM (default: current month)")

    args = parser.parse_args()

    if args.command == "db-init":
        cmd_db_init(args)
    elif args.command == "run-daily":
        cmd_run_daily(args)
    elif args.command == "backtest":
        cmd_backtest(args)
    elif args.command == "ui":
        cmd_ui(args)
    elif args.command == "fetch-history":
        cmd_fetch_history(args)
    elif args.command == "strategy-status":
        cmd_strategy_status(args)
    elif args.command == "strategy-record-tx":
        cmd_strategy_record_tx(args)
    elif args.command == "strategy-eval":
        cmd_strategy_eval(args)
    elif args.command == "strategy-tax-report":
        cmd_strategy_tax_report(args)


if __name__ == "__main__":
    main()
