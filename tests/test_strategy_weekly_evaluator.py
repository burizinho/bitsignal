"""Tests for weekly evaluator orchestration and Telegram runbook dispatching."""

from datetime import datetime, timezone
from unittest.mock import patch
import pandas as pd
import pytest

from bitsignal.alerts.dispatcher import format_strategy_runbook_message, send_strategy_runbook
from bitsignal.storage.db import (
    init_db,
    record_portfolio_transaction,
)
from bitsignal.strategy.models import (
    PortfolioTransaction,
    StageType,
    StrategyRunbook,
    TaxExecutionPlan,
    TaxStatus,
    TransactionType,
)
from bitsignal.strategy.weekly_evaluator import (
    evaluate_weekly_strategy,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "test_strategy.db")
    init_db(db_file)
    return db_file


def test_weekly_evaluator_dca_buy_c0(test_db):
    """Test C0 DCA trigger when price drops below -30% ATH."""
    # Seed 0 BTC balance
    cfg = {
        "strategy": {
            "cycle_ath_usd": 100000.0,
            "total_reserve_brl": 100000.0,
            "bank_night_limit_brl": 5000.0,
            "default_exchange": "Bipa",
        }
    }

    # Price at 68,000 USD (-32% from 100k ATH) -> triggers C0
    runbook = evaluate_weekly_strategy(
        db_path=test_db,
        config=cfg,
        spot_price_usd=68000.0,
        spot_price_brl=400000.0,
    )

    assert runbook is not None
    assert runbook.stage == StageType.C0
    assert runbook.action_type == TransactionType.BUY
    assert runbook.amount_brl == 30000.0  # 30% of 100k reserve
    assert runbook.amount_btc == pytest.approx(30000.0 / 400000.0, 1e-6)
    assert runbook.tax_plan.status == TaxStatus.EXEMPT
    assert any("Bipa" in inst for inst in runbook.instructions)


def test_weekly_evaluator_dca_sell_v1(test_db):
    """Test V1 trigger when price breaks new ATH."""
    # Seed portfolio with 0.4 BTC
    tx = PortfolioTransaction(
        date="2025-01-01 12:00:00",
        tx_type=TransactionType.BUY,
        stage=StageType.C0,
        amount_btc=0.4,
        price_brl=300000.0,
        price_usd=50000.0,
        exchange="Bipa",
    )
    record_portfolio_transaction(tx, db_path=test_db)

    cfg = {
        "strategy": {
            "cycle_ath_usd": 100000.0,
            "bank_night_limit_brl": 5000.0,
            "default_exchange": "Bipa",
        }
    }

    # Spot price at 105,000 USD (> ATH 100k) -> triggers V1 (10% exit)
    runbook = evaluate_weekly_strategy(
        db_path=test_db,
        config=cfg,
        spot_price_usd=105000.0,
        spot_price_brl=600000.0,
    )

    assert runbook is not None
    assert runbook.stage == StageType.V1
    assert runbook.action_type == TransactionType.SELL
    assert runbook.amount_btc == pytest.approx(0.04, 1e-6)  # 10% of 0.4
    assert runbook.amount_brl == pytest.approx(0.04 * 600000.0, 1e-2)  # 24,000 BRL
    # 24,000 <= 35,000 -> EXEMPT
    assert runbook.tax_plan.status == TaxStatus.EXEMPT
    assert runbook.nocturnal_pix_warning is True  # 24,000 > 5,000 night limit


def test_weekly_evaluator_trailing_stop_1(test_db):
    """Test Stop 1 trigger on Sunday close below 21w EMA."""
    # Seed 0.3 BTC
    tx = PortfolioTransaction(
        date="2025-01-01 12:00:00",
        tx_type=TransactionType.BUY,
        stage=StageType.C0,
        amount_btc=0.3,
        price_brl=300000.0,
        price_usd=50000.0,
        exchange="Bipa",
    )
    record_portfolio_transaction(tx, db_path=test_db)

    # Generate 60 weeks of prices: starts at 50k, rises to 120k, then drops below 21w EMA
    prices = [50000.0 + i * 1200.0 for i in range(55)]  # up to ~116k
    # 21w EMA will be ~100k+, drop price to 85,000
    prices.extend([92000.0, 92000.0, 92000.0, 92000.0, 92000.0])
    weekly_series = pd.Series(prices)

    cfg = {
        "strategy": {
            "cycle_ath_usd": 120000.0,
            "bank_night_limit_brl": 5000.0,
        }
    }

    runbook = evaluate_weekly_strategy(
        db_path=test_db,
        config=cfg,
        weekly_closes=weekly_series,
        spot_price_usd=92000.0,
        spot_price_brl=550000.0,
    )

    assert runbook is not None
    assert runbook.stage == StageType.STOP_1
    assert runbook.action_type == TransactionType.SELL
    # Stop 1 sells 50% of 0.3 = 0.15 BTC
    # But notice tax split check: 0.15 * 480k = 72k BRL (> 70k -> TAXABLE, full execution)
    assert runbook.tax_plan.status == TaxStatus.TAXABLE
    assert runbook.amount_btc == 0.15


def test_weekly_evaluator_pending_split_part2(test_db):
    """Test Day 1 detection of pending Part 2 from prior month split."""
    # Seed a BUY of 0.2 BTC
    record_portfolio_transaction(
        PortfolioTransaction(
            date="2025-09-01 10:00:00",
            tx_type=TransactionType.BUY,
            stage=StageType.C0,
            amount_btc=0.2,
            price_brl=300000.0,
            price_usd=50000.0,
            exchange="Bipa",
        ),
        db_path=test_db,
    )
    # Seed a SELL on day 27 of 0.08 BTC with split note
    record_portfolio_transaction(
        PortfolioTransaction(
            date="2025-10-27 21:00:00",
            tx_type=TransactionType.SELL,
            stage=StageType.V1,
            amount_btc=0.08,
            price_brl=437500.0,
            price_usd=75000.0,
            exchange="Bipa",
            notes="Split intermensal: R$ 35.000 agora (isento) e saldo no dia 1 do próximo mês",
        ),
        db_path=test_db,
    )

    # Evaluate on Nov 1st
    nov_1st = datetime(2025, 11, 1, 9, 0, 0, tzinfo=timezone.utc)
    runbook = evaluate_weekly_strategy(
        db_path=test_db,
        current_time=nov_1st,
        spot_price_usd=75000.0,
        spot_price_brl=450000.0,
    )

    assert runbook is not None
    assert runbook.stage == StageType.SPLIT_PART_2
    assert runbook.action_type == TransactionType.SELL
    assert runbook.tax_plan.status == TaxStatus.EXEMPT


def test_telegram_runbook_message_and_dispatch(test_db):
    """Test Telegram message generation and dispatch function."""
    tax_plan = TaxExecutionPlan(
        action="SELL_FULL",
        status=TaxStatus.EXEMPT,
        darf_amount=0.0,
        gross_gain_brl=12500.0,
    )
    runbook = StrategyRunbook(
        stage=StageType.V1,
        date="2025-10-26 21:01 BRT",
        price_usd=128500.0,
        price_brl=745300.0,
        amount_btc=0.04628,
        amount_brl=34500.0,
        tax_plan=tax_plan,
        action_type=TransactionType.SELL,
        collar_price_brl=743000.0,
        nocturnal_pix_warning=True,
        instructions=[
            "Transfira 0.04628000 BTC da cold wallet para a Bipa.",
            "Ordem de venda limitada a R$ 743.000,00.",
            "Protocolo Noturno de PIX: Transfira até R$ 5.000,00 hoje e R$ 29.500,00 amanhã às 06h01.",
        ],
    )

    msg = format_strategy_runbook_message(runbook, current_cmp_brl=280000.0)
    assert "BITSIGNAL - ALERTA DE EXECUÇÃO ESTRATÉGICA" in msg
    assert "VENDA V1" in msg
    assert "R$ 745,300.00" in msg
    assert "Protocolo Noturno de PIX" in msg
    assert "100% ISENTO" in msg
    assert "R$ 280,000.00/BTC" in msg

    # Test dispatch in dry run mode
    delivered = send_strategy_runbook(
        runbook=runbook,
        bot_token=None,
        chat_id=None,
        current_cmp_brl=280000.0,
        db_path=test_db,
        dry_run=True,
    )
    assert delivered is False

    # Test dispatch with mocked network success
    with patch("bitsignal.alerts.dispatcher.requests.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        delivered = send_strategy_runbook(
            runbook=runbook,
            bot_token="fake_bot_token",
            chat_id="fake_chat_id",
            current_cmp_brl=280000.0,
            db_path=test_db,
            dry_run=False,
        )
        assert delivered is True
        assert mock_post.called
