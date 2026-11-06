# Bitcoin Macro Cycle Sentinel (BitSignal)

* **Author:** Project Lead
* **Date:** 2026-11-05

## Overview

Bitcoin Macro Cycle Sentinel (BitSignal) is an autonomous, quantitative monitoring system designed to track Bitcoin macro cycle turns. By ingesting daily market OHLCV data, on-chain valuation ratios, and mining metrics, it computes a normalized Composite Cycle Score (0 to 100). The system issues automated push alerts via Telegram and local webhooks to guide staged cold-storage divestment during parabolic tops (Score >= 80) and staged dollar-cost averaging (DCA) during capitulation bottoms (Score <= 20).

## Analysis

A multi-lens Goldfish review across system architecture, UX, data engineering, macro strategy, and operational pragmatism yielded the following synthesized findings:

1. **Defensive Ingestion and Circuit Breaker Mechanics (`egm-structural`, `egm-codebase-details`)**:
   - Zero-cost public APIs (Binance, Yahoo Finance, Dune, Mempool.space) carry constant risk of rate limits (HTTP 429), schema drift, or silent null responses.
   - A two-tier fallback is required: allow last-known values within a 48-hour window marked with `data_quality: STALE`. If stale metrics account for >20% of the aggregate indicator weight, trip a deterministic circuit breaker: freeze phase-transition alerts and dispatch an immediate operational diagnostic alert to Telegram to prevent misallocated trades on degraded data.

2. **Mathematical Continuity and Normalization (`egm-codebase-details`, `egm-comprehension`)**:
   - Discrete threshold jumps produce erratic score spikes. A clamped piecewise linear function is mandated for all continuous indicators:
     $$S_i = \text{clamp}\left(\frac{x_i - \text{Min}_i}{\text{Max}_i - \text{Min}_i} \times 100, 0, 100\right)$$
   - Inverse indicators (where lower values indicate overheated tops) invert via $100 - \text{clamp}(\dots)$.
   - Asymmetric indicators (Hash Ribbon): In normal non-capitulation phases, assign a neutral baseline score of 50 ($50 \times 10\% = 5.0$ points), dropping to 15 during miner capitulation and jumping to 85 during post-capitulation buy recovery.

3. **Macro Regime Shifts and Calibration (`egm-zoom-out`)**:
   - Bitcoin cycle peaks demonstrate diminishing marginal multiples due to market capitalization scaling and institutional ETF liquidity absorption.
   - Hardcoded threshold bounds (e.g., historical MVRV Z-Score >= 5.0) risk failing to trigger in cycles with compressed volatility.
   - Calibration bounds must be strictly separated from application logic, placed into a versioned configuration file (`config.yaml`), enabling walk-forward threshold tuning.

4. **Alert Ergonomics, Cold Storage Friction, and Hysteresis (`egm-design`)**:
   - Cold storage transactions involve multisig or hardware wallet access, mempool fee surges, and transfer latency. Alerts must not merely broadcast a raw number.
   - Alerts must provide a tiered operational checklist (Tier 1: 80–84 for 20% tranche; Tier 2: 85–89 for 30%; Tier 3: >= 90 for 50%), including metric contribution breakdowns.
   - To prevent alert fatigue when scores oscillate around boundaries (e.g., 79.8 to 80.4), an alert hysteresis deadband of 5 points must be enforced before re-triggering phase-change alerts.

5. **Mandatory Historical Backtest Quality Gate (`egm-implementation-readiness`)**:
   - Direct deployment without historical validation poses financial and execution risk.
   - A Phase 1.5 Backtesting Engine is established as a prerequisite quality gate. It executes daily historical replays across 2012–2026 to verify signal timeliness, lead times before historical cycle tops/bottoms, and false-positive rates prior to live Telegram daemon activation.

## Goals vs. Non-Goals

* **In-Scope Goals:**
  - Autonomous daily pipeline executing at UTC 00:05 via lightweight Python CLI and SQLite (WAL mode).
  - Deterministic calculation of 6 core macro metrics: MVRV Z-Score (25%), 200-Week SMA Heatmap (20%), Puell Multiple (20%), Pi Cycle Top (15%), 14-Period Weekly RSI (10%), and Hash Ribbon (10%).
  - Clamped piecewise linear normalization engine outputting a composite score between 0 and 100.
  - Two-tier fallback and automated circuit breaker (freezing alerts when missing weight > 20% or staleness > 48h).
  - Alert hysteresis deadband (5 points) with tiered operational cold-storage runbooks dispatched to Telegram.
  - Mandatory Phase 1.5 Historical Backtest Engine validating signals against 2012–2026 cycle peaks and troughs.
  - Interactive local dashboard (Streamlit) featuring cycle gauge, metric waterfall, and historical cycle overlay.

* **Out-of-Scope Non-Goals:**
  - Automated order placement or private key custody integration (custody remains strictly cold and manual).
  - Intraday high-frequency trading, derivative hedging, or short-term swing signals.
  - Multi-asset or altcoin tracking (Bitcoin-exclusive).
  - Multi-tenant cloud SaaS infrastructure.

## Alternatives Weighed

* **Full Local Node Calculation (Bitcoin Core RPC + Electrs) vs. External Free APIs**:
  - *Weighed:* Local node parsing guarantees sovereign data integrity without external dependency.
  - *Decision:* Deferred to Phase 4. Processing raw blocks locally for Realized Cap requires custom indexer state and >700 GB storage. Free public APIs with strict Pydantic schema validation and circuit breakers provide immediate feasibility at zero cost.
* **Piecewise Linear Normalization vs. Logistic Sigmoidal Mapping**:
  - *Weighed:* Sigmoids provide smooth curves but introduce non-linear distortion and obscure score interpretability.
  - *Decision:* Clamped piecewise linear normalization chosen for deterministic transparency, direct debugging, and linear weight attribution.
* **Complex Multi-Service Microservices vs. Modular Python CLI with SQLite**:
  - *Weighed:* Splitting ingestion, calculation, and alerting into separate Dockerized microservices.
  - *Decision:* Rejected. Adds disproportionate orchestration complexity for a 24-hour batch job. A modular Python package with SQLite and a simple scheduler is adopted.

## Key Decisions & Staging for Next Steps

* **Configuration Decoupling**: All indicator parameters, normalization bounds, and tier thresholds are maintained in `config.yaml`.
* **Database Schema**: SQLite with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) storing raw snapshots, normalized sub-scores, and alert dispatch logs.
* **Implementation Phasing**:
  - Phase 1: Ingestion connectors, Pydantic schemas, and math calculation CLI.
  - Phase 1.5: Historical backtesting replay (2012–2026) to calibrate thresholds.
  - Phase 2: Staleness circuit breaker and Telegram bot dispatcher with hysteresis.
  - Phase 3: Streamlit local dashboard.
  - Phase 4 (Optional): Bitcoin Core RPC sovereign integration.
