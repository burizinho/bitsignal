# Stage 9: Implementation Readiness Test Report

**Target:** `docs/designs/bitcoin_national_execution_strategy.md` (`lines 303..349`)  
**Standard:** `implementation-readiness-standard`  
**Mode:** REVIEW  

---

## Reviewer Status

| Reviewer | Status |
| :--- | :--- |
| `egm-codebase-details` | **completed** |
| `egm-style` | **completed** |

---

## Severity Breakdown

| Severity | Count | Summary |
| :--- | :---: | :--- |
| 🔴 **Blocker** | **3** | Missing PTAX ingestion client; omitted pipeline orchestration/scheduling wire-up; missing SQLite state seeding & migration logic. |
| 🟡 **Major** | **3** | Circular inclusion of design doc in file list; ambiguous alert dispatcher interface; mathematical/sampling ambiguity in 21w EMA / 50w SMA calculation. |
| 🟢 **Nit** | **2** | CLI subparser argument specification missing; lack of test coverage for PTAX API failure fallback. |

---

## Prioritized Findings (Blockers ➔ Major ➔ Nits)

### 🔴 Blocker 1: Missing PTAX Ingestion Module / BACEN API Client in File Enumeration
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `lines 307-326` (Lista Unificada de Arquivos Impactados), `lines 55, 179`
* **Discrepancy Description:** 
  The design document explicitly mandates official BACEN PTAX rate ingestion with Yahoo Finance fallback (`BRL=X`) for legal consistency with Receita Federal rules (line 55), and defines `ptax_rate REAL NOT NULL` in the `portfolio_transactions` table (line 179). However, the implementation plan's file table (lines 309–326) completely omits any module responsible for fetching PTAX. Neither `bitsignal/ingestion.py` is listed as modified nor is a new client module (e.g. `bitsignal/strategy/ptax.py`) enumerated.
* **Rationale & Recommendation:** 
  A developer cannot implement the tax engine without knowing where PTAX data originates. Add `bitsignal/strategy/ptax.py` (or modify `bitsignal/ingestion.py`) to the file list, specifying the official BACEN Olinda OData API endpoint (`https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/...`), timeout parameters, retry policies via `tenacity`, and fallback to `yfinance` (`BRL=X`).

---

### 🔴 Blocker 2: Missing Execution Wire-Up into Daily Automated Pipeline and Sunday Scheduling
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `lines 316, 319, 341-346` (`weekly_evaluator.py`, `cli.py`, Fases 4 e 5)
* **Discrepancy Description:** 
  Section 1 and Section 2 state that `weekly_evaluator.py` must run at Sunday 18:00 BRT (pre-alert) and Sunday 21:01 BRT (weekly close evaluation). However, in `bitsignal/cli.py` (line 319), only manual CLI subcommands are enumerated (`strategy-status`, `strategy-record-tx`, `strategy-eval`, `strategy-tax-report`). There is no specification for wiring strategy evaluation into `cmd_run_daily()`, nor is there any cron / GitHub Actions schedule specified for the Sunday 18:00 BRT trigger.
* **Rationale & Recommendation:** 
  Without automated wire-up, the new strategy engine remains completely inert during production runs. The plan must explicitly specify:
  1. Modification of `cmd_run_daily()` in `bitsignal/cli.py` to invoke `evaluate_weekly_strategy()` when running on Sunday evenings/Monday 00:00 UTC.
  2. A dedicated scheduler or GitHub Actions workflow (`.github/workflows/strategy_sunday.yml` or cron entry) to fire the Sunday 18:00 BRT pre-alert.

---

### 🔴 Blocker 3: Lack of Initial State Seeding and Schema Initialization for `strategy_state`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `lines 188-201, 317, 332-334` (`bitsignal/storage/db.py` & Fase 1)
* **Discrepancy Description:** 
  The schema for `strategy_state` enforces `id INTEGER PRIMARY KEY CHECK (id = 1)` and `total_reserve_brl REAL NOT NULL` (without a SQL `DEFAULT`). When `init_db()` runs on a fresh database, `strategy_state` will have 0 rows. Any evaluation query (`SELECT * FROM strategy_state WHERE id = 1`) will return `None`, throwing unhandled exceptions across all strategy modules. The implementation plan does not detail how row `id=1` is seeded or synchronized with `config/config.yaml`.
* **Rationale & Recommendation:** 
  In `bitsignal/storage/db.py`, specify an explicit database helper `init_strategy_state(total_reserve_brl: float, cycle_ath: float = 126000.0)` that executes:
  ```sql
  INSERT OR IGNORE INTO strategy_state (id, total_reserve_brl, cycle_ath_usd, active_phase)
  VALUES (1, ?, ?, 'ACCUMULATION');
  ```
  and call it during `init_db()` or sync it from `config.yaml` parameters.

---

### 🟡 Major 1: Self-Referential / Circular Inclusion of Target Design Doc in Implementation Plan
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `line 326`
* **Discrepancy Description:** 
  Item 16 of the table lists `docs/designs/bitcoin_national_execution_strategy.md` with action **Criar** and rationale "Documento final de especificação formal aprovado que consolida este design e guia as futuras iterações." The file being reviewed is this exact document. Listing the pre-implementation design document as a work artifact to be created during code implementation is circular and misrepresents the engineering backlog.
* **Rationale & Recommendation:** 
  Remove line 326 from the impacted files table, or change its action tag to `[Existente / Especificação Aprovada]`.

---

### 🟡 Major 2: Unspecified Integration Pattern for Strategy Runbooks in `dispatcher.py`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `line 318, lines 341-343` (`bitsignal/alerts/dispatcher.py` & Fase 4)
* **Discrepancy Description:** 
  The current `bitsignal/alerts/dispatcher.py` is tightly coupled to `DailyCompositeResult` and `AlertType` (`TOP_TIER_1..3`, `BOTTOM_CAPITULATION`, `CIRCUIT_BREAKER`). The plan states "Expandir o formatador do Telegram...", but does not define how strategy events (`StageType`, `TaxStatus`, `TaxExecutionPlan`) are dispatched without polluting or breaking the existing macro cycle sentinel alerts.
* **Rationale & Recommendation:** 
  Define a dedicated public function in `bitsignal/alerts/dispatcher.py`, e.g., `send_strategy_runbook(runbook: StrategyRunbook, bot_token: Optional[str] = None, chat_id: Optional[str] = None) -> bool`, and record strategy alert logs cleanly in `alert_dispatches` without requiring a synthetic `DailyCompositeResult`.

---

### 🟡 Major 3: Ambiguous Candle Resolution and Series Input for `trailing_stops.py`
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `line 313, lines 137-140`
* **Discrepancy Description:** 
  Line 313 describes $\text{EMA}_{21w}$ as "147 dias" and $\text{SMA}_{50w}$ as "350 dias", whereas lines 138–139 define $\text{EMA}_{21w}$ calculated over weekly closes with $\alpha = \frac{2}{21+1}$. A 21-week EMA on weekly bars is mathematically distinct from a 147-day EMA on daily bars. Furthermore, for the Sunday 18:00 BRT pre-alert, the weekly candle has not closed yet.
* **Rationale & Recommendation:** 
  Explicitly specify that `trailing_stops.py` consumes weekly close series (`pd.Series`) constructed from `weekly_candles` (or daily closes resampled to `W-SUN`), reusing `calculate_ema(series, span=21)` and `calculate_sma(series, window=50)` from `bitsignal.engine.indicators`. Clarify that the Sunday 18:00 BRT pre-alert evaluates against a tentative candle containing the latest live spot price.

---

### 🟢 Nit 1: Missing CLI Subparser Argument Specifications for `strategy-record-tx`
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `line 319`
* **Discrepancy Description:** 
  Command `strategy-record-tx` is listed without its CLI arguments. Because `portfolio_transactions` contains mandatory non-null fields (`tx_type`, `stage`, `amount_btc`, `price_usd`, `price_brl`, `ptax_rate`, `exchange`), the CLI specification should declare these options.
* **Rationale & Recommendation:** 
  Enumerate required arguments (`--type {BUY,SELL}`, `--stage`, `--btc`, `--price-usd`, `--price-brl`, `--ptax`, `--exchange`, `--fee-brl`, `--notes`) or specify an interactive terminal prompt wizard (`--interactive`).

---

### 🟢 Nit 2: Test Suite Coverage Gap for PTAX API Failure Modes
* **Reviewer Lens:** `egm-codebase-details`
* **Affected Scope:** `lines 322-325` (Test Files Table)
* **Discrepancy Description:** 
  While `tests/test_strategy_tax_br.py` covers tax calculations and DARF logic, there is no enumerated test for external exchange rate failures (e.g. BACEN API 500 error, timeout, or fallback to Yahoo Finance).
* **Rationale & Recommendation:** 
  Add test scenarios for PTAX ingestion resilience and fallback to `tests/test_strategy_tax_br.py` or a dedicated `tests/test_strategy_ptax.py`.
