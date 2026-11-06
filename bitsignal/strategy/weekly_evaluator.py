"""Weekly strategy evaluator and orchestration engine for national Bitcoin execution."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
import pandas as pd
import requests

from bitsignal.storage.db import (
    get_executed_stages,
    get_portfolio_summary,
    get_portfolio_transactions,
)
from bitsignal.strategy.models import (
    StageType,
    StrategyPhase,
    StrategyRunbook,
    TaxExecutionPlan,
    TaxStatus,
    TransactionType,
)
from bitsignal.strategy.national_dca import evaluate_cycle_stage
from bitsignal.strategy.tax_br import evaluate_tax_strategy, get_monthly_accumulated_alienation
from bitsignal.strategy.trailing_stops import compute_weekly_indicators, evaluate_trailing_stops

logger = logging.getLogger(__name__)


def fetch_btc_brl_spot(timeout: int = 5) -> Optional[float]:
    """Fetch current BTC/BRL spot price from Binance, with error suppression."""
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCBRL"
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return float(resp.json().get("price", 0.0))
    except Exception as exc:
        logger.debug("Failed to fetch live BTC/BRL spot: %s", exc)
    return None


def fetch_usd_brl_rate(timeout: int = 5) -> float:
    """Fetch live USD/BRL exchange rate, fallback to conservative default."""
    try:
        url = "https://economia.awesomeapi.com.br/last/USD-BRL"
        resp = requests.get(url, timeout=timeout)
        if resp.status_code == 200:
            return float(resp.json()["USDBRL"]["bid"])
    except Exception as exc:
        logger.debug("Failed to fetch live USD/BRL rate: %s", exc)
    return 5.80


def check_pending_split_part2(
    db_path: str,
    current_date_str: str,
    price_brl: float,
    price_usd: float,
    exchange: str = "Bipa",
    bank_night_limit_brl: float = 5000.0,
) -> Optional[StrategyRunbook]:
    """Check if there is an unexecuted second tranche from a prior month-end split."""
    txs = get_portfolio_transactions(db_path=db_path, limit=20)
    if not txs:
        return None

    # Find the most recent SELL
    latest_sell = None
    for tx in txs:
        if tx.tx_type == TransactionType.SELL:
            latest_sell = tx
            break

    if not latest_sell:
        return None

    # Check if latest SELL notes indicate a split intermensal
    notes = latest_sell.notes or ""
    if "Split intermensal" not in notes:
        return None

    # Check if a SPLIT_PART_2 has already been executed after this sale
    for tx in txs:
        if tx.stage == StageType.SPLIT_PART_2 and tx.date >= latest_sell.date:
            return None  # Already fulfilled

    summary = get_portfolio_summary(db_path)
    if summary.current_btc_balance <= 0.0001:
        return None

    part2_btc = min(summary.current_btc_balance, round(35000.0 / price_brl, 8))
    part2_brl = round(part2_btc * price_brl, 2)
    collar_price = round(price_brl * 0.997, 2)
    nocturnal_warning = part2_brl > bank_night_limit_brl

    tax_plan = TaxExecutionPlan(
        action="SELL_FULL",
        status=TaxStatus.EXEMPT,
        darf_amount=0.0,
        gross_gain_brl=max(0.0, part2_brl - (part2_btc * summary.current_cmp_brl)),
        notes="Segunda parcela de split intermensal executada no 1º dia útil do mês seguinte (isenta)",
    )

    instructions = [
        f"Custódia: Transfira exatamente {part2_btc:.8f} BTC da sua cold wallet para a corretora {exchange}.",
        f"Ordem: Abra ordem de venda limitada no par BTC/BRL a R$ {collar_price:,.2f} (collar de 0,3% para evitar slippage). Valor estimado a receber: R$ {part2_brl:,.2f}.",
    ]
    if nocturnal_warning:
        instructions.append(
            f"Protocolo Noturno de PIX: Como o valor (R$ {part2_brl:,.2f}) excede o limite noturno (R$ {bank_night_limit_brl:,.2f}), transfira até R$ {bank_night_limit_brl:,.2f} imediatamente e agende R$ {part2_brl - bank_night_limit_brl:,.2f} para amanhã às 06h01 BRT."
        )
    else:
        instructions.append(
            f"Saque: Efetue saque via PIX de R$ {part2_brl:,.2f} para sua conta corrente titular."
        )
    instructions.append("Destino do Caixa: Aplicar recursos em CDB de liquidez diária com resgate 24/7 (100% CDI).")

    return StrategyRunbook(
        stage=StageType.SPLIT_PART_2,
        date=current_date_str,
        price_usd=price_usd,
        price_brl=price_brl,
        amount_btc=part2_btc,
        amount_brl=part2_brl,
        tax_plan=tax_plan,
        action_type=TransactionType.SELL,
        order_type="LIMIT",
        collar_price_brl=collar_price,
        nocturnal_pix_warning=nocturnal_warning,
        instructions=instructions,
    )


def evaluate_weekly_strategy(
    db_path: str = "./data/bitsignal.db",
    config: Optional[Dict[str, Any]] = None,
    current_time: Optional[datetime] = None,
    weekly_closes: Optional[pd.Series] = None,
    spot_price_usd: Optional[float] = None,
    spot_price_brl: Optional[float] = None,
    mvrv_z: Optional[float] = None,
) -> Optional[StrategyRunbook]:
    """Orchestrate weekly cycle evaluation, trailing stops, and national tax runbook generation."""
    now = current_time or datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    cfg = config or {}
    strat_cfg = cfg.get("strategy", {})
    cycle_ath_usd = float(strat_cfg.get("cycle_ath_usd", 126000.0))
    total_reserve_brl = float(strat_cfg.get("total_reserve_brl", 100000.0))
    bank_night_limit_brl = float(strat_cfg.get("bank_night_limit_brl", 5000.0))
    default_exchange = strat_cfg.get("default_exchange", "Bipa")
    moonbag_pct = float(strat_cfg.get("moonbag_pct", 0.20))

    # Resolve spot prices and FX rate
    if spot_price_usd is None:
        if weekly_closes is not None and not weekly_closes.empty:
            spot_price_usd = float(weekly_closes.iloc[-1])
        else:
            spot_price_usd = 95000.0

    if spot_price_brl is None:
        live_brl = fetch_btc_brl_spot()
        if live_brl:
            spot_price_brl = live_brl
        else:
            fx = fetch_usd_brl_rate()
            spot_price_brl = round(spot_price_usd * fx, 2)

    # 1. Check if Day 1 month pending split tranche needs execution
    if now.day == 1:
        pending_split_runbook = check_pending_split_part2(
            db_path=db_path,
            current_date_str=date_str,
            price_brl=spot_price_brl,
            price_usd=spot_price_usd,
            exchange=default_exchange,
            bank_night_limit_brl=bank_night_limit_brl,
        )
        if pending_split_runbook:
            return pending_split_runbook

    # Load current portfolio state
    summary = get_portfolio_summary(db_path)
    executed_stages = set(get_executed_stages(db_path))

    ema_21w = None
    sma_50w = None
    if weekly_closes is not None and len(weekly_closes) >= 50:
        ema_21w, sma_50w = compute_weekly_indicators(weekly_closes)

    # 2. Evaluate Trailing Stops on Weekly Closes
    if weekly_closes is not None and len(weekly_closes) >= 50 and summary.current_btc_balance > 0.0001:
        latest_weekly_close = float(weekly_closes.iloc[-1])
        stop_stage = evaluate_trailing_stops(
            weekly_close_price=latest_weekly_close,
            ema_21w=ema_21w,
            sma_50w=sma_50w,
            already_executed_stops=list(executed_stages),
        )

        if stop_stage:
            if stop_stage == StageType.STOP_1:
                btc_to_sell = round(summary.current_btc_balance * 0.50, 8)
            else:  # STOP_2
                btc_to_sell = round(max(0.0, summary.current_btc_balance * (1.0 - moonbag_pct)), 8)

            gross_sale_brl = round(btc_to_sell * spot_price_brl, 2)
            collar_price = round(spot_price_brl * 0.997, 2)
            monthly_accum = get_monthly_accumulated_alienation(month_year=date_str[:7], db_path=db_path)

            tax_plan = evaluate_tax_strategy(
                alienation_brl=gross_sale_brl,
                quantity_btc=btc_to_sell,
                current_cmp_brl=summary.current_cmp_brl,
                month_accumulated_brl=monthly_accum,
                signal_date=now,
            )

            actual_btc = tax_plan.part1_btc if tax_plan.part1_btc else btc_to_sell
            actual_brl = tax_plan.part1_now_brl if tax_plan.part1_now_brl else gross_sale_brl
            nocturnal_warning = actual_brl > bank_night_limit_brl

            instructions = [
                f"Custódia: Transfira exatamente {actual_btc:.8f} BTC da sua cold wallet para a corretora {default_exchange}.",
                f"Ordem: Abra ordem de venda limitada no par BTC/BRL a R$ {collar_price:,.2f} (collar de 0,3% para evitar slippage). Valor estimado a receber: R$ {actual_brl:,.2f}.",
            ]
            if nocturnal_warning:
                instructions.append(
                    f"Protocolo Noturno de PIX: Como o valor (R$ {actual_brl:,.2f}) excede o limite noturno bancário (R$ {bank_night_limit_brl:,.2f}), transfira até R$ {bank_night_limit_brl:,.2f} imediatamente e agende R$ {actual_brl - bank_night_limit_brl:,.2f} para amanhã às 06h01 BRT."
                )
            else:
                instructions.append(
                    f"Saque: Efetue saque via PIX de R$ {actual_brl:,.2f} para sua conta corrente titular."
                )
            instructions.append("Destino do Caixa: Aplicar recursos em CDB de liquidez diária com resgate 24/7 (100% CDI).")

            return StrategyRunbook(
                stage=stop_stage,
                date=date_str,
                price_usd=spot_price_usd,
                price_brl=spot_price_brl,
                amount_btc=actual_btc,
                amount_brl=actual_brl,
                tax_plan=tax_plan,
                action_type=TransactionType.SELL,
                order_type="LIMIT",
                collar_price_brl=collar_price,
                nocturnal_pix_warning=nocturnal_warning,
                instructions=instructions,
            )

    # 3. Determine active phase: DISTRIBUTION if price > ATH or V stage executed, else ACCUMULATION
    has_distribution_stage = any(s in executed_stages for s in ["V1", "V2", "V3", "V4", "V5"])
    if (spot_price_usd >= cycle_ath_usd or has_distribution_stage) and summary.current_btc_balance > 0.0001:
        active_phase = StrategyPhase.DISTRIBUTION
    else:
        active_phase = StrategyPhase.ACCUMULATION

    cycle_trigger = evaluate_cycle_stage(
        price_usd=spot_price_usd,
        cycle_ath_usd=cycle_ath_usd,
        mvrv_z_score=mvrv_z,
        sma_50w=sma_50w,
        executed_stages=list(executed_stages),
        active_phase=active_phase,
    )

    if cycle_trigger:
        stage, action_type, alloc_pct = cycle_trigger

        if action_type == TransactionType.BUY:
            amount_brl = round(total_reserve_brl * alloc_pct, 2)
            amount_btc = round(amount_brl / spot_price_brl, 8) if spot_price_brl > 0 else 0.0
            collar_price = round(spot_price_brl * 1.003, 2)

            tax_plan = TaxExecutionPlan(
                action="BUY",
                status=TaxStatus.EXEMPT,
                darf_amount=0.0,
                gross_gain_brl=0.0,
                notes="Aquisição de Bitcoin (não gera tributação, atualiza CMP)",
            )

            instructions = [
                f"Transferência: Transfira R$ {amount_brl:,.2f} via PIX da sua conta bancária para a corretora {default_exchange}.",
                f"Ordem: Abra ordem de compra limitada no par BTC/BRL a R$ {collar_price:,.2f} para acumular aproximadamente {amount_btc:.8f} BTC.",
                f"Custódia Soberana: Imediatamente após a execução, solicite o saque on-chain de {amount_btc:.8f} BTC para o endereço da sua cold wallet.",
                "Auditoria: Registre a transação no BitSignal via CLI ou painel web para atualizar o Custo Médio Ponderado (CMP).",
            ]

            return StrategyRunbook(
                stage=stage,
                date=date_str,
                price_usd=spot_price_usd,
                price_brl=spot_price_brl,
                amount_btc=amount_btc,
                amount_brl=amount_brl,
                tax_plan=tax_plan,
                action_type=TransactionType.BUY,
                order_type="LIMIT",
                collar_price_brl=collar_price,
                nocturnal_pix_warning=False,
                instructions=instructions,
            )

        elif action_type == TransactionType.SELL:
            btc_to_sell = round(summary.current_btc_balance * alloc_pct, 8)
            gross_sale_brl = round(btc_to_sell * spot_price_brl, 2)
            collar_price = round(spot_price_brl * 0.997, 2)
            monthly_accum = get_monthly_accumulated_alienation(month_year=date_str[:7], db_path=db_path)

            tax_plan = evaluate_tax_strategy(
                alienation_brl=gross_sale_brl,
                quantity_btc=btc_to_sell,
                current_cmp_brl=summary.current_cmp_brl,
                month_accumulated_brl=monthly_accum,
                signal_date=now,
            )

            actual_btc = tax_plan.part1_btc if tax_plan.part1_btc else btc_to_sell
            actual_brl = tax_plan.part1_now_brl if tax_plan.part1_now_brl else gross_sale_brl
            nocturnal_warning = actual_brl > bank_night_limit_brl

            instructions = [
                f"Custódia: Transfira exatamente {actual_btc:.8f} BTC da sua cold wallet para a corretora {default_exchange}.",
                f"Ordem: Abra ordem de venda limitada no par BTC/BRL a R$ {collar_price:,.2f} (collar de 0,3% para evitar slippage). Valor estimado a receber: R$ {actual_brl:,.2f}.",
            ]
            if nocturnal_warning:
                instructions.append(
                    f"Protocolo Noturno de PIX: Como o valor (R$ {actual_brl:,.2f}) excede o limite noturno bancário (R$ {bank_night_limit_brl:,.2f}), transfira até R$ {bank_night_limit_brl:,.2f} imediatamente e agende R$ {actual_brl - bank_night_limit_brl:,.2f} para amanhã às 06h01 BRT."
                )
            else:
                instructions.append(
                    f"Saque: Efetue saque via PIX de R$ {actual_brl:,.2f} para sua conta corrente titular."
                )
            instructions.append("Destino do Caixa: Aplicar recursos em CDB de liquidez diária com resgate 24/7 (100% CDI).")

            return StrategyRunbook(
                stage=stage,
                date=date_str,
                price_usd=spot_price_usd,
                price_brl=spot_price_brl,
                amount_btc=actual_btc,
                amount_brl=actual_brl,
                tax_plan=tax_plan,
                action_type=TransactionType.SELL,
                order_type="LIMIT",
                collar_price_brl=collar_price,
                nocturnal_pix_warning=nocturnal_warning,
                instructions=instructions,
            )

    return None
