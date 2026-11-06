# Stage 9 Implementation Readiness Test Report

**Target:** `docs/designs/bitcoin_macro_cycle_sentinel.md` (`lines 338..522`)

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-implementation-readiness` | completed |
| `egm-codebase-details` | completed |
| `egm-style` | completed |

## Prioritized Findings (Blockers -> Major -> Nits)

### 1. Undefined Pi Cycle Continuous Normalization Formula & Bounds - Severity: Blocker
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 388–405 (`bitsignal/engine/indicators.py`, `bitsignal/engine/normalizer.py`), cross-referencing Lines 170–179 (Table: Metric Calibration)
* **Discrepancy Description**: 
  The normalization plan explicitly defines clamped linear normalization for standard metrics via `clamp((x - min) / (max - min) * 100, 0, 100)`. However, for Pi Cycle, Table 171 and Section 11/12 only specify binary cross conditions: "Bottom cross active ($S_i = 0$)" and "Top cross active ($S_i = 100$)". When neither cross is active (which represents >95% of market days), the document provides no mathematical formula, no input metric $x$, and no `min`/`max` bounds in `config.yaml` to compute a continuous 0–100 score. 
* **Rationale & Recommendation**: 
  An implementer cannot write deterministic code for `evaluate_picycle` and `normalizer.py` without inventing arbitrary formulas. Explicitly specify the continuous evaluation metric (e.g., spread ratio $R_{\text{top}} = \frac{\text{SMA}_{111}}{2 \times \text{SMA}_{350}}$ mapped from 0.70 to 1.00 for top proximity, or distance to bottom multiplier) and provide concrete calibration boundaries in `config.yaml`.

---

### 2. Unresolved External Data Contracts for On-Chain Valuation - Severity: Blocker
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 384–387 (`bitsignal/ingest/onchain.py`), cross-referencing Line 44 (Open Question 1)
* **Discrepancy Description**: 
  The implementation plan tasks `bitsignal/ingest/onchain.py` with pulling daily MVRV Z-Score and Puell Multiple from "verified public aggregators (CoinGecko / Blockchain.com / Dune public query endpoints)". However, Open Question 1 (Line 44) explicitly states that the specific free endpoint for Realized Cap / MVRV Z-Score is undecided. Neither CoinGecko's free tier nor Blockchain.com's public REST API provides native daily MVRV Z-Score or daily Realized Cap time series. Leaving the source endpoint, query schemas, and authentication parameters unresolved delegates architectural feasibility decisions to the implementer.
* **Rationale & Recommendation**: 
  Resolve Open Question 1 before implementation. Pin the exact primary and fallback API endpoints, request schemas, authentication requirements (or specific public query ID / GitHub mirror URL), and Pydantic response parsing models directly in the design document.

---

### 3. Missing Package Entrypoint (`__main__.py`) for Module Execution - Severity: Blocker
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 436–444 (`bitsignal/cli.py`), Lines 495–519 (Verification Plan)
* **Discrepancy Description**: 
  The Verification Plan repeatedly instructs executing the application via `python -m bitsignal backtest`, `python -m bitsignal db-init`, `python -m bitsignal run-daily`, and `python -m bitsignal ui`. However, Section 340 ("Target Files to Create/Modify") only specifies creating `bitsignal/__init__.py` and `bitsignal/cli.py`, with no `bitsignal/__main__.py` defined. Furthermore, `pyproject.toml` (Line 344) does not declare console script entry points (`[project.scripts]`). Running `python -m bitsignal <cmd>` will terminate with `No module named bitsignal.__main__`.
* **Rationale & Recommendation**: 
  Add `bitsignal/__main__.py` to the Target Files list in Section 340 (forwarding `sys.argv` to `bitsignal.cli:main`), or configure `[project.scripts] bitsignal = "bitsignal.cli:main"` in `pyproject.toml` and update Verification Plan commands accordingly.

---

### 4. Missing `yfinance` Runtime Dependency in `pyproject.toml` - Severity: Major
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 342–345 (`pyproject.toml`), Line 378 (`bitsignal/ingest/binance.py`)
* **Discrepancy Description**: 
  Section 8 (`bitsignal/ingest/binance.py`) states: "If Binance is unreachable (HTTP error or geo-blocking), automatically falls back to Yahoo Finance query for BTC-USD daily series." However, `yfinance` is completely omitted from core and optional dependencies in `pyproject.toml` (Line 344). Triggering the fallback in production or test will fail with `ModuleNotFoundError`.
* **Rationale & Recommendation**: 
  Add `yfinance>=0.2.30` (or the chosen HTTP client fallback) to `dependencies` in `pyproject.toml` (Line 344).

---

### 5. Mempool API Endpoint Path and Data Model Mismatch - Severity: Major
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 380–383 (`bitsignal/ingest/mempool.py`)
* **Discrepancy Description**: 
  Section 9 specifies pulling hashrate history from `mempool.space/api/v1/mining/hashrate/pools/1m` to compute 30-day and 60-day moving averages. The `/mining/hashrate/pools/*` route on mempool.space provides mining pool distribution percentages (market share), not aggregate network hashrate time series. 
* **Rationale & Recommendation**: 
  Correct the target endpoint to the actual network hashrate endpoint (`mempool.space/api/v1/mining/hashrate/3m` or `/api/v1/mining/hashrate/1m`), and document the expected response schema (array of `{ timestamp, avgHashrate }`) to calculate the 30d/60d rolling averages.

---

### 6. Unhandled Binance 1000-Candle Limit for 200-Week Moving Average - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 376–379 (`bitsignal/ingest/binance.py`), cross-referencing Line 143
* **Discrepancy Description**: 
  Computing the 200-week SMA on a daily basis requires 1,400 daily candles ($200 \times 7$). The Binance API endpoint `/api/v3/klines` has a hard limit of `limit=1000` candles per request. The detailed implementation plan does not provide instructions for pagination, historical cold backfill, or handling initial setup when fewer than 1,000 candles are fetched in a single request.
* **Rationale & Recommendation**: 
  Explicitly detail the pagination strategy in `bitsignal/ingest/binance.py` (e.g., executing two chunked requests using `startTime`/`endTime` parameters or fetching weekly candles directly for the 200w SMA) to ensure 1,400 daily bars are available upon cold start.

---

### 7. Ambiguous Multi-Tier Hysteresis State Machine Specification - Severity: Major
* **Reviewer Lens:** `egm-implementation-readiness`
* **Affected Scope:** Lines 413–420 (`bitsignal/alerts/dispatcher.py`), cross-referencing Lines 200–213
* **Discrepancy Description**: 
  Section 14 describes hysteresis using a 5-point deadband for Tier 1 Top (must drop below 75 before re-alerting at 80) and Bottom (must rise above 25 before re-alerting at 20). However, the system defines three Top alert tiers: Tier 1 (80), Tier 2 (85), and Tier 3 (90). The plan does not specify the state transitions or deadbands between intermediate tiers (e.g., if the score oscillates between 84.8 and 85.2, or reaches 86, falls to 81, and rises back to 86). 
* **Rationale & Recommendation**: 
  Define a formal state machine enum (e.g., `NEUTRAL`, `TOP_TIER_1`, `TOP_TIER_2`, `TOP_TIER_3`, `BOTTOM_CAPITULATION`) and specify exact re-arming deadband thresholds for each tier transition (e.g., Tier 2 re-arms only after dropping below 80, Tier 3 re-arms only after dropping below 85).

---

### 8. Database Schema Omission of Hysteresis State and Raw OHLCV History - Severity: Major
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** Lines 368–371 (`bitsignal/storage/db.py`), cross-referencing Lines 218–258
* **Discrepancy Description**: 
  1. Section 14 and Section 5 require tracking the active hysteresis state across daemon runs. However, neither `daily_scores` nor `alert_dispatches` contains a column storing `current_hysteresis_state`.
  2. `raw_snapshots` (Line 219) only stores pre-calculated indicators (`sma_111`, `sma_350`, `rsi_14w`, etc.) and `btc_price`, omitting raw OHLCV candles and raw daily hashrates. Without raw historical OHLCV data stored in the database, recalculating moving averages or backtesting indicator calibration changes offline requires re-fetching years of data from external APIs.
* **Rationale & Recommendation**: 
  Add `hysteresis_state TEXT NOT NULL` to `daily_scores` or create an explicit `system_state` key-value table. Extend `raw_snapshots` (or define a `market_candles` table) to persist raw daily `open, high, low, close, volume` and `network_hashrate`.

---

### 9. Incomplete Verification Test Coverage (Missing Storage & Ingestion Tests) - Severity: Major
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 449–464 (Test Suite Targets), Lines 488–494 (Verification Plan Pass Criteria)
* **Discrepancy Description**: 
  Section 3 of the Verification Plan mandates: *"minimum 85% branch coverage across `bitsignal/engine`, `bitsignal/integrity`, and `bitsignal/storage`"*. However, the target files list only defines 4 test modules: `test_normalizer.py`, `test_integrity.py`, `test_indicators.py`, and `test_alerts.py`. There is no test file for persistence (`tests/test_storage.py` or `tests/test_db.py`) or ingestion connectors (`tests/test_ingest.py`). 
* **Rationale & Recommendation**: 
  Add `tests/test_storage.py` (covering SQLite WAL operations, upsert idempotency, and query filters) and `tests/test_ingest.py` (mocking API responses, retry behavior, and timeouts) to the Target Files list.

---

### 10. Discrepancy in Tier 3 Divestment Tranche Percentage - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 418 (`bitsignal/alerts/dispatcher.py`), cross-referencing Line 212 and Line 13
* **Discrepancy Description**: 
  Line 418 specifies runbook allocations as "(Tier 1: 20%, Tier 2: 30%, Tier 3: 50%)". In contrast, Line 212 defines Tier 3 as "Stage additional 10% tranche (40% cumulative)", and Line 13 cites "(30% to 40%)". 
* **Rationale & Recommendation**: 
  Standardize the runbook percentages across all sections (e.g., clarify whether Tier 2 and Tier 3 refer to incremental tranches or cumulative totals: Tier 1: 20%, Tier 2: +10% [30% cumulative], Tier 3: +10% [40% cumulative]).

---

### 11. Discrepancy in Default SQLite Database Location - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Line 352 (`.env.example`), cross-referencing Line 324 (Non-Functional Requirements)
* **Discrepancy Description**: 
  Line 352 specifies the default database path as `./data/bitsignal.db`, while Line 324 specifies `~/.bitsignal/bitsignal.db or local project root`.
* **Rationale & Recommendation**: 
  Unify the default database location across `.env.example` and the documentation to `./data/bitsignal.db` (with automatic directory creation).
