## What I Understand This Feature Does (Feature Spec)

The Bitcoin Macro Cycle Sentinel (BitSignal) is a self-hosted, sovereign monitoring tool that tracks macro market cycles to guide long-term investors through market extremes without emotional bias. Operating on a daily batch cadence at UTC 00:05, it collects market price, network hashrate, and on-chain valuation ratios from free public sources and combines them into a deterministic 0–100 Composite Cycle Score using clamped piecewise linear normalization. When the score enters overheated euphoria (≥ 80), it dispatches tiered operational checklists to Telegram and local webhooks to orchestrate staged divestment from cold storage, and when the score indicates capitulation bottoms (≤ 20), it signals staged dollar-cost averaging accumulation. To prevent false alarms and operator fatigue, the system incorporates a 5-point alert hysteresis deadband and an automated data integrity circuit breaker that suspends phase alerts if stale or missing data exceeds 20% of the indicator weight.

## What I Understand The Implementation Will Do (Detailed Implementation)

The system will be implemented as a lightweight Python 3.11+ package (`bitsignal`) backed by an embedded SQLite database running with Write-Ahead Logging (WAL) and an interactive local Streamlit dashboard. A daily scheduler triggers modular connectors (`BinanceConnector` with Yahoo fallback, `MempoolConnector`, and `OnChainConnector`) protected by timeouts and exponential backoff, validates payloads into Pydantic V2 models, and stores raw daily snapshots. An integrity monitor verifies metric timestamps against a 48-hour staleness threshold, dynamically rescaling active weights if missing weight is ≤ 20% or tripping a `CIRCUIT_BREAKER_TRIPPED` state if > 20%. The calculation engine computes moving averages, momentum, and indicator sub-scores, evaluates hysteresis state transitions in SQLite, dispatches markdown alerts via Telegram bots/webhooks, and gates live production alerting behind a Phase 1.5 historical backtest replay spanning 2012–2026.

---

## Comprehension Gaps, Undefined Acronyms, and Ambiguous Mechanisms

### 1. Contradictory Divestment Tranche Allocations
* **Severity**: Blocker
* **Affected Scope**: Section "Overview" (line 13), Section "Goals" (line 31), Section 4 "Alerting Engine" (lines 210–212), Section 6 "Backtesting" (line 268), Section 14 "Dispatcher" (line 418).
* **Discrepancy Description & Rationale**: The document provides contradictory numbers for the divestment runbook tranches:
  - Line 13 states: "guide staged divestment of cold-storage holdings (30% to 40%)".
  - Line 31 states: "(Score 80–84: 20% tranche, 85–89: 30%, >=90: 50%)", implying cumulative 100% or incremental tranches summing to 100%.
  - Lines 210–212 state: "Tier 1: Stage 20% divestment tranche... Tier 2: Stage additional 10% tranche (30% cumulative)... Tier 3: Stage additional 10% tranche (40% cumulative)".
  - Line 268 specifies: "executing 30% staged cold-storage divestment at Tier 1/2".
  - Line 418 specifies: "runbooks (Tier 1: 20%, Tier 2: 30%, Tier 3: 50%)".
  A fresh reader or implementer cannot determine whether Tier 2 and Tier 3 recommend selling 10% increments (maxing out at 40% cold-storage divestment) or selling 30% and 50% tranches (liquidating up to 100% of holdings).

### 2. Missing Mathematical Formulation for Pi Cycle Normalization
* **Severity**: Blocker
* **Affected Scope**: Section 1 "Ingestion Layer" (lines 145–146), Section 2 "Metric Calibration Matrix" (line 177), Section 11 & 12 (lines 394, 400).
* **Discrepancy Description & Rationale**: In the Calibration Matrix (line 177), Pi Cycle is assigned a 15% weight, with Bottom Boundary ($S_i = 0$) defined as "Bottom cross active" and Top Boundary ($S_i = 100$) defined as "Top cross active", with formulation "Piecewise: Top spread vs Bottom spread". While lines 145–146 define the discrete Boolean crossing triggers ($\text{SMA}_{111} \ge 2 \times \text{SMA}_{350}$ and $\text{EMA}_{150} \times 0.745 \le \text{SMA}_{471}$), no continuous mathematical formula is provided for the intermediate days when neither cross is active. The piecewise linear equation in Section 2 (lines 160–165) requires scalar inputs $x_i$, $\text{Min}_i$, and $\text{Max}_i$. Without explicit formulas for the top and bottom spreads, a developer cannot write `evaluate_picycle` or `normalizer.py`.

### 3. Unresolved Free Data Sources for 45% of Indicator Weight
* **Severity**: Blocker
* **Affected Scope**: Section "Open Questions" (lines 44–45), Section 1 "On-Chain Valuation Metrics" (lines 150–153), Section 3 "Circuit Breaker" (lines 195–199).
* **Discrepancy Description & Rationale**: MVRV Z-Score (25% weight) and Puell Multiple (20% weight) represent 45% of the total composite scoring engine. Open Question 1 (line 44) explicitly notes that it is unresolved which free public endpoint provides daily historical and live series for Realized Cap / MVRV Z-Score. Furthermore, standard free tiers for CoinGecko and Blockchain.com do not provide native daily MVRV Z-Score or Puell Multiple, and Dune API queries require paid credits or authenticated keys. Because the system's circuit breaker trips into `CIRCUIT_BREAKER_TRIPPED` whenever missing indicator weight exceeds 20% (lines 195–199), failing to specify a working, zero-cost data source for these two indicators means the system will immediately trip its circuit breaker and freeze alerting on day one.

### 4. Inconsistent Scoring Semantics and States for Hash Ribbon
* **Severity**: Major
* **Affected Scope**: Section 2 "Metric Calibration Matrix" (lines 179–181), Section 5 "Models" (line 362), Section 12 "Normalizer" (line 402).
* **Discrepancy Description & Rationale**: The documents state contradictory scoring rules for Hash Ribbon:
  - Line 179 defines Bottom Boundary as "Recovery cross ($S_i = 15$)" and Top Boundary as "Normal state ($S_i = 50$)".
  - Line 181 notes that normal state is 50, and capitulation is 15.
  - Line 362 lists enum states: `NORMAL`, `CAPITULATION`, `BUY_RECOVERY`.
  - Line 402 states: "Normal = 50, Capitulation = 15, Buy Recovery = 85".
  If `Buy Recovery` maps to 85 as stated in line 402, it adds $85 \times 10\% = 8.5$ points to the Composite Cycle Score, erroneously pulling the score toward an overheated cycle peak (Tier 1 Top $\ge 80$), even though Hash Ribbon Buy Recovery signals a cyclical macro bottom. The relationship between states, sub-scores, and boundary mappings is internally conflicting.

### 5. Underspecified Multi-Tier Alert Hysteresis Mechanics
* **Severity**: Major
* **Affected Scope**: Section 4 "Alerting Engine, Hysteresis & Tiered Runbooks" (lines 204–213), Section 14 "Dispatcher" (lines 416–418).
* **Discrepancy Description & Rationale**: Section 4 details the 5-point deadband for entering and exiting the top zone: crossing $\ge 80$ sets `IN_TOP_ZONE`, which resets to `NEUTRAL` only when the score drops strictly below 75. However, it does not specify how hysteresis behaves across the multiple tiers (Tier 1 at 80, Tier 2 at 85, Tier 3 at 90):
  - If the score fluctuates between 84.5 and 85.5 over consecutive days, does Tier 2 fire repeatedly?
  - Does each tier have its own 5-point deadband, or does the dispatcher record the highest reached tier within `IN_TOP_ZONE`?
  Without clarifying inter-tier hysteresis, the dispatcher risks firing redundant high-priority runbook alerts on daily price noise near tier boundaries.

### 6. Ambiguous Weekly RSI Aggregation Window
* **Severity**: Nit
* **Affected Scope**: Section 1 "Market Price Connector" (line 144), Section 11 "Indicators" (line 393).
* **Discrepancy Description & Rationale**: The document specifies pulling daily candles to calculate a "14-period weekly RSI" on a daily execution cadence (UTC 00:05). It is unclear whether the weekly RSI is calculated on closed 7-day calendar weeks (which only change once every 7 days), on a rolling 14-week (98-day) daily candle resample, or including the in-progress partial week.

### 7. Undefined Acronyms and Technical Shorthand
* **Severity**: Nit
* **Affected Scope**: Lines 282, 290, 522.
* **Discrepancy Description & Rationale**: The following acronyms are introduced without definition or external links:
  - `UTXO` (line 282, 291): Unspent Transaction Output is assumed knowledge in Alternative 1.
  - `IBD` (line 290): Initial Block Download is used without explanation.
  - `EGM` (line 522: "Drafted with EGM"): Undefined project acronym at the conclusion of the document.
