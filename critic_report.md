# Critic Review Report: Bitcoin National Execution Strategy

**Target:** `docs/designs/bitcoin_national_execution_strategy.md` (`lines 1..302`)  
**Mode:** REVIEW  
**Standards:** `feature-spec-standard`  

## Reviewer Status

| Reviewer | Lens | Status |
| :--- | :--- | :--- |
| `egm-design` | System Architecture, Scalability, Edge Cases, Tax Compliance | completed |
| `egm-structural` | Specification Structure, Completeness, Internal Consistency | completed |
| `egm-style` | Precision, Conciseness, Ambiguity Elimination | completed |

---

## Severity Breakdown
* 🔴 **Blocker**: 3
* 🟡 **Major**: 4
* 🟢 **Nit**: 3
* **Total Findings**: 10

---

## Prioritized Findings (Blockers -> Major -> Nits)

### 1. Undefined Variables and Flawed Tax Logic in `evaluate_tax_strategy` - Severity: 🔴 Blocker
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 148-161` (`bitsignal.strategy.tax_br`)
* **Discrepancy Description:**
  1. The reference Python implementation on line 158 uses `quantity_sold` and `current_cmp` (`capital_gain = alienation_brl - (quantity_sold * current_cmp)`), but neither variable is passed in the signature `def evaluate_tax_strategy(alienation_brl: float, signal_date: datetime)`. This produces a runtime `NameError`.
  2. The function checks `alienation_brl <= 35000.0` in isolation without accounting for `month_accumulated_sales_brl`. Under Brazilian tax law (art. 35 da Lei 8.981/1995), the R$ 35k exemption applies to the *sum of all alienations in the calendar month*. If a user previously sold R$ 10.000, an alienation of R$ 30.000 is not exempt.
  3. In the split branch, `part1 = 34500.0` and `part2 = alienation_brl - part1`. For any sale where `alienation_brl > 69500.0` (up to the allowed R$ 70k limit), `part2` exceeds R$ 35.000,00, thereby breaching the exemption ceiling in month 2 and incurring tax unexpectedly.
* **Rationale & Recommendation:**
  Refactor the signature and decision algorithm to accept `current_month_accumulated_brl`, `quantity_to_sell_btc`, and `current_cmp_brl`. Calculate split boundaries dynamically so neither `part1` nor `part2` ever exceeds `R$ 35.000,00 - safety_buffer`:
  ```python
  def evaluate_tax_strategy(
      alienation_brl: float,
      quantity_btc: float,
      current_cmp_brl: float,
      month_accumulated_brl: float,
      signal_date: datetime
  ) -> TaxExecutionPlan:
  ```

---

### 2. Sunday Night Central Bank PTAX Non-Availability & Illiquid Market Orders - Severity: 🔴 Blocker
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 55, 74, 178-180, 230-232`
* **Discrepancy Description:**
  The design specifies running evaluation on Sunday at 21h01 BRT and computing exact BRL conversions and DARF using the BACEN PTAX closing rate. However, the Central Bank of Brazil (BACEN) does not publish or update PTAX on weekends. At 21h01 BRT on Sunday, calling the BACEN API for the current date returns HTTP 404 / no quote.
  Furthermore, the runbook instructs executing a "venda a mercado no par BTC/BRL" on Brazilian exchanges for tranches exceeding R$ 100k (e.g., CUJ 3). Order books on Brazilian exchanges have thin liquidity on Sunday nights; unconstrained market orders will trigger significant slippage.
* **Rationale & Recommendation:**
  1. Specify the fallback and legal benchmark: On non-business days (Sunday 21h BRT), the system must explicitly query the *last available business day's closing PTAX* (D-2 / Friday PTAX bulletin 5), which is the legally accepted rate by RFB.
  2. In the runbook and execution logic, prohibit pure market orders (`MARKET`). Mandate limit orders with a slippage collar (e.g. `LIMIT` pegged at 0.5% below the current index bid) to avoid order book slippage.

---

### 3. Sunday 21h01 BRT PIX Night Limit Deadlock - Severity: 🔴 Blocker
* **Reviewer Lens:** `egm-design` / `egm-style`
* **Affected Scope:** `Lines 26-27, 88-89, 233-234`
* **Discrepancy Description:**
  In Section "The Problem" (item 3), the spec correctly identifies that BACEN mandates a nocturnal PIX security limit (typically R$ 1.000 to R$ 5.000 between 20h00 and 06h00). However, in CUJ 3 (line 89) and the Runbook template (line 233), the system instructs the user: *"No mesmo instante da execução, solicite PIX de R$ 111.000,00 para sua conta bancária"*.
  Attempting a R$ 111.000 PIX at 21h01 BRT on a Sunday will be blocked by Brazilian banking fraud and night-limit controls, trapping funds in limbo or creating extreme user panic.
* **Rationale & Recommendation:**
  The runbook and strategy engine must incorporate a nocturnal transfer protocol:
  * For withdrawals > bank night limit (defaulting to R$ 5.000): Instruct the user to leave the fiat balance in the exchange account overnight and schedule the PIX withdrawal for Monday at 06:01 BRT.
  * Add a pre-requisite check in the setup onboarding asking the user whether they have adjusted their nocturnal PIX limit with their banking institution.

---

### 4. Direct Contradiction in CUJ 2 (Split Intermensal Title vs Single Exempt Sale) - Severity: 🟡 Major
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 71-80` (`CUJ 2`)
* **Discrepancy Description:**
  The heading of CUJ 2 is explicitly: *"CUJ 2: Saída em Topo Parabólico com Split Intermensal (Gatilho V1)"*.
  However, in the body (lines 74-78), the alienation value is R$ 29.812,00. The system notes that $29.812 \le 35.000$, concludes that it is 100% exempt, and executes a full immediate sale in a single tranche. No split is ever performed or demonstrated.
* **Rationale & Recommendation:**
  CUJ 2 fails to validate the split intermensal algorithm. Either:
  1. Increase the tranche size in CUJ 2 (e.g. 0.08 BTC at US$ 128.500 $\approx$ R$ 59.624) so it triggers the split: Part 1 (R$ 34.500) on Oct 26 and Part 2 (R$ 25.124) on Nov 01; OR
  2. Rename CUJ 2 to *"Saída em Topo Parabólico com Isenção Integral (Gatilho V1)"* and introduce a dedicated CUJ 4 demonstrating the split intermensal workflow.

---

### 5. Mathematical Error in CUJ 1 Average Cost Recalculation - Severity: 🟡 Major
* **Reviewer Lens:** `egm-structural`
* **Affected Scope:** `Lines 63-69` (`CUJ 1`)
* **Discrepancy Description:**
  In CUJ 1:
  * Prior holdings: 0.18 BTC @ R$ 320.000/BTC = R$ 57.600,00.
  * New purchase (C2): R$ 20.000,00 for 0.065 BTC (implied rate of R$ 307.692,30/BTC).
  * New total BTC = $0.18 + 0.065 = 0.245$ BTC.
  * New total cost = $\text{R\$} 57.600 + \text{R\$} 20.000 = \text{R\$} 77.600,00$.
  * Accurate Weighted Average Cost ($CMP$): $77.600 / 0.245 = \mathbf{\text{R\$} 316.734,69/\text{BTC}}$.
  Line 68 states: *"recalcula o custo médio ponderado para R$ 312.500/BTC"*, an error of R$ 4.234,69 per BTC.
  Additionally, the PTAX quote is missing from the "When" section of CUJ 1.
* **Rationale & Recommendation:**
  Update line 68 to state the exact recalculated CMP of R$ 316.734,69/BTC and explicitly declare PTAX in line 64 (e.g. PTAX = R$ 5,4555).

---

### 6. Missing Retroactive Taxation Transition in Monthly Ledger - Severity: 🟡 Major
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 203-215` (`tax_monthly_ledger`)
* **Discrepancy Description:**
  In `tax_monthly_ledger`, each month starts with `tax_exempt = 1`. If an initial sale of R$ 20.000 occurs, it is flagged as exempt. If a subsequent sale of R$ 20.000 occurs within the same calendar month, the total reaches R$ 40.000. Under RFB rules, *all* gains in that month lose exemption status retroactively, requiring DARF calculation on the cumulative gain of both transactions.
  The design lacks specification for the state transition trigger and recalculation of previously cleared exempt gains when monthly totals cross R$ 35.000,00.
* **Rationale & Recommendation:**
  Detail the recalculation workflow in `tax_br.py`: whenever cumulative alienation crosses R$ 35.000,00, query all `portfolio_transactions` for that `YYYY-MM`, recalculate the gross capital gain for all sales in the month, and update `tax_monthly_ledger` with `tax_exempt = 0` and the revised total `darf_amount_due`.

---

### 7. Timezone Ambiguity in Scheduled Evaluator (`weekday() == 0`) - Severity: 🟡 Major
* **Reviewer Lens:** `egm-structural` / `egm-style`
* **Affected Scope:** `Lines 109, 162-164`
* **Discrepancy Description:**
  Line 163 states: *"acionado na rotina diária quando `weekday() == 0` (segunda-feira 00:05 UTC / domingo 21h05 BRT)"*.
  `weekday() == 0` is Monday. In UTC, Sunday 21h05 BRT is indeed Monday 00h05 UTC (`weekday() == 0`). However, if the Python process or system clock runs in local Brazilian time (`America/Sao_Paulo`), Sunday at 21h05 has `weekday() == 6`. Using standard `datetime.now().weekday()` would fail to trigger or trigger 24 hours late.
* **Rationale & Recommendation:**
  Explicitly mandate UTC-aware datetime objects across all schedulers:
  `datetime.now(timezone.utc).weekday() == 0` or anchor the cron schedule explicitly as `CRON_TZ=America/Sao_Paulo 05 21 * * 0`.

---

### 8. LaTeX Syntax and Formatting Corruption - Severity: 🟢 Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 138-140`
* **Discrepancy Description:**
  Lines 138-140 contain corrupted LaTeX escapes where `\t` was converted into literal tabs and `\f` into form feed characters (`$\text{EMA}_{21w}$`, `$\alpha = \frac{2}{21+1}$`, `$\text{Close}_w < \text{EMA}_{21w}$`). This breaks GitHub Markdown and KaTeX rendering.
* **Rationale & Recommendation:**
  Replace with sanitized formulas:
  `$\text{EMA}_{21w}$ com $\alpha = \frac{2}{21+1}$` and `$\text{Close}_w < \text{EMA}_{21w}$`.

---

### 9. JSON String Storage for `executed_stages` in `strategy_state` - Severity: 🟢 Nit
* **Reviewer Lens:** `egm-design`
* **Affected Scope:** `Lines 197-200`
* **Discrepancy Description:**
  Storing `executed_stages TEXT NOT NULL DEFAULT '[]'` as a JSON blob inside the single-row `strategy_state` table limits SQL queries and requires JSON serialization/deserialization on every state check.
* **Rationale & Recommendation:**
  While acceptable for SQLite WAL, creating a dedicated table `strategy_executed_stages (stage TEXT PRIMARY KEY, executed_at TIMESTAMP, tx_id INTEGER REFERENCES portfolio_transactions(id))` provides relational integrity and indexed lookup.

---

### 10. Redundant Exposition Across Overview, Problem, and Alternatives - Severity: 🟢 Nit
* **Reviewer Lens:** `egm-style`
* **Affected Scope:** `Lines 15-16, 23, 256-258, 284-289`
* **Discrepancy Description:**
  The statutory references (Lei 8.981/1995, isenção de R$ 35k, alíquota de 15%, Resoluções BCB 519/520/521) are repeated almost verbatim four times across the Overview, Problem statement, and Alternatives sections.
* **Rationale & Recommendation:**
  Consolidate the regulatory foundation into a single dedicated paragraph in the Overview or Problem section and reference it concisely in the Alternatives to improve technical brevity.
