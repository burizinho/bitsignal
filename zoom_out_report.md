# Zoom Out Architectural Review Report: Estratégia de Ciclo Macro com Gestão Tributária Nacional

**Target Document:** `docs/designs/bitcoin_national_execution_strategy.md` (lines 1..349)  
**Standard:** `resources/document_standards/zoom-out-standard.md`  
**Reviewer:** Skeptical Architect (Zoom Out Goldfish)  
**Date:** 2026-11-06  

---

## Executive Summary

The proposed design establishes a deterministic, macro-cycle execution strategy tailored for Brazilian tax jurisdiction (< 0.5 BTC positions). The core motivation and user journeys (CUJs) are well articulated and address real friction points (Sunday execution, R$ 35k exemption thresholds, and emotional indiscipline).

However, from an architectural simplicity, YAGNI, and codebase health perspective, the proposal suffers from:
1. **Redundant state management and dual sources of truth** in the database layer (caching derived metrics and JSON arrays in SQLite tables for a system that will process < 50 transactions per 4-year cycle).
2. **Unresolved product and architectural clash** between the existing BitSignal Core philosophy (strict 60% sovereign reserve baseline) and the new Strategy (90% to 100% liquidation).
3. **Reinventing the wheel** by creating new moving average indicator modules when vectorized `calculate_sma` and `calculate_ema` already exist in `bitsignal.engine.indicators`.
4. **Speculative external dependencies (YAGNI)** such as BACEN PTAX APIs when national BTC/BRL trades are executed and taxed directly in BRL.
5. **Altitude drops into low-level implementation weeds** (incomplete and buggy Python pseudocode embedded in the architectural design).

---

## Detailed Findings

### 🔴 Blocker Findings

#### 1. Redundant State Caching & Dual Sources of Truth in SQLite
* **Affected Scope:** Section 3 (lines 167–215), Detailed Plan (lines 317, 332–334)
* **Simplicity Rationale:**  
  The design introduces three interconnected SQLite tables: `portfolio_transactions`, `strategy_state`, and `tax_monthly_ledger`.
  - In `strategy_state`, it persists mutable cached values (`current_btc_balance`, `current_cmp_brl`, `allocated_reserve_brl`) and a serialized JSON string (`executed_stages TEXT`) constrained to `CHECK (id = 1)`.
  - In `tax_monthly_ledger`, it stores pre-computed monthly totals (`total_alienated_brl`, `gross_capital_gain_brl`, `darf_amount_due`).
  
  For a 4-year macro DCA strategy, an individual will record at most 20 to 50 transactions across the entire multi-year cycle. Storing derived state in secondary caching tables introduces cache invalidation nightmares, risk of state drift, and synchronization failures if a user edits or corrects an erroneous transaction.
* **Recommendation:**  
  Adhere to single-source-of-truth ledger design. Keep `portfolio_transactions` as the sole append-only transactional source of truth. Current balance, weighted average acquisition cost (CMP), monthly alienation volume, and DARF due can be calculated on demand in microseconds (or queried via lightweight SQL views). Eliminate `strategy_state` and `tax_monthly_ledger` as persistent tables.

---

#### 2. Architectural & Philosophical Collision with BitSignal Core
* **Affected Scope:** Goals & CUJs (lines 33–34, 83–91), Architecture Diagram (lines 101–130), Implementation Plan (line 318); existing `config/config.yaml` (lines 46–68) & `bitsignal/alerts/dispatcher.py` (lines 39, 64)
* **Simplicity Rationale:**  
  BitSignal's existing core design and Telegram dispatcher enforce a strict **Sovereign Baseline**:
  `sovereign_baseline_pct: 60.0%` ("CEASE FURTHER DIVESTMENT. The remaining 60% is the sovereign reserve", max cumulative divestment 40%).
  In contrast, the new National Strategy mandates exiting **90%** of the portfolio (V1–V5 tranches leave only a 10% Moonbag) and Trailing Stop 2 liquidates **100% of remaining balance** except the 10% Moonbag.
  
  Section 1 claims `Core [BitSignal Core (Intocado)]` remains untouched while dispatching strategy alerts via `bitsignal.alerts.dispatcher`. If both run in parallel, the user will receive conflicting Telegram alerts during a market top (one demanding the retention of 60% baseline custody, the other ordering 90% liquidation). The document fails to define how the system arbitrates or toggles between these two contradictory portfolio paradigms.
* **Recommendation:**  
  Explicitly formalize the relationship between Core Hysteresis alerting and the National Strategy execution. Introduce an operational configuration toggle in `config.yaml` (e.g. `execution_mode: sovereign_hodl | tax_optimized_cycle`) or specify that enabling `bitsignal.strategy` overrides or supersedes Core top-tier divestment alerts.

---

### 🟡 Major Findings

#### 3. Reinventing the Wheel on Indicator Calculations
* **Affected Scope:** Section 2 (lines 136–140), Detailed Plan (lines 313, 322, 339–340)
* **Simplicity Rationale:**  
  The plan specifies creating a new module `bitsignal/strategy/trailing_stops.py` to calculate the 21-week EMA and 50-week SMA (350 days).
  However, `bitsignal.engine.indicators` **already provides** pure functional, vectorized implementations: `calculate_sma` and `calculate_ema`. Furthermore, `sma_350` and `weekly_candles` are already ingested and stored in `daily_metrics`.
  Creating duplicate calculation logic and dedicated unit tests (`test_strategy_trailing_stops.py`) for moving averages introduces unnecessary code to maintain and violates DRY.
* **Recommendation:**  
  Reuse `bitsignal.engine.indicators` directly. `trailing_stops` should simply evaluate conditions against existing indicator series rather than re-implementing mathematical calculations.

---

#### 4. Speculative BACEN PTAX Integration for Domestic BTC/BRL Trades (YAGNI)
* **Affected Scope:** Open Questions (line 55), Schema (line 179), Runbook (line 226)
* **Simplicity Rationale:**  
  The design specifies integrating the Central Bank of Brazil (BACEN) PTAX API with a Yahoo Finance fallback to convert orders to BRL.
  However, Non-Goals (line 48) and Alternative 1 explicitly mandate trading directly on **domestic exchanges in the BTC/BRL pair** with BRL PIX transfers.
  Under Brazilian tax legislation (IN RFB 1.888/2019 and GCAP regulations), transactions executed in national currency (BRL) are taxed based on the **actual execution price and fees on the brokerage statement (nota de corretagem)**. PTAX conversion is only applicable to foreign-currency operations conducted offshore.
  Integrating BACEN PTAX API introduces an external network dependency, rate limit risks, and artificial tax discrepancies between real BRL proceeds and PTAX theoretical estimates.
* **Recommendation:**  
  Remove BACEN PTAX API and `ptax_rate` from the design. Rely strictly on the actual `price_brl` and `fee_brl` from the local trade execution. Reserve PTAX integration for when/if offshore trading is supported (YAGNI).

---

#### 5. Premature Implementation Details & Buggy Pseudocode (Altitude Drop)
* **Affected Scope:** Section 2 (lines 148–161)
* **Simplicity Rationale:**  
  Section 2 drops from architecture into low-level weeds by including an incomplete Python function `evaluate_tax_strategy`. The snippet contains hardcoded values (`part1 = 34500.0`, `darf * 0.15`) and contains scope bugs: line 158 references `quantity_sold` and `current_cmp`, which are undefined in the function signature.
  Architecture documents should define domain rules, contracts, and interfaces, not tentative function implementations.
* **Recommendation:**  
  Replace the concrete Python function with a clean specification table or flowchart defining the business rules:
  - Monthly Volume $\le \text{R\$} 35.000 \rightarrow$ Action: Full Sell, Status: Exempt.
  - $\text{R\$} 35.000 < \text{Volume} \le \text{R\$} 70.000$ AND Date $\ge 25 \rightarrow$ Action: Split (R$ 34.500 now, remainder on 1st of next month), Status: Exempt.
  - All other cases $\rightarrow$ Action: Full Sell, Status: Taxable (DARF 15%).

---

### 🟢 Nit Findings

#### 6. Hardcoded Default Cycle Target in Schema and Fintech Mentions in Runbooks
* **Affected Scope:** Line 190 (`cycle_ath_usd REAL NOT NULL DEFAULT 126000.0`), Line 234 (`CDB de Liquidez Imediata 24/7 (Caixinha / Inter)`)
* **Simplicity Rationale:**  
  - Hardcoding a cycle-specific price (`126000.0`) as a DDL column default bakes temporary market assumptions into the database schema.
  - Hardcoding specific commercial fintech products ("Caixinha / Inter") in Telegram templates couples the engine to specific retail apps.
* **Recommendation:**  
  Configure `cycle_ath_usd` exclusively via `config/config.yaml`. In alerts, use generic phrasing ("CDB de liquidez diária com resgate 24/7").

---

#### 7. Module Over-Fragmentation
* **Affected Scope:** Section 2 (lines 132–164), Table (lines 309–316)
* **Simplicity Rationale:**  
  The plan creates 5 separate files in `bitsignal/strategy/` (`models.py`, `trailing_stops.py`, `national_dca.py`, `tax_br.py`, `weekly_evaluator.py`). For the scope of this feature, dividing logic across 5 files adds file-hopping overhead and boilerplate imports.
* **Recommendation:**  
  Consolidate into 2 or 3 focused modules:
  - `bitsignal/strategy/models.py` (Domain dataclasses/enums)
  - `bitsignal/strategy/tax_br.py` (Ledger, CMP calculation, and RFB tax rules)
  - `bitsignal/strategy/engine.py` (Stops, DCA thresholds, and evaluation orchestration)
