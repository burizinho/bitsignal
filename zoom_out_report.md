# Stage 5 Initial Zoom Out Architectural Review: Bitcoin Macro Cycle Sentinel (BitSignal)

**Target Document**: [`docs/designs/bitcoin_macro_cycle_sentinel.md`](file:///d:/Projetos%20Gui/BitSignal/docs/designs/bitcoin_macro_cycle_sentinel.md#L1-L523)  
**Evaluator**: Skeptical Architect (Zoom Out Goldfish)  
**Primary Focus**: High-altitude architecture, minimalism, YAGNI, dependency reuse, and core value proposition.

---

### Executive Summary

BitSignal gets several key architectural decisions right: it explicitly rejects enterprise bloat (Alternative 3 correctly eliminates Docker Compose, Kafka, Celery, and PostgreSQL in favor of a single SQLite database in WAL mode), focuses on a sovereign daily batch model, and incorporates alert hysteresis with a data integrity circuit breaker.

However, the design exhibits noticeable **structural over-engineering** (23 target files and an abstract inheritance hierarchy for 3 static daily GET requests), **premature feature creep** (speculative smart-home webhooks and a long-running sleeping daemon), and a **critical data dependency gap** (leaving the data provider for 45% of the score as an unresolved "Open Question" while specifying granular database tables and UI gauges).

---

### Prioritized Findings & Architectural Action Items

#### 1. [Blocker] Critical Data Dependency Left Unresolved for 45% of Composite Score
* **Affected Scope**: Section "Open Questions" (Lines 43–46), Section 1 "Ingestion Layer" (Lines 150–153), Section 3 "Circuit Breaker" (Lines 183–199).
* **Simplicity Rationale**:
  - The design assigns **45% aggregate weight** to on-chain metrics: MVRV Z-Score (25%) and Puell Multiple (20%).
  - At the same time, the circuit breaker trips and freezes all phase alerts if missing metric weight exceeds **20%**.
  - Yet, Question 1 admits that finding a free, reliable, historical and live daily series for Realized Cap / MVRV Z-score is an open question. Free CoinGecko and Blockchain.com endpoints do not provide free, automated programmatic MVRV Z-Score series without authentication or paid enterprise tiers.
  - Designing granular Pydantic models, SQL tables, and UI graphs before locking down the exact zero-cost data provider contract for nearly half the score is an inverted dependency. If no stable zero-cost MVRV endpoint exists, the system will immediately trip into `CIRCUIT_BREAKER_TRIPPED` on Day 1.
* **Recommendation**:
  - Resolve Open Question 1 directly in the architectural design before implementation. Define the primary zero-cost on-chain source (e.g. specific Dune API execution, BGeometrics free tier, or public GitHub daily mirror dataset) and specify an explicit fallback.
  - Alternatively, adjust baseline weights or allow an offline/fallback calibration mode for Phase 1.

---

#### 2. [Major] YAGNI: Long-Running Sleeping Daemon (`bitsignal/daemon.py`)
* **Affected Scope**: Detailed Implementation Plan, Target File 18 (Lines 445–448).
* **Simplicity Rationale**:
  - BitSignal runs strictly **once every 24 hours** at UTC 00:05 and finishes in under 15 seconds.
  - Proposing a custom Python process that stays resident in memory 24/7, sleeping for 23 hours and 59 minutes, introduces memory leak risks, process crash vulnerabilities, and daemon monitoring overhead.
  - Operating systems already possess rock-solid, zero-maintenance tools for running periodic daily jobs: standard `cron` (Linux/macOS), `systemd.timer`, or Windows Task Scheduler.
* **Recommendation**:
  - Eliminate `bitsignal/daemon.py` entirely.
  - The CLI command `python -m bitsignal run-daily` is the single execution contract. Provide a 3-line crontab example (`5 0 * * * /path/to/venv/bin/python -m bitsignal run-daily`) in `README.md`.

---

#### 3. [Major] YAGNI & Scope Creep: Speculative Local Webhook Infrastructure
* **Affected Scope**: Open Question 2 (Lines 45–46), Persistence Schema `alert_dispatches` (Lines 255), Dispatcher (Lines 418–419).
* **Simplicity Rationale**:
  - BitSignal is designed to alert an allocator during macro cycle extremes (Score $\ge 80$ or $\le 20$). These events occur approximately 5 to 10 times across an entire **4-year cycle**.
  - Engineering a dual-channel dispatch engine with configurable webhook signing, custom JSON payloads for Home Assistant / JARVIS, retry loops, and separate database delivery flags (`delivered_webhook`) violates YAGNI.
  - Telegram push notifications reach the operator directly on mobile and desktop, fulfilling 100% of the operational requirement for cold-storage rebalancing runbooks.
* **Recommendation**:
  - Drop the local webhook dispatcher and `delivered_webhook` column for MVP.
  - Focus strictly on Telegram Markdown alerts. Webhook integrations can be deferred until an actual consumer exists.

---

#### 4. [Major] Over-Fragmentation & Class Hierarchy in Ingestion Layer
* **Affected Scope**: Architectural Overview (Lines 138–154), Target Files 7–10 (`bitsignal/ingest/*`, Lines 372–387).
* **Simplicity Rationale**:
  - The design specifies an abstract base class `BaseConnector` (`base.py`) subclassed by three separate modules: `binance.py`, `mempool.py`, and `onchain.py`.
  - In reality, the system makes only 3 simple HTTP GET requests once per day. Spreading 3 HTTP calls across 4 distinct files with object-oriented inheritance is Java-style over-abstraction.
* **Recommendation**:
  - Consolidate the entire ingestion layer into a single, cohesive module (`bitsignal/ingestion.py`).
  - Standardize on a single configured `requests.Session` with `tenacity` retry decorators and simple fetching functions.

---

#### 5. [Nit] Undefined Continuous Normalization for Pi Cycle Indicator
* **Affected Scope**: Section 2 "Metric Calibration & Attribution Matrix" (Line 177).
* **Simplicity Rationale**:
  - The calibration table specifies:
    `Pi Cycle Top / Bottom | 15% | Bottom cross active ($S_i = 0$) | Top cross active ($S_i = 100$) | Piecewise: Top spread vs Bottom spread`
  - While Hash Ribbon explicitly defines a neutral baseline score ($S_i = 50$) when no cross is active, the Pi Cycle entry is mathematically ambiguous for the 99% of days where neither cross is active.
  - If it measures "Top spread vs Bottom spread", the exact formula and clamping boundaries must be defined to avoid arbitrary runtime crashes or score discontinuities.
* **Recommendation**:
  - Explicitly document the neutral / non-crossover formulation for Pi Cycle in the calibration matrix (e.g. ratio of $\text{SMA}_{111} / (2 \times \text{SMA}_{350})$ mapped linearly, with 50 at midpoint).

---

#### 6. [Nit] Heavy Presentation Dependencies in Core Package
* **Affected Scope**: Target File 1 `pyproject.toml` (Line 344), Target File 16 `bitsignal/ui/app.py` (Lines 428–435).
* **Simplicity Rationale**:
  - Putting `streamlit` and `plotly` in core dependencies bloats headless execution environments with heavy web server and compilation dependencies (>250MB).
* **Recommendation**:
  - Keep `streamlit` and `plotly` in optional extra dependencies: `pip install -e ".[ui]"`. The core batch sentinel should remain lightweight with minimal dependencies (`requests`, `pandas`, `pydantic`, `pyyaml`, `tenacity`).

---

### Summary Checklist for Plan Refinement

| Action Item | Severity | Recommended Change |
| :--- | :--- | :--- |
| **Lock Down On-Chain Data Source** | Blocker | Resolve Question 1; specify concrete zero-cost endpoint for MVRV Z-Score / Realized Cap before coding. |
| **Eliminate Custom Daemon** | Major | Remove `bitsignal/daemon.py`; rely on OS `cron` / Task Scheduler calling `python -m bitsignal run-daily`. |
| **Prune Webhook Dispatcher** | Major | Remove local webhook logic, Open Question 2, and `delivered_webhook` DB schema; keep Telegram only. |
| **Consolidate Ingest Hierarchy** | Major | Collapse `bitsignal/ingest/*` (4 files) into a single functional `bitsignal/ingestion.py`. |
| **Formulate Pi Cycle Mapping** | Nit | Define non-crossover state for Pi Cycle to match the explicit neutrality of Hash Ribbon. |
| **Decouple UI Dependencies** | Nit | Move `streamlit` and `plotly` to optional `[ui]` package extras in `pyproject.toml`. |
