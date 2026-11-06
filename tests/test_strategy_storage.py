"""Unit tests for strategy portfolio ledger and SQLite views."""

import os
import tempfile
import pytest
from bitsignal.storage.db import (
    get_executed_stages,
    get_monthly_tax_summary,
    get_portfolio_summary,
    get_portfolio_transactions,
    init_db,
    record_portfolio_transaction,
)
from bitsignal.strategy.models import (
    PortfolioTransaction,
    StageType,
    TransactionType,
)


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    if os.path.exists(db_path):
        os.remove(db_path)


def test_portfolio_ledger_empty(temp_db):
    summary = get_portfolio_summary(temp_db)
    assert summary.current_btc_balance == 0.0
    assert summary.current_cmp_brl == 0.0
    assert summary.total_invested_brl == 0.0
    assert summary.total_withdrawn_brl == 0.0
    assert get_executed_stages(temp_db) == []


def test_portfolio_buy_and_cmp_calculation(temp_db):
    # Buy 1: 0.1 BTC at R$ 300,000 + R$ 100 fee -> Cost = R$ 30,100 -> CMP = 301,000
    tx1 = PortfolioTransaction(
        date="2026-11-01 10:00:00",
        tx_type=TransactionType.BUY,
        stage=StageType.C0,
        amount_btc=0.1,
        price_brl=300000.0,
        price_usd=50000.0,
        fee_brl=100.0,
        exchange="Mercado Bitcoin",
    )
    row_id1 = record_portfolio_transaction(tx1, temp_db)
    assert row_id1 == 1

    summary1 = get_portfolio_summary(temp_db)
    assert pytest.approx(summary1.current_btc_balance, 0.0001) == 0.1
    assert pytest.approx(summary1.current_cmp_brl, 0.01) == 301000.0
    assert pytest.approx(summary1.total_invested_brl, 0.01) == 301000.0 * 0.1

    # Buy 2: 0.1 BTC at R$ 350,000 + R$ 200 fee -> Total Cost = 30,100 + 35,200 = 65,300 for 0.2 BTC -> CMP = 326,500
    tx2 = PortfolioTransaction(
        date="2026-11-05 12:00:00",
        tx_type=TransactionType.BUY,
        stage=StageType.C1,
        amount_btc=0.1,
        price_brl=350000.0,
        price_usd=58000.0,
        fee_brl=200.0,
        exchange="Foxbit",
    )
    record_portfolio_transaction(tx2, temp_db)

    summary2 = get_portfolio_summary(temp_db)
    assert pytest.approx(summary2.current_btc_balance, 0.0001) == 0.2
    assert pytest.approx(summary2.current_cmp_brl, 0.01) == 326500.0

    stages = get_executed_stages(temp_db)
    assert "C0" in stages
    assert "C1" in stages


def test_portfolio_sell_and_tax_summary(temp_db):
    # Buy 0.2 BTC at R$ 300,000
    tx_buy = PortfolioTransaction(
        date="2026-10-15 10:00:00",
        tx_type=TransactionType.BUY,
        stage=StageType.C0,
        amount_btc=0.2,
        price_brl=300000.0,
        price_usd=50000.0,
        fee_brl=0.0,
        exchange="Mercado Bitcoin",
    )
    record_portfolio_transaction(tx_buy, temp_db)

    # Sell 0.04 BTC at R$ 750,000 -> Alienation = R$ 30,000 (Exempt <= 35k)
    tx_sell1 = PortfolioTransaction(
        date="2026-11-02 14:00:00",
        tx_type=TransactionType.SELL,
        stage=StageType.V1,
        amount_btc=0.04,
        price_brl=750000.0,
        price_usd=130000.0,
        fee_brl=50.0,
        exchange="Mercado Bitcoin",
    )
    record_portfolio_transaction(tx_sell1, temp_db)

    summary = get_portfolio_summary(temp_db)
    assert pytest.approx(summary.current_btc_balance, 0.0001) == 0.16
    assert pytest.approx(summary.current_cmp_brl, 0.01) == 300000.0  # CMP remains unchanged upon sales

    # Check monthly tax view
    tax_rows = get_monthly_tax_summary(month_year="2026-11", db_path=temp_db)
    assert len(tax_rows) == 1
    assert tax_rows[0]["month_year"] == "2026-11"
    assert pytest.approx(tax_rows[0]["total_alienated_brl"], 0.01) == 30000.0
    assert tax_rows[0]["is_exempt"] == 1

    # Retrieve transactions
    tx_history = get_portfolio_transactions(temp_db)
    assert len(tx_history) == 2
    assert tx_history[0].tx_type == TransactionType.SELL
    assert tx_history[1].tx_type == TransactionType.BUY
