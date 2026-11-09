"""Persistence layer using SQLite in WAL mode."""

import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional
from bitsignal.models import DailyCompositeResult, DailyMetrics, HysteresisState
from bitsignal.strategy.models import PortfolioSummary, PortfolioTransaction


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS daily_metrics (
    date TEXT PRIMARY KEY,
    btc_price REAL NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    volume REAL,
    sma_111 REAL,
    sma_350 REAL,
    sma_471 REAL,
    ema_150 REAL,
    sma_200w REAL,
    rsi_14w REAL,
    mvrv_z REAL,
    puell_multiple REAL,
    hashrate REAL,
    hash_ribbon_status TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_scores (
    date TEXT PRIMARY KEY,
    composite_score REAL NOT NULL,
    mvrv_score REAL NOT NULL,
    sma200w_score REAL NOT NULL,
    puell_score REAL NOT NULL,
    picycle_score REAL NOT NULL,
    rsi_score REAL NOT NULL,
    hashribbon_score REAL NOT NULL,
    system_status TEXT NOT NULL,
    hysteresis_state TEXT NOT NULL,
    stale_metrics TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_dispatches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    composite_score REAL,
    payload TEXT NOT NULL,
    delivered_telegram BOOLEAN NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS portfolio_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    tx_type TEXT CHECK(tx_type IN ('BUY', 'SELL')) NOT NULL,
    stage TEXT NOT NULL,
    amount_btc REAL NOT NULL,
    price_brl REAL NOT NULL,
    price_usd REAL NOT NULL,
    ptax_rate REAL,
    fee_brl REAL DEFAULT 0.0,
    exchange TEXT NOT NULL,
    tx_hash TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE VIEW IF NOT EXISTS v_portfolio_summary AS
SELECT 
    COALESCE(SUM(CASE WHEN tx_type = 'BUY' THEN amount_btc ELSE -amount_btc END), 0.0) AS current_btc_balance,
    COALESCE(
        SUM(CASE WHEN tx_type = 'BUY' THEN (amount_btc * price_brl + fee_brl) ELSE 0.0 END) /
        NULLIF(SUM(CASE WHEN tx_type = 'BUY' THEN amount_btc ELSE 0.0 END), 0),
        0.0
    ) AS current_cmp_brl
FROM portfolio_transactions;

CREATE VIEW IF NOT EXISTS v_tax_monthly_summary AS
SELECT 
    strftime('%Y-%m', date) AS month_year,
    SUM(amount_btc * price_brl) AS total_alienated_brl,
    SUM(fee_brl) AS total_fees_brl,
    CASE WHEN SUM(amount_btc * price_brl) <= 35000.0 THEN 1 ELSE 0 END AS is_exempt
FROM portfolio_transactions
WHERE tx_type = 'SELL'
GROUP BY strftime('%Y-%m', date);
"""


@contextmanager
def get_connection(db_path: str = "./data/bitsignal.db"):
    """Yield an active SQLite connection configured with WAL mode."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = "./data/bitsignal.db") -> None:
    """Initialize SQLite tables and indexes."""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_SQL)


def upsert_daily_metrics(metrics: DailyMetrics, db_path: str = "./data/bitsignal.db") -> None:
    """Upsert daily raw and calculated metrics."""
    query = """
    INSERT INTO daily_metrics (
        date, btc_price, open, high, low, volume,
        sma_111, sma_350, sma_471, ema_150, sma_200w,
        rsi_14w, mvrv_z, puell_multiple, hashrate, hash_ribbon_status
    ) VALUES (
        :date, :btc_price, :open, :high, :low, :volume,
        :sma_111, :sma_350, :sma_471, :ema_150, :sma_200w,
        :rsi_14w, :mvrv_z, :puell_multiple, :hashrate, :hash_ribbon_status
    ) ON CONFLICT(date) DO UPDATE SET
        btc_price = excluded.btc_price,
        open = excluded.open,
        high = excluded.high,
        low = excluded.low,
        volume = excluded.volume,
        sma_111 = excluded.sma_111,
        sma_350 = excluded.sma_350,
        sma_471 = excluded.sma_471,
        ema_150 = excluded.ema_150,
        sma_200w = excluded.sma_200w,
        rsi_14w = excluded.rsi_14w,
        mvrv_z = excluded.mvrv_z,
        puell_multiple = excluded.puell_multiple,
        hashrate = excluded.hashrate,
        hash_ribbon_status = excluded.hash_ribbon_status,
        created_at = CURRENT_TIMESTAMP;
    """
    with get_connection(db_path) as conn:
        conn.execute(query, metrics.model_dump())


def upsert_daily_score(score: DailyCompositeResult, db_path: str = "./data/bitsignal.db") -> None:
    """Upsert a calculated daily composite score."""
    query = """
    INSERT INTO daily_scores (
        date, composite_score, mvrv_score, sma200w_score, puell_score,
        picycle_score, rsi_score, hashribbon_score, system_status,
        hysteresis_state, stale_metrics
    ) VALUES (
        :date, :composite_score, :mvrv_score, :sma200w_score, :puell_score,
        :picycle_score, :rsi_score, :hashribbon_score, :system_status,
        :hysteresis_state, :stale_metrics
    ) ON CONFLICT(date) DO UPDATE SET
        composite_score = excluded.composite_score,
        mvrv_score = excluded.mvrv_score,
        sma200w_score = excluded.sma200w_score,
        puell_score = excluded.puell_score,
        picycle_score = excluded.picycle_score,
        rsi_score = excluded.rsi_score,
        hashribbon_score = excluded.hashribbon_score,
        system_status = excluded.system_status,
        hysteresis_state = excluded.hysteresis_state,
        stale_metrics = excluded.stale_metrics,
        created_at = CURRENT_TIMESTAMP;
    """
    params = {
        "date": score.date,
        "composite_score": score.composite_score,
        "mvrv_score": score.mvrv_score,
        "sma200w_score": score.sma200w_score,
        "puell_score": score.puell_score,
        "picycle_score": score.picycle_score,
        "rsi_score": score.rsi_score,
        "hashribbon_score": score.hashribbon_score,
        "system_status": score.system_status.value,
        "hysteresis_state": score.hysteresis_state.value,
        "stale_metrics": score.stale_metrics,
    }
    with get_connection(db_path) as conn:
        conn.execute(query, params)


def record_alert_dispatch(
    date: str,
    alert_type: str,
    composite_score: Optional[float],
    payload: str,
    delivered_telegram: bool = False,
    db_path: str = "./data/bitsignal.db",
) -> int:
    """Record an alert dispatch in SQLite and return the new row ID."""
    query = """
    INSERT INTO alert_dispatches (
        date, alert_type, composite_score, payload, delivered_telegram
    ) VALUES (?, ?, ?, ?, ?);
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            query, (date, alert_type, composite_score, payload, int(delivered_telegram))
        )
        return cursor.lastrowid


def get_latest_hysteresis_state(db_path: str = "./data/bitsignal.db") -> HysteresisState:
    """Retrieve the most recent hysteresis state, or default to NEUTRAL."""
    query = "SELECT hysteresis_state FROM daily_scores ORDER BY date DESC LIMIT 1;"
    with get_connection(db_path) as conn:
        row = conn.execute(query).fetchone()
        if row and row["hysteresis_state"]:
            try:
                return HysteresisState(row["hysteresis_state"])
            except ValueError:
                return HysteresisState.NEUTRAL
        return HysteresisState.NEUTRAL


def get_latest_score(db_path: str = "./data/bitsignal.db") -> Optional[Dict[str, Any]]:
    """Retrieve the most recent calculated daily score."""
    query = "SELECT * FROM daily_scores ORDER BY date DESC LIMIT 1;"
    with get_connection(db_path) as conn:
        row = conn.execute(query).fetchone()
        if row:
            return dict(row)
        return None


def get_historical_scores(db_path: str = "./data/bitsignal.db", limit: int = 5000) -> List[Dict[str, Any]]:
    """Retrieve historical daily scores ordered chronologically."""
    query = "SELECT * FROM daily_scores ORDER BY date ASC LIMIT ?;"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, (limit,)).fetchall()
        return [dict(r) for r in rows]


def record_portfolio_transaction(
    tx: PortfolioTransaction,
    db_path: str = "./data/bitsignal.db",
) -> int:
    """Record a portfolio transaction in SQLite and return the new row ID."""
    query = """
    INSERT INTO portfolio_transactions (
        date, tx_type, stage, amount_btc, price_brl, price_usd,
        ptax_rate, fee_brl, exchange, tx_hash, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            query,
            (
                tx.date,
                tx.tx_type.value if hasattr(tx.tx_type, "value") else str(tx.tx_type),
                tx.stage.value if hasattr(tx.stage, "value") else str(tx.stage),
                float(tx.amount_btc),
                float(tx.price_brl),
                float(tx.price_usd),
                float(tx.ptax_rate) if tx.ptax_rate is not None else None,
                float(tx.fee_brl),
                str(tx.exchange),
                tx.tx_hash,
                tx.notes,
            ),
        )
        return cursor.lastrowid


def get_portfolio_summary(db_path: str = "./data/bitsignal.db") -> PortfolioSummary:
    """Calculate current portfolio balance and weighted average acquisition cost (CMP)."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            "SELECT tx_type, amount_btc, price_brl, fee_brl FROM portfolio_transactions ORDER BY date ASC, id ASC;"
        ).fetchall()

    current_btc = 0.0
    total_cost_brl = 0.0
    total_invested_brl = 0.0
    total_withdrawn_brl = 0.0
    total_fees_brl = 0.0

    for r in rows:
        amount = float(r["amount_btc"])
        price = float(r["price_brl"])
        fee = float(r["fee_brl"] or 0.0)
        total_fees_brl += fee

        if r["tx_type"] == "BUY":
            total_invested_brl += (amount * price) + fee
            total_cost_brl += (amount * price) + fee
            current_btc += amount
        elif r["tx_type"] == "SELL":
            total_withdrawn_brl += (amount * price) - fee
            if current_btc > 0:
                cost_ratio = min(1.0, amount / current_btc)
                total_cost_brl -= total_cost_brl * cost_ratio
                current_btc -= amount
            else:
                current_btc -= amount

    cmp_brl = (total_cost_brl / current_btc) if current_btc > 0 else 0.0
    return PortfolioSummary(
        current_btc_balance=max(0.0, current_btc),
        current_cmp_brl=max(0.0, cmp_brl),
        total_invested_brl=total_invested_brl,
        total_withdrawn_brl=total_withdrawn_brl,
        total_fees_brl=total_fees_brl,
    )


def get_portfolio_transactions(
    db_path: str = "./data/bitsignal.db",
    limit: int = 1000,
) -> List[PortfolioTransaction]:
    """Retrieve historical portfolio transactions."""
    query = "SELECT * FROM portfolio_transactions ORDER BY date DESC, id DESC LIMIT ?;"
    with get_connection(db_path) as conn:
        rows = conn.execute(query, (limit,)).fetchall()
        return [PortfolioTransaction(**dict(r)) for r in rows]


def get_monthly_tax_summary(
    month_year: Optional[str] = None,
    db_path: str = "./data/bitsignal.db",
) -> List[Dict[str, Any]]:
    """Retrieve monthly alienation summaries for RFB tax audit."""
    if month_year:
        query = "SELECT * FROM v_tax_monthly_summary WHERE month_year = ?;"
        params = (month_year,)
    else:
        query = "SELECT * FROM v_tax_monthly_summary ORDER BY month_year DESC;"
        params = ()

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def get_executed_stages(db_path: str = "./data/bitsignal.db") -> List[str]:
    """Retrieve the set of unique strategy stages already executed."""
    query = "SELECT DISTINCT stage FROM portfolio_transactions;"
    with get_connection(db_path) as conn:
        rows = conn.execute(query).fetchall()
        return [str(r["stage"]) for r in rows]
