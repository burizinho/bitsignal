"""Brazilian RFB tax compliance engine (Lei 8.981/1995 & IN 1.888/2019)."""

from datetime import datetime
from typing import Any, Dict
from bitsignal.storage.db import get_connection, get_monthly_tax_summary
from bitsignal.strategy.models import TaxExecutionPlan, TaxStatus

EXEMPTION_THRESHOLD_BRL = 35000.0
SPLIT_MAX_THRESHOLD_BRL = 70000.0
SPLIT_WINDOW_MIN_DAY = 25
CAPITAL_GAIN_TAX_RATE = 0.15
DEFAULT_SAFETY_BUFFER_BRL = 500.0


def evaluate_tax_strategy(
    alienation_brl: float,
    quantity_btc: float,
    current_cmp_brl: float,
    month_accumulated_brl: float,
    signal_date: datetime,
    safety_buffer_brl: float = DEFAULT_SAFETY_BUFFER_BRL,
) -> TaxExecutionPlan:
    """Evaluate tax impact under Brazilian RFB regulations.

    Applies R$ 35,000/month exemption rule and conditional month-end split.
    """
    total_projected = month_accumulated_brl + alienation_brl
    cost_basis = quantity_btc * current_cmp_brl
    gross_gain = max(0.0, alienation_brl - cost_basis)

    # 1. Total monthly sales stay within R$ 35,000 exemption limit
    if total_projected <= EXEMPTION_THRESHOLD_BRL:
        return TaxExecutionPlan(
            action="SELL_FULL",
            status=TaxStatus.EXEMPT,
            darf_amount=0.0,
            part1_now_brl=alienation_brl,
            part1_btc=quantity_btc,
            gross_gain_brl=gross_gain,
            notes=f"100% Isento (Alienação acumulada no mês: R$ {total_projected:,.2f} <= R$ 35.000,00).",
        )

    # 2. Eligible for inter-month split:
    # First sale of the month, total between R$ 35k and R$ 70k, occurring on or after day 25
    elif (
        month_accumulated_brl == 0.0
        and EXEMPTION_THRESHOLD_BRL < alienation_brl <= SPLIT_MAX_THRESHOLD_BRL
        and signal_date.day >= SPLIT_WINDOW_MIN_DAY
    ):
        part1_brl = EXEMPTION_THRESHOLD_BRL - safety_buffer_brl
        part2_brl = alienation_brl - part1_brl
        part1_btc = (part1_brl / alienation_brl) * quantity_btc
        part2_btc = quantity_btc - part1_btc

        return TaxExecutionPlan(
            action="SPLIT_MONTH_END",
            status=TaxStatus.EXEMPT,
            darf_amount=0.0,
            part1_now_brl=part1_brl,
            part2_next_month_brl=part2_brl,
            part1_btc=part1_btc,
            part2_btc=part2_btc,
            gross_gain_brl=gross_gain,
            notes=(
                f"Split Intermensal Ativado: Parte 1 (R$ {part1_brl:,.2f}) agora; "
                f"Parte 2 (R$ {part2_brl:,.2f}) agendada para 01/{signal_date.month % 12 + 1:02d} às 09h BRT."
            ),
        )

    # 3. Taxable full sell: Exceeds R$ 35k or occurs outside split window
    else:
        # 15% flat tax under GCAP (up to R$ 5 million gain)
        darf_due = gross_gain * CAPITAL_GAIN_TAX_RATE
        notes = "Tributável a 15% via DARF código 4600."
        if total_projected > EXEMPTION_THRESHOLD_BRL and month_accumulated_brl > 0:
            notes += f" (Alienações anteriores no mês já somavam R$ {month_accumulated_brl:,.2f})."
        elif signal_date.day < SPLIT_WINDOW_MIN_DAY:
            notes += " (Sinal antes do dia 25; liquidação total imediata para priorizar proteção patrimonial)."

        return TaxExecutionPlan(
            action="SELL_FULL",
            status=TaxStatus.TAXABLE,
            darf_amount=darf_due,
            part1_now_brl=alienation_brl,
            part1_btc=quantity_btc,
            gross_gain_brl=gross_gain,
            notes=notes,
        )


def get_monthly_accumulated_alienation(
    month_year: str,
    db_path: str = "./data/bitsignal.db",
) -> float:
    """Retrieve cumulative gross BRL alienation for a given YYYY-MM."""
    summaries = get_monthly_tax_summary(month_year, db_path)
    if summaries:
        return float(summaries[0]["total_alienated_brl"])
    return 0.0


def compute_darf_for_month(
    month_year: str,
    db_path: str = "./data/bitsignal.db",
) -> Dict[str, Any]:
    """Calculate cumulative capital gain and DARF due for a specific month.

    Enforces retroactive taxation: if total sales in YYYY-MM exceed R$ 35,000,
    all sales in that month are taxable at 15%.
    """
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT amount_btc, price_brl, fee_brl 
            FROM portfolio_transactions 
            WHERE tx_type = 'SELL' AND strftime('%Y-%m', date) = ?
            ORDER BY date ASC;
            """,
            (month_year,),
        ).fetchall()

        # Get CMP from summary
        cmp_row = conn.execute(
            """
            SELECT COALESCE(
                SUM(CASE WHEN tx_type = 'BUY' THEN (amount_btc * price_brl + fee_brl) ELSE 0.0 END) /
                NULLIF(SUM(CASE WHEN tx_type = 'BUY' THEN amount_btc ELSE 0.0 END), 0),
                0.0
            ) as cmp FROM portfolio_transactions;
            """
        ).fetchone()
        cmp_brl = float(cmp_row["cmp"]) if cmp_row else 0.0

    if not rows:
        return {
            "month_year": month_year,
            "total_alienated_brl": 0.0,
            "total_gain_brl": 0.0,
            "is_exempt": True,
            "darf_due_brl": 0.0,
        }

    total_alienated = sum(float(r["amount_btc"]) * float(r["price_brl"]) for r in rows)
    total_cost = sum(float(r["amount_btc"]) * cmp_brl for r in rows)
    total_fees = sum(float(r["fee_brl"] or 0.0) for r in rows)
    net_gain = max(0.0, total_alienated - total_cost - total_fees)

    is_exempt = total_alienated <= EXEMPTION_THRESHOLD_BRL
    darf_amount = 0.0 if is_exempt else net_gain * CAPITAL_GAIN_TAX_RATE

    return {
        "month_year": month_year,
        "total_alienated_brl": total_alienated,
        "total_gain_brl": net_gain,
        "is_exempt": is_exempt,
        "darf_due_brl": darf_amount,
    }
