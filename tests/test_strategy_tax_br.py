"""Unit tests for Brazilian RFB tax compliance engine."""

from datetime import datetime
import pytest
from bitsignal.strategy.models import TaxStatus
from bitsignal.strategy.tax_br import (
    compute_darf_for_month,
    evaluate_tax_strategy,
)
from bitsignal.storage.db import init_db, record_portfolio_transaction
from bitsignal.strategy.models import PortfolioTransaction, StageType, TransactionType
import tempfile
import os


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def test_evaluate_tax_strategy_exempt():
    # Alienation R$ 30,000, 0 accumulated in month -> 100% exempt
    plan = evaluate_tax_strategy(
        alienation_brl=30000.0,
        quantity_btc=0.04,
        current_cmp_brl=250000.0,
        month_accumulated_brl=0.0,
        signal_date=datetime(2027, 5, 10),
    )
    assert plan.status == TaxStatus.EXEMPT
    assert plan.action == "SELL_FULL"
    assert plan.darf_amount == 0.0
    assert plan.part1_now_brl == 30000.0
    assert pytest.approx(plan.gross_gain_brl, 0.01) == 20000.0


def test_evaluate_tax_strategy_accumulated_breach():
    # Prior sales R$ 20,000, new alienation R$ 20,000 -> Total R$ 40,000 > R$ 35,000 -> TAXABLE
    plan = evaluate_tax_strategy(
        alienation_brl=20000.0,
        quantity_btc=0.02,
        current_cmp_brl=300000.0,
        month_accumulated_brl=20000.0,
        signal_date=datetime(2027, 5, 20),
    )
    assert plan.status == TaxStatus.TAXABLE
    assert plan.action == "SELL_FULL"
    # Cost = 0.02 * 300k = 6k. Gain = 20k - 6k = 14k. DARF 15% = 2,100
    assert pytest.approx(plan.gross_gain_brl, 0.01) == 14000.0
    assert pytest.approx(plan.darf_amount, 0.01) == 2100.0


def test_evaluate_tax_strategy_split_end_of_month():
    # Alienation R$ 60,000 on day 26 -> Split eligible!
    plan = evaluate_tax_strategy(
        alienation_brl=60000.0,
        quantity_btc=0.08,
        current_cmp_brl=280000.0,
        month_accumulated_brl=0.0,
        signal_date=datetime(2027, 10, 26),
    )
    assert plan.status == TaxStatus.EXEMPT
    assert plan.action == "SPLIT_MONTH_END"
    assert plan.darf_amount == 0.0
    assert plan.part1_now_brl == 34500.0
    assert plan.part2_next_month_brl == 25500.0
    assert pytest.approx(plan.part1_btc + plan.part2_btc, 0.00001) == 0.08
    assert plan.part1_btc < 0.08
    assert plan.part2_btc > 0.0


def test_evaluate_tax_strategy_split_blocked_early_month():
    # Alienation R$ 60,000 on day 10 -> Too early to hold risk -> SELL FULL TAXABLE
    plan = evaluate_tax_strategy(
        alienation_brl=60000.0,
        quantity_btc=0.08,
        current_cmp_brl=280000.0,
        month_accumulated_brl=0.0,
        signal_date=datetime(2027, 10, 10),
    )
    assert plan.status == TaxStatus.TAXABLE
    assert plan.action == "SELL_FULL"
    # Cost = 0.08 * 280,000 = 22,400. Gain = 60,000 - 22,400 = 37,600. DARF = 37,600 * 0.15 = 5,640
    assert pytest.approx(plan.darf_amount, 0.01) == 5640.0


def test_compute_darf_for_month_retroactive(temp_db):
    # Buy 0.5 BTC at R$ 200,000 -> Cost basis R$ 200,000/BTC
    record_portfolio_transaction(
        PortfolioTransaction(
            date="2027-01-01 10:00:00",
            tx_type=TransactionType.BUY,
            stage=StageType.C0,
            amount_btc=0.5,
            price_brl=200000.0,
            price_usd=40000.0,
            fee_brl=0.0,
            exchange="Mercado Bitcoin",
        ),
        temp_db,
    )

    # Sale 1 in May: R$ 25,000 (0.05 BTC @ R$ 500,000)
    record_portfolio_transaction(
        PortfolioTransaction(
            date="2027-05-05 10:00:00",
            tx_type=TransactionType.SELL,
            stage=StageType.V1,
            amount_btc=0.05,
            price_brl=500000.0,
            price_usd=100000.0,
            fee_brl=0.0,
            exchange="Mercado Bitcoin",
        ),
        temp_db,
    )
    report_may_1 = compute_darf_for_month("2027-05", temp_db)
    assert report_may_1["is_exempt"] is True
    assert report_may_1["darf_due_brl"] == 0.0

    # Sale 2 in May: R$ 25,000 (0.05 BTC @ R$ 500,000) -> Total May sales = R$ 50,000 > R$ 35,000!
    record_portfolio_transaction(
        PortfolioTransaction(
            date="2027-05-20 10:00:00",
            tx_type=TransactionType.SELL,
            stage=StageType.V2,
            amount_btc=0.05,
            price_brl=500000.0,
            price_usd=100000.0,
            fee_brl=0.0,
            exchange="Mercado Bitcoin",
        ),
        temp_db,
    )
    report_may_2 = compute_darf_for_month("2027-05", temp_db)
    assert report_may_2["is_exempt"] is False
    # Total alienation: R$ 50,000. Cost: 0.10 BTC * 200,000 = R$ 20,000. Gain: R$ 30,000. DARF 15% = R$ 4,500.
    assert pytest.approx(report_may_2["total_alienated_brl"], 0.01) == 50000.0
    assert pytest.approx(report_may_2["total_gain_brl"], 0.01) == 30000.0
    assert pytest.approx(report_may_2["darf_due_brl"], 0.01) == 4500.0
