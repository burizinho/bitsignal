# Stage 7 Critic Review Report: Bitcoin Macro Cycle Sentinel

**Target:** `docs/designs/bitcoin_macro_cycle_sentinel.md` (`Lines 1..337`)

## Reviewer Status

| Reviewer | Status |
| --- | --- |
| `egm-design` | completed |
| `egm-structural` | completed |
| `egm-style` | completed |

---

## Severity Breakdown
- 🔴 **Blockers**: 4
- 🟡 **Major**: 5
- 🟢 **Nits**: 3
- **Total Findings**: 12

---

## Prioritized Findings (Blockers -> Major -> Nits)

### 1. Contradictory Divestment Tranche Schedules - Severity: Blocker
* **Reviewer Lens:** `egm-design`, `egm-style`
* **Affected Scope:** Lines 13, 31, 210–212, 268
* **Discrepancy Description**: The document presents conflicting divestment tranche schedules across different sections:
  - Line 13 states divestment guides staged selling of "30% to 40%".
  - Line 31 (Goals) defines: "Score 80–84: 20% tranche, 85–89: 30%, >=90: 50%" (summing to 100% total divestment).
  - Lines 210–212 (Alerting Engine) define: "Tier 1: Stage 20% divestment tranche", "Tier 2: Stage additional 10% tranche (30% cumulative)", "Tier 3: Stage additional 10% tranche (40% cumulative). Full cycle euphoria exit execution."
  - Line 268 (Backtest Gate) mentions "executing 30% staged cold-storage divestment".
* **Rationale & Recommendation**: Staging an exit from cold storage is a safety-critical operational procedure. If an operator follows Line 31, they liquidate 100% of holdings, whereas Lines 210–212 mandate retaining 60% of cold storage. Standardize all sections to one explicit schedule (e.g., Tier 1: 20%, Tier 2: 10% [30% cum], Tier 3: 10% [40% cum] with 60% permanent cold-stack retention) and eliminate contradictory percentages.

---

### 2. Undefined Pi Cycle Continuous Formulation & Dual-Curve Normalization Gap - Severity: Blocker
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 145–146, 158–165, 177
* **Discrepancy Description**: Pi Cycle Top evaluates $\text{SMA}_{111} \ge 2 \times \text{SMA}_{350}$, while Pi Cycle Bottom evaluates $\text{EMA}_{150} \times 0.745 \le \text{SMA}_{471}$. In the Metric Calibration Table (Line 177), it is assigned a 15% weight with boundary conditions "Bottom cross active ($S_i = 0$)" and "Top cross active ($S_i = 100$)", and description "Piecewise: Top spread vs Bottom spread". However, the piecewise linear equation in Lines 158–165 requires a single scalar metric $x_i$ with monotonic bounds $[\text{Min}_i, \text{Max}_i]$. 
* **Rationale & Recommendation**: Because Pi Cycle is composed of two disconnected indicator pairs (a 111/350 SMA pair for tops and a 150 EMA / 471 SMA pair for bottoms), a single 1D clamp cannot compute an intermediate score when neither cross is active. Define the exact continuous scalar formula $x_{\text{picycle}}$ (e.g., a ratio spread between top proximity and bottom proximity, or a default neutral score of 50 when neither boundary condition is triggered).

---

### 3. Hash Ribbon Bottom vs. Euphoria Logic Inversion & Contradictory State Values - Severity: Blocker
* **Reviewer Lens:** `egm-design`, `egm-style`
* **Affected Scope:** Lines 70, 179–181, 362, 402
* **Discrepancy Description**: 
  - Line 179 specifies: "Recovery cross ($S_i = 15$)", "Normal state ($S_i = 50$)", and "Asymmetric: Normal = 50 (neutral), Capitulation = 15".
  - Line 402 states: "Handles Hash Ribbon asymmetric assignment (Normal = 50, Capitulation = 15, Buy Recovery = 85)".
  - If a low composite score ($\le 20$) triggers the capitulation DCA accumulation runbook (CUJ 3, Line 70), assigning `Buy Recovery = 85` creates an inverted signal: a buy recovery event would drive the score *upward* toward the divestment zone ($\ge 80$) instead of confirming the bottom zone.
* **Rationale & Recommendation**: Harmonize the states and numerical mappings. Clarify whether capitulation or buy recovery is the trigger for the bottom score, and assign consistent sub-scores (e.g., Capitulation = 20, Buy Recovery = 10, Normal = 50). Ensure that bullish bottom signals pull the composite score down towards $\le 20$, while neutral conditions contribute 50.

---

### 4. Binance Ingestion Limit Deficit for 200-Week SMA - Severity: Blocker
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 142–144
* **Discrepancy Description**: Line 143 specifies fetching daily OHLCV from Binance using: `GET /api/v3/klines?symbol=BTCUSDT&interval=1d&limit=1000`. However, Line 144 explicitly notes that the 200-week SMA requires "1400 daily candles" ($200 \times 7 = 1400$).
* **Rationale & Recommendation**: Binance's single-request limit is 1000 candles. Querying with `limit=1000` will only provide ~142 weeks of daily data, making calculation of the 200-week SMA impossible. Specify paginated ingestion across multiple requests (`startTime`/`endTime`) or specify downloading weekly candles (`interval=1w&limit=200`) specifically for the 200-week SMA and 14-period weekly RSI.

---

### 5. Dynamic Weight Rescaling Induces Asymmetric Score Distortion Near Boundary Regimes - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 103, 180–181, 194
* **Discrepancy Description**: When metrics are stale but within the 20% missing weight threshold, the system scales remaining weights via $w'_k = \frac{w_k}{1 - W_{\text{missing}}}$. When Hash Ribbon is in its neutral state ($S_i = 50$), scaling its weight from 10% to 12.5% shifts its baseline contribution from 5.0 to 6.25 points. More critically, if a top indicator is missing during a market rally, rescaling over-amplifies remaining indicators, which can artificially trigger a Tier 1 or Tier 2 exit threshold.
* **Rationale & Recommendation**: Dynamic weight rescaling without boundary clamping or deadband compensation creates synthetic boundary crossings. Require that in `DEGRADED` mode, the threshold bounds are either widened or an alert flag clearly marks the signal as "DEGRADED SCORE - WEIGHT RESCALED" to prevent accidental execution of cold-storage divestment based on an inflated score.

---

### 6. Unhandled Inter-Tier Alert Hysteresis and Escalation Deadbands - Severity: Major
* **Reviewer Lens:** `egm-design`, `egm-structural`
* **Affected Scope:** Lines 204–213
* **Discrepancy Description**: The hysteresis specification in Section 4 details the boundary transition for entering and leaving the top zone ($80 - 5 = 75$). However, it fails to specify hysteresis rules between Tier 1 (80), Tier 2 (85), and Tier 3 (90).
* **Rationale & Recommendation**: If the score oscillates between 84.8 and 85.2 across several days, the system could repeatedly trigger Tier 2 alerts. Define an inter-tier deadband (e.g., score must drop 2 points below a tier boundary before that specific tier alert can re-fire).

---

### 7. Ingestion Timestamp Staleness False Positives on Daily Metrics - Severity: Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 187–190
* **Discrepancy Description**: `FRESH` is defined as data timestamp $\le 24$ hours old. The pipeline executes at UTC 00:05 daily. Free public APIs for daily aggregated metrics (e.g. MVRV Z-Score, Puell Multiple) timestamp their daily record at UTC 00:00 of the closed candle or lag by 1–2 hours during processing. At 00:05, a candle from the previous day can be measured at 24.1 hours old.
* **Rationale & Recommendation**: A strict 24-hour cutoff will cause legitimate daily metrics to oscillate between `FRESH` and `STALE` on every run. Widen the `FRESH` window for 1-day interval metrics to $\le 30$ or $\le 36$ hours to accommodate publishing latency.

---

### 8. Critical Unresolved Data Source and Webhook Schema Open Questions in Approved Spec - Severity: Major
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 4, 42–46, 150–153
* **Discrepancy Description**: The document is marked as `Status: Approved` (Line 4), yet contains unresolved Open Questions regarding the core free on-chain data endpoint for Realized Cap / MVRV Z-Score (Question 1) and the downstream webhook integration payload schema (Question 2).
* **Rationale & Recommendation**: Because MVRV Z-Score carries the highest individual weight in the engine (25%), leaving its upstream source unresolved risks architectural blockages during implementation. Resolve Question 1 by specifying the exact primary endpoint and fallback mirror, define the JSON schema for Question 2, and close out the Open Questions section.

---

### 9. Incomplete CUJ Coverage for Degraded Circuit Breaker Recovery and Tier Escalation - Severity: Major
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Lines 48–75
* **Discrepancy Description**: The Critical User Journeys cover basic Tier 1 top trigger (CUJ 1), complete circuit breaker tripping (CUJ 2), and bottom capitulation (CUJ 3). However, there is no journey demonstrating:
  1. Escalation through Tiers 1 $\to$ 2 $\to$ 3 and return through the hysteresis gate.
  2. The `DEGRADED` state behavior ($W_{\text{missing}} \le 20\%$) where weights are rescaled and an operational notice is logged.
* **Rationale & Recommendation**: Add CUJ 4 (`DEGRADED` State Handling & Automatic Weight Normalization) and CUJ 5 (`Tier Escalation & Hysteresis Recovery`) to validate all system state transitions before code construction.

---

### 10. Ambiguous Weekly RSI Cadence (Sunday Close vs. Rolling Daily Weekly) - Severity: Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** Lines 144, 178
* **Discrepancy Description**: The document specifies "14-period weekly RSI", but runs on a daily cadence at UTC 00:05. The spec does not specify whether this is calculated strictly on completed Sunday weekly closes (updating only once every 7 days) or as a rolling 98-day window calculated daily.
* **Rationale & Recommendation**: Clarify the sampling frequency in the technical plan (recommend using rolling 7-day intervals sampled daily to maintain continuous daily score sensitivity).

---

### 11. Vague Free On-Chain Endpoint Fallback References - Severity: Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** Lines 151–153
* **Discrepancy Description**: The text mentions "verified daily community Dune queries (or cached daily on-chain mirrors)" without giving concrete query IDs, repo URLs, or specific API paths.
* **Rationale & Recommendation**: Replace generic phrases with concrete references or configuration stubs (e.g., Dune Query ID parameter in `config.yaml` or specific GitHub raw mirror URL).

---

### 12. Dashboard Latency NFR Lacks Dataset Sizing Baseline - Severity: Nit
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** Line 329
* **Discrepancy Description**: Line 329 requires that Streamlit render initial graphs in under 500 ms, but does not specify the dataset size or client hardware assumptions.
* **Rationale & Recommendation**: Specify the benchmark dataset size: "render initial graphs in under 500 ms over the full 14-year daily historical dataset (~5,200 rows) on standard commodity hardware (4-core CPU, 8 GB RAM)".

---
*Generated by EGM Synthesizer Persona*
