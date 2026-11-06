# Consolidated Review Report: Bitcoin Macro Cycle Sentinel (BitSignal)

**Target Document**: [`docs/designs/bitcoin_macro_cycle_sentinel.md`](file:///d:/Projetos%20Gui/BitSignal/docs/designs/bitcoin_macro_cycle_sentinel.md#L1-L523)  
**Execution Mode**: Uninterrupted Full Flow (Stages 5, 6, 7, 8, 9)  
**Date**: 2026-11-05  

---

## 1. Executive Summary

Across all five review lenses—Strategic Architecture (`egm-zoom-out`), Naive Comprehension (`egm-comprehension`), Antagonistic Design & Style (`egm-design`, `egm-structural`, `egm-style`), Intermediate Synthesis (`egm-zoom-out`), and Implementation Readiness (`egm-implementation-readiness`, `egm-codebase-details`)—the BitSignal design was evaluated as **fundamentally viable, mathematically sound in principle, and well-proportioned** for a sovereign, zero-cost macro cycle sentinel.

However, the review protocol revealed critical discrepancies, missing mathematical formulas, and creeping implementation bloat:
1. **Critical Contradictions & Mathematical Gaps**: The design had conflicting cold-storage divestment schedules (30–40% vs. 100%), missing intermediate formulas for Pi Cycle normalization, inverted Hash Ribbon scoring (which pushed bottom buy signals toward top exit tiers), and unresolved zero-cost endpoints for 45% of the scoring engine.
2. **Structural Over-Engineering & YAGNI Violations**: The design specified a 24/7 sleeping background daemon (instead of standard OS cron), speculative smart-home webhooks, an over-abstracted 4-file OOP ingestion hierarchy for 3 daily HTTP requests, and bundled heavy UI dependencies (`streamlit`, `plotly`) into the headless core engine.

This consolidated report synthesizes all 18 deduplicated findings into prioritized, actionable remediation tasks with an exhaustive Traceability Matrix.

---

## 2. Prioritized Action Items

### 🔴 Blockers (Must resolve before code construction)

#### Action Item 1: Standardize Staged Cold-Storage Divestment Tranches
* **Finding Sources**: Stage 6 #1, Stage 7 #1, Stage 9 #10
* **Issue**: Overview cites 30–40% divestment; Goals cites 20%, 30%, 50% (summing to 100%); Alerting defines Tier 1 = 20%, Tier 2 = +10% (30% cum), Tier 3 = +10% (40% cum); Backtest cites 30%.
* **Remediation**: Standardize all sections (Overview, Goals, CUJ 1, Alerting Engine, Models, Dispatcher) to an explicit, uniform schedule:
  - **Tier 1 (Score 80–84)**: Stage 20% divestment tranche.
  - **Tier 2 (Score 85–89)**: Stage additional 10% tranche (30% cumulative).
  - **Tier 3 (Score $\ge 90$)**: Stage additional 10% tranche (40% cumulative exit maximum).
  - **Core Baseline**: 60% of cold storage is permanently retained as a sovereign hodl reserve.

#### Action Item 2: Formulate Continuous Pi Cycle Normalization Metric
* **Finding Sources**: Stage 5 #5, Stage 6 #2, Stage 7 #2, Stage 9 #1
* **Issue**: Pi Cycle Top ($\text{SMA}_{111} \ge 2 \times \text{SMA}_{350}$) and Bottom ($\text{EMA}_{150} \times 0.745 \le \text{SMA}_{471}$) are discrete crossing conditions. No scalar metric or piecewise formula exists for the >95% of days where neither cross is active.
* **Remediation**: Define the continuous evaluation metric as the **Top Proximity Spread Ratio**:
  $$R_{\text{top}} = \frac{\text{SMA}_{111}}{2 \times \text{SMA}_{350}}$$
  - Clamped between $\text{Min} = 0.70$ (Score = 0) and $\text{Max} = 1.00$ (Score = 100).
  - If Pi Cycle Bottom is triggered ($\text{EMA}_{150} \times 0.745 \le \text{SMA}_{471}$), score clamps directly to 0.
  - In normal regimes, $R_{\text{top}}$ maps linearly to sub-score $S_{\text{picycle}} \in [0, 100]$ with neutral midpoint ~50.

#### Action Item 3: Pin Concrete Free On-Chain Data Endpoints & Close Open Question 1
* **Finding Sources**: Stage 5 #1, Stage 6 #3, Stage 7 #8, Stage 9 #2
* **Issue**: MVRV Z-Score (25%) and Puell Multiple (20%) total 45% of composite weight. The circuit breaker trips at >20% missing weight. Leaving the endpoint as an unresolved "Open Question" guarantees day-one failure.
* **Remediation**: Pin concrete endpoints in the design:
  - **Primary**: Community Dune API execution query endpoint for daily MVRV Z-Score and Puell Multiple with API key configured via `.env`.
  - **Cold Fallback**: GitHub-mirrored daily public CSV dataset (raw daily historical series).
  - Delete Open Question 1 from the approved specification.

#### Action Item 4: Correct Hash Ribbon Sub-Score Values to Prevent Signal Inversion
* **Finding Sources**: Stage 6 #4, Stage 7 #3, Stage 8 #3
* **Issue**: Line 402 mapped `Buy Recovery = 85`, which added 8.5 points and pulled the composite score *upward* toward the top exit zone ($\ge 80$), inverted from its true identity as a macro bottom confirmation.
* **Remediation**: Align all references to the following sub-scores:
  - `NORMAL`: 50 (neutral, contributes $50 \times 10\% = 5.0$ pts).
  - `CAPITULATION`: 20 (miner distress, pulls composite score down toward bottom zone).
  - `BUY_RECOVERY`: 10 (confirmed bottom pivot, pulls score strongly toward $\le 20$ DCA accumulation).

#### Action Item 5: Add Missing Package Entrypoint (`__main__.py`) & Project Scripts
* **Finding Sources**: Stage 9 #3
* **Issue**: Running `python -m bitsignal <cmd>` fails with `No module named bitsignal.__main__`.
* **Remediation**: Add `bitsignal/__main__.py` to target files list (forwarding `sys.argv` to `bitsignal.cli.main()`), and add `[project.scripts] bitsignal = "bitsignal.cli:main"` in `pyproject.toml`.

---

### 🟡 Major (Architecture, Reliability & YAGNI)

#### Action Item 6: Paginate Binance Ingestion for 200-Week SMA / Weekly Candles
* **Finding Sources**: Stage 7 #4, Stage 9 #6, Stage 8 #3
* **Issue**: Binance API `GET /api/v3/klines` limits responses to 1,000 candles. Computing the 200-week SMA from daily candles requires 1,400 daily bars.
* **Remediation**: Fetch 208 weekly candles (`GET /api/v3/klines?symbol=BTCUSDT&interval=1w&limit=208`) specifically for 200-week SMA and 14-week RSI. Reduces request size by 85% and eliminates pagination complexity.

#### Action Item 7: Eliminate Long-Running Daemon (`bitsignal/daemon.py`)
* **Finding Sources**: Stage 5 #2, Stage 8 #B
* **Issue**: Running a 24/7 Python process that sleeps 23h 59m daily introduces memory leak, crash, and watchdog overhead for a 10-second daily batch task.
* **Remediation**: Remove `bitsignal/daemon.py`. Use OS cron (`5 0 * * * /path/to/venv/bin/python -m bitsignal run-daily`), `systemd.timer`, or Windows Task Scheduler. Document the 1-line cron configuration in `README.md`.

#### Action Item 8: Prune Speculative Smart-Home Webhook Infrastructure
* **Finding Sources**: Stage 5 #3, Stage 8 #D
* **Issue**: Alerts trigger 5–10 times across an entire 4-year cycle. Multi-channel webhook dispatch with database delivery tracking is speculative bloat.
* **Remediation**: Remove local webhook logic, Open Question 2, and `delivered_webhook` column from `alert_dispatches`. Standardize on Telegram Markdown push notifications.

#### Action Item 9: Consolidate Ingestion Hierarchy into Single Module
* **Finding Sources**: Stage 5 #4, Stage 8 #C
* **Issue**: 4 files creating an abstract base class `BaseConnector` and 3 subclasses for 3 simple daily HTTP GET requests is OOP over-abstraction.
* **Remediation**: Replace `bitsignal/ingest/*` (4 files) with a single, cohesive `bitsignal/ingestion.py` sharing a configured `requests.Session` with `tenacity` retries and 10s timeouts.

#### Action Item 10: Replace Volatile Weight Rescaling with Neutral Baseline Imputation
* **Finding Sources**: Stage 7 #5, Stage 8 #A
* **Issue**: Dynamically rescaling weights ($w'_k = \frac{w_k}{1 - W_{\text{missing}}}$) during `DEGRADED` status inflates remaining metrics and distorts neutral states, creating synthetic threshold breakouts.
* **Remediation**: When an indicator is stale $\le 48h$, impute its neutral score ($S_i = 50$) rather than rescaling weights. Preserves $\sum w_i = 1.0$, prevents artificial score spikes, and records `status: DEGRADED` in logs.

#### Action Item 11: Specify Multi-Tier Alert Hysteresis State Machine & Schema Persistence
* **Finding Sources**: Stage 6 #5, Stage 7 #6, Stage 9 #7, Stage 9 #8
* **Issue**: Hysteresis was defined for entering/leaving top zone (80 vs 75), but omitted intermediate tier transitions (85, 90). Database schema lacked `hysteresis_state` column.
* **Remediation**: Define formal enum: `NEUTRAL`, `TOP_TIER_1` ($\ge 80$), `TOP_TIER_2` ($\ge 85$), `TOP_TIER_3` ($\ge 90$), `BOTTOM_CAPITULATION` ($\le 20$). Enforce deadbands: Tier 2 re-arms only below 82; Tier 3 re-arms only below 87. Add `hysteresis_state TEXT NOT NULL` to `daily_scores`.

#### Action Item 12: Widen Timestamp Staleness Window for Daily Metrics
* **Finding Sources**: Stage 7 #7
* **Issue**: Checking $\le 24h$ at UTC 00:05 against daily candles published at 00:00 causes metrics to oscillate into `STALE` on minor API publication lag.
* **Remediation**: Widen the `FRESH` threshold to $\le 36$ hours for 1-day interval data, preserving 48 hours as the hard `EXPIRED` limit.

#### Action Item 13: Correct Mempool.space Hashrate API Route
* **Finding Sources**: Stage 9 #5
* **Issue**: Route `/mining/hashrate/pools/1m` provides mining pool market share percentages, not aggregate network hashrate time series.
* **Remediation**: Point connector to `mempool.space/api/v1/mining/hashrate/3m` (returning `{ timestamp, avgHashrate }` series).

#### Action Item 14: Add Dedicated Unit Tests for Storage and Ingestion
* **Finding Sources**: Stage 9 #9
* **Issue**: Verification Plan required 85% coverage on storage and engine, but Target Files omitted `tests/test_storage.py` and `tests/test_ingestion.py`.
* **Remediation**: Add `tests/test_storage.py` (SQLite WAL, upserts, schema migration) and `tests/test_ingestion.py` (mocked HTTP responses, timeouts, retries) to Target Files.

---

### 🟢 Nits (Code Quality, Usability & Documentation)

#### Action Item 15: Decouple UI Dependencies into Optional Extra
* **Finding Sources**: Stage 5 #6, Stage 8 #F
* **Issue**: Putting `streamlit` and `plotly` in core dependencies bloats headless CLI cron environments (>300MB).
* **Remediation**: Configure `[project.optional-dependencies] ui = ["streamlit>=1.30.0", "plotly>=5.18.0"]` in `pyproject.toml`.

#### Action Item 16: Clarify Weekly RSI Calculation Window
* **Finding Sources**: Stage 6 #6, Stage 7 #10
* **Issue**: Unclear whether weekly RSI is calculated on Sunday closes or rolling daily intervals.
* **Remediation**: Specify rolling 7-day intervals sampled daily at UTC 00:05 to ensure continuous daily score sensitivity.

#### Action Item 17: Unify SQLite Default Database Location
* **Finding Sources**: Stage 9 #11
* **Issue**: Discrepancy between `.env.example` (`./data/bitsignal.db`) and NFR text (`~/.bitsignal/bitsignal.db`).
* **Remediation**: Standardize to `./data/bitsignal.db` with automatic directory creation.

#### Action Item 18: Define Acronyms (UTXO, IBD) and Benchmark Latency Scope
* **Finding Sources**: Stage 6 #7, Stage 7 #12
* **Issue**: Unexpanded acronyms in text and undefined dataset sizing for UI latency NFR.
* **Remediation**: Expand `UTXO` (Unspent Transaction Output) and `IBD` (Initial Block Download). Clarify UI latency benchmark as $<500$ ms across 5,200 historical rows on a 4-core, 8 GB RAM host.

---

## 3. Traceability Matrix

| Raw Finding ID | Review Stage & Lens | Primary Action Item | Target Document Section Affected |
| :--- | :--- | :--- | :--- |
| **Z5-1** | Stage 5 (Zoom Out): Unresolved Data Source | **Action Item 3** | Open Questions, Section 1 Ingestion |
| **Z5-2** | Stage 5 (Zoom Out): YAGNI Sleeping Daemon | **Action Item 7** | Section 18 Daemon, Verification Plan |
| **Z5-3** | Stage 5 (Zoom Out): YAGNI Webhooks | **Action Item 8** | Open Questions, Alerting, Storage |
| **Z5-4** | Stage 5 (Zoom Out): Ingestion Hierarchy | **Action Item 9** | Target Files 7–10, Architecture |
| **Z5-5** | Stage 5 (Zoom Out): Pi Cycle Intermediate Formula | **Action Item 2** | Section 2 Normalization Matrix |
| **Z5-6** | Stage 5 (Zoom Out): UI Dependency Diet | **Action Item 15** | `pyproject.toml` |
| **C6-1** | Stage 6 (Comprehension): Contradictory Tranches | **Action Item 1** | Overview, Goals, Alerting, Verification |
| **C6-2** | Stage 6 (Comprehension): Pi Cycle Normalization | **Action Item 2** | Section 2 Normalization Matrix |
| **C6-3** | Stage 6 (Comprehension): Unresolved On-Chain Source | **Action Item 3** | Open Questions, Section 1 Ingestion |
| **C6-4** | Stage 6 (Comprehension): Hash Ribbon Scoring Inversion | **Action Item 4** | Section 2 Normalization, Engine |
| **C6-5** | Stage 6 (Comprehension): Multi-Tier Hysteresis | **Action Item 11** | Section 4 Alerting, Section 14 Dispatcher |
| **C6-6** | Stage 6 (Comprehension): Weekly RSI Window | **Action Item 16** | Section 1 Ingestion, Section 11 Engine |
| **C6-7** | Stage 6 (Comprehension): Undefined Acronyms | **Action Item 18** | Alternatives Considered |
| **CR7-1** | Stage 7 (Critic): Contradictory Tranches | **Action Item 1** | Overview, Goals, Alerting, Backtest |
| **CR7-2** | Stage 7 (Critic): Pi Cycle Dual-Curve Normalization | **Action Item 2** | Section 2 Normalization Matrix |
| **CR7-3** | Stage 7 (Critic): Hash Ribbon Inversion | **Action Item 4** | Section 2 Normalization, Engine |
| **CR7-4** | Stage 7 (Critic): Binance 1000-Candle Limit | **Action Item 6** | Section 1 Ingestion, Binance Connector |
| **CR7-5** | Stage 7 (Critic): Weight Rescaling Distortion | **Action Item 10** | Section 3 Circuit Breaker, Engine |
| **CR7-6** | Stage 7 (Critic): Inter-Tier Hysteresis | **Action Item 11** | Section 4 Alerting, Section 14 Dispatcher |
| **CR7-7** | Stage 7 (Critic): Timestamp Staleness 24h vs 36h | **Action Item 12** | Section 3 Circuit Breaker |
| **CR7-8** | Stage 7 (Critic): Open Questions in Approved Spec | **Action Item 3, 8** | Open Questions |
| **CR7-9** | Stage 7 (Critic): Incomplete CUJ Coverage | **Action Item 10, 11** | Critical User Journeys |
| **CR7-10**| Stage 7 (Critic): Weekly RSI Cadence | **Action Item 16** | Section 1 Ingestion |
| **CR7-11**| Stage 7 (Critic): Vague On-Chain Endpoints | **Action Item 3** | Section 1 Ingestion |
| **CR7-12**| Stage 7 (Critic): Dashboard Latency Sizing | **Action Item 18** | Non-Functional Requirements |
| **IR9-1** | Stage 9 (Readiness): Undefined Pi Cycle Bounds | **Action Item 2** | Target Files 11–12, Normalization |
| **IR9-2** | Stage 9 (Readiness): Unresolved Data Contract | **Action Item 3** | Target File 10, Open Questions |
| **IR9-3** | Stage 9 (Readiness): Missing `__main__.py` | **Action Item 5** | Target File 4, `pyproject.toml` |
| **IR9-4** | Stage 9 (Readiness): Missing `yfinance` Dependency | **Action Item 6** | `pyproject.toml` |
| **IR9-5** | Stage 9 (Readiness): Mempool Endpoint Mismatch | **Action Item 13** | Target File 9 |
| **IR9-6** | Stage 9 (Readiness): Binance 1000-Candle Limit | **Action Item 6** | Target File 8 |
| **IR9-7** | Stage 9 (Readiness): Multi-Tier State Machine | **Action Item 11** | Target File 14, Models |
| **IR9-8** | Stage 9 (Readiness): DB Schema Missing State | **Action Item 11** | Target File 6 (Storage) |
| **IR9-9** | Stage 9 (Readiness): Incomplete Test Files | **Action Item 14** | Target Files 19–22 |
| **IR9-10**| Stage 9 (Readiness): Tier 3 Divestment Discrepancy | **Action Item 1** | Target File 14 |
| **IR9-11**| Stage 9 (Readiness): Default DB Path Discrepancy | **Action Item 17** | `.env.example`, NFRs |
| **IZ8-A** | Stage 8 (Intermediate): Dynamic Rescaling vs Imputation | **Action Item 10** | Section 3 Circuit Breaker |
| **IZ8-B** | Stage 8 (Intermediate): Daemon Elimination | **Action Item 7** | Target Files, Verification Plan |
| **IZ8-C** | Stage 8 (Intermediate): Ingestion Hierarchy Pruning | **Action Item 9** | Target Files 7–10 |
| **IZ8-D** | Stage 8 (Intermediate): Webhook Pruning | **Action Item 8** | Open Questions, Target File 14 |
| **IZ8-E** | Stage 8 (Intermediate): Database Simplicity | **Action Item 11** | Target File 6 |
| **IZ8-F** | Stage 8 (Intermediate): UI Dependency Diet | **Action Item 15** | `pyproject.toml` |

---

## 4. Next Steps & Recommended Action

1. **Apply Remediation to Design Document**: Update [`docs/designs/bitcoin_macro_cycle_sentinel.md`](file:///d:/Projetos%20Gui/BitSignal/docs/designs/bitcoin_macro_cycle_sentinel.md) by applying the 18 action items directly (updating tranche schedules, inserting the Pi Cycle spread formula, pinning the on-chain endpoint, fixing Hash Ribbon sub-scores, consolidating ingestion files, and eliminating the daemon and webhooks).
2. **Review Resolved Specification**: Once updated, the document will stand at 100% implementation readiness with zero open blockers.
