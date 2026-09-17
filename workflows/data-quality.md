# Workflow: DATA QUALITY — Dimensions, Validation, Reconciliation

## Purpose

Establish measurable data quality across six canonical dimensions (completeness, uniqueness, validity, consistency, accuracy, timeliness) plus referential integrity, schema stability, distribution fidelity, and anomaly detection. Apply three levels of equality checks (technical vs semantic vs business) when comparing sources. The output is a quality baseline, a continuous-validation suite, and a reconciliation framework that catches regressions before they reach dashboards or models. Data quality is not a one-time audit; it is a living process embedded in every pipeline run.

## When to use

- Immediately after `data-discovery.md` produces a fact base, before modeling begins, to lock in a quality baseline.
- As part of the dbt/SQLMesh/ETL test suite on every pipeline run (continuous validation).
- When onboarding a new upstream source, changing an ingestion connector, or cutting over to a new system (parallel-run reconciliation).
- In response to a stakeholder complaint that "the numbers look wrong" (reactive quality triage).
- When signing a data contract between a producer team and a consumer team.
- Before publishing a semantic layer, dashboard, or reporting endpoint to production users.

## Inputs

- DATA-DISCOVERY report with per-table profiling outputs, grain statements, join maps, and risk lists.
- BUSINESS-SPEC document with KPI technical definitions, grain, constraints, and as-of-time requirements.
- Read access to source systems, staging tables, and (where applicable) a golden-source or reconciled control total.
- A data contract template (if producing one) and the consumer/producer stakeholder lists.
- A test execution framework: dbt tests, Great Expectations, Soda, SQLMesh audits, or a hand-rolled SQL/Python assertion runner.

## Preconditions

- Source tables are profiled; candidate keys, KPI columns, and dimensions are identified.
- At least one stable baseline period is available (e.g., a recently closed month where finance/operations have signed off the numbers).
- The data engineering team has agreed a path to remediate at least critical issues.

## Procedure

1. **Define the scope and criticality.**
   1. List every table, every column, and every relationship pair in scope.
   2. Label each with criticality: `Critical` (feeds a Primary KPI directly, missing it would trigger a wrong decision), `Important` (feeds a secondary KPI or diagnosis), `Informational` (nice-to-have, no decision depends on it).
   3. For Critical items, attach a Decision Impact statement: "If this column is wrong, the [Decision Name] in BUSINESS-SPEC will be wrong in this specific way."
2. **Define dimension 1: Completeness.**
   1. For every column, define what counts as missing: SQL NULL + any type-appropriate sentinel values (0, -1, "", "N/A", "1900-01-01", etc.).
   2. Set per-column completeness thresholds: Critical columns typically ≥99.9% non-missing, Important ≥99%, Informational ≥95%. If the BUSINESS-SPEC attaches a contractual SLA, use that.
   3. Write assertions that run per batch and flag any column whose completeness falls below threshold. For time-series, additionally assert no period is completely missing (0 rows) at the grain required by the KPI.
3. **Define dimension 2: Uniqueness.**
   1. For every natural key, surrogate key candidate, and grain-level key set, write uniqueness assertions: `COUNT(*) = COUNT(DISTINCT key)` at the defined grain.
   2. For non-unique grain keys, record the expected duplicate rate (from data-discovery step 6) and write an assertion that the actual rate is within ±0.1 percentage points of expected.
   3. Capture any duplicate rows that violate the assertion into a quarantined table with ingestion timestamp, violating key values, and raw payload for later investigation.
4. **Define dimension 3: Validity.**
   1. For every column, enumerate valid values:
      - Enumerated (e.g., `status IN ('Open','Closed','Cancelled')`),
      - Range-based (e.g., `temperature BETWEEN -50 AND 200`, `amount > 0`, `timestamp BETWEEN '2000-01-01' AND NOW()`),
      - Pattern-based (e.g., `email ~* '^.+@.+\..+$'`, `phone_number ~ '^\+?[0-9\-\s]{7,20}$'`),
      - Reference-table-based (e.g., `country_code IN (SELECT code FROM ref_country)`).
   2. Set validity thresholds per criticality. For Critical enums, 100% validity is required or the batch quarantines.
   3. Write assertions per column. Capture invalid rows to quarantine with the specific rule violated.
5. **Define dimension 4: Consistency.**
   1. Identify logical invariants between columns within the same row. Examples:
      - `ship_date >= order_date`
      - `total_amount = line_amount_1 + line_amount_2 + ... + tax + shipping`
      - `status = 'Closed' IMPLIES close_date IS NOT NULL`
      - `profit = revenue - cost` (within floating tolerance)
   2. Set consistency thresholds per invariant. Critical invariants require 100% compliance or batch quarantine.
   3. Write row-level assertions per invariant; capture violating rows.
   4. Extend consistency across tables: if a derived metric exists in two places (e.g., daily sales aggregation vs source invoices), assert they match within tolerance at the grain of comparison.
6. **Define dimension 5: Accuracy.**
   1. Identify a trusted golden source or control total for every Critical KPI-input column. A golden source may be: a closed-period finance GL reconciliation, an operator-verified shift log, a physical meter reading, a signed invoice PDF, a parallel run of the legacy reporting system.
   2. Define the three equality levels between candidate data and golden source:
      - **Technical equality:** Do raw values match at the row level exactly (type, precision, formatting, timezone)?
      - **Semantic equality:** Do values match after normalization (case-folding, trimming, timezone normalization to UTC, currency conversion to reporting currency, unit conversion to base unit, rounding to agreed precision)?
      - **Business equality:** Do summarized KPI totals match at decision-relevant grain and period, after applying documented business rules (e.g., excluding test transactions, including manual adjustments, applying accrual logic)? Business equality is the only level that matters for decision integrity; technical and semantic equality are diagnostic tools when business equality fails.
   3. For each golden-source comparison, state which level of equality is required and what tolerance (if any) applies. Financial totals typically require business equality with 0 tolerance. Sensor or telemetry data may allow ±0.5% or ±2σ tolerance.
   4. Produce a reconciliation report for each baseline period. Flag any mismatch, diagnose the layer (technical vs semantic vs business), and open a defect or remediation ticket.
7. **Define dimension 6: Timeliness.**
   1. For every source feed, assert: `MAX(timestamp) >= NOW() - agreed_lag` where `agreed_lag` comes from the BUSINESS-SPEC as-of-time requirement (e.g., 6 hours for daily reporting at 06:00).
   2. For every scheduled pipeline, assert last successful run completed before the agreed cutoff time. Record duration P50/P95 to detect slowness that risks future SLA breaches.
   3. Assert no data is received with timestamps far in the future (>24h unless batch-window justified) and no stale backfill data is injected into completed closed periods without an explicit backfill flag.
8. **Define referential integrity (RI).**
   1. For every fact→dimension join required by the model, write an assertion: fact rows must find a matching dimension member.
   2. Classify missing dimension members into: (a) late-arriving dimension (legitimate new value that will land within the SLA window), (b) true data-quality miss.
   3. Set an RI threshold; for Critical joins, missing members must be <0.1% and explicitly surfaced in the dashboard as "Unknown" category, never silently dropped.
   4. For bridge tables and many-to-many relations, additionally assert the bridge is balanced (sum of bridge factors = 1 for allocation bridges).
9. **Define schema validation.**
   1. Lock the expected schema per table: column name, ordinal, data type, nullability, length/precision.
   2. Run a schema-diff assertion on every ingestion. Fail the batch on:
      - Removal or rename of a column present in the Critical/Important set,
      - Type narrowing (e.g., `INT` → `SMALLINT`) that would truncate values,
      - Changing a previously non-nullable column to nullable without an approved data contract amendment.
   3. Warn (do not fail) on: column additions at the end of the table, widening of string/int lengths, non-nullable → nullable of Informational columns.
10. **Define distribution change detection.**
    1. For every numeric KPI-input column and high-cardinality categorical dimension, compute baseline distribution descriptors from the signed-off baseline period:
       - Numeric: mean, std, P5/P25/P50/P75/P95, skewness, kurtosis, histogram bin counts.
       - Categorical: value counts, Shannon entropy, top-10 share ratio.
    2. On every new batch, compute the same descriptors and apply a statistical stability test:
       - Numeric: Kolmogorov-Smirnov (KS) test vs baseline, Wasserstein distance, or percentile-range checks (new batch P50 within [baseline P25, baseline P75]).
       - Categorical: chi-squared goodness-of-fit or PSI (Population Stability Index, commonly used in credit risk; PSI <0.1 = stable, 0.1–0.25 = moderate shift, >0.25 = severe shift).
    3. Set thresholds that trigger alerts (warning at moderate shift, critical paged alert at severe shift). Distribution shifts often precede broken KPIs.
11. **Define anomaly detection on time-series KPIs.**
    1. For every KPI aggregated at its reporting cadence (day/week/month), fit a baseline model using historical data: a simple seasonal naive baseline (same period last year + week-over-week trend), STL decomposition + residual thresholding, or an exponential smoothing / Prophet model.
    2. For each new period, compute the residual (actual vs baseline prediction) and flag anomalies using a 3σ band or a robust MAD-based band.
    3. Anomalies are *signals*, not automatically defects. Route each anomaly to the SME for classification: (a) true data-quality issue, (b) legitimate business event (promotion, shutdown, incident), (c) seasonal/one-off effect already known. Feed classifications back to improve the baseline model.
12. **Implement the continuous validation suite.**
    1. Codify every assertion (steps 2–11) into the chosen framework. Each assertion produces a row in an `dq_results` table with: timestamp, table, column, check_type, passed (bool), observed_value, threshold, criticality, failure_sample (optional).
    2. Tag each assertion with the KPI or decision it protects for traceability.
    3. Wire the suite into the pipeline: after ingestion / transformation, before the publish step, the suite runs; if any Critical assertion fails, publish is blocked and the on-call engineer is paged.
    4. Build a dashboard over `dq_results`: trend per check type over the last 30 runs, top failing checks, pass rate by criticality, time-to-repair per incident.
13. **Produce the reconciliation (golden-source comparison) reports.**
    1. For every baseline period, run the accuracy comparisons (step 6) at all three equality levels.
    2. Report: period, metric, golden total, candidate total, absolute delta, relative delta, equality level, pass/fail, root-cause layer if failed.
    3. Drill into mismatches at the row level using technical equality to narrow: is the issue missing rows, extra rows, or value mismatches on shared keys?
14. **Draft the data contract (if applicable).**
    1. Between producer (team owning the source) and consumer (team owning dashboards/models), write a contract that enumerates:
       - Schemas covered.
       - Per-column completeness, uniqueness, validity thresholds by criticality.
       - Timeliness SLA (e.g., data for day D available by 06:00 D+1, 99.5% of days per rolling month).
       - Schema-change advance notice (minimum 4 weeks for breaking changes, with a deprecation window).
       - Escalation contacts, incident response SLA.
       - Consequence of breach: consumer may block upstream changes until resolved.
    2. Socialize, negotiate, obtain signed approval from both team leads.
15. **Synthesize the data quality report and sign off.**
    1. Combine the criticality list, per-dimension assertions, thresholds, baseline quality scores, reconciliation results, contract (if any), and the continuous validation suite dashboard link into a single report.
    2. Present to data engineering, the SME, and the decision-maker.
    3. Close or track every non-passing assertion: assign owner, due date, whether a temporary workaround (filter, "Unknown" bucket, tolerance relaxation) is accepted pending permanent fix.
    4. Obtain sign-off that the current quality baseline is acceptable for launch, with all accepted workarounds on file.

## Decision points

- **Step 1 (Criticality disagreement).** If consumer and producer disagree on whether a column is Critical, fall back to the BUSINESS-SPEC Decision Impact statement. Any column whose incorrectness would change the signed decision is Critical by definition.
- **Step 6 (Golden source unavailable).** If no golden source exists for a Critical column, do not fabricate one. Instead: (a) document accuracy as "not independently verifiable" in the report, (b) flag the KPI as "provisional, pending golden source identification", and (c) make the decision-maker explicitly accept the risk in writing.
- **Step 6 (Tolerance setting).** If business equality fails with a very small delta (e.g., 0.01% of totals) that the SME classifies as immaterial, allow documented tolerance; if delta affects a threshold crossing (even by 1 cent), zero tolerance is required.
- **Step 8 (RI failures).** If missing dimension members are >0.1% but all are "late-arriving", accept a grace window (e.g., fact rows may remain unmatched up to 24 hours, after which they are routed to a manual correction queue).
- **Step 9 (Breaking schema change).** If a breaking schema change is detected mid-flight and no contract amendment was submitted, fail the batch, preserve previous data, and escalate per contract; do not "make it work" with ad-hoc casts without traceability.
- **Step 10 (Distribution shift).** If PSI >0.25 or KS p<0.001 for a KPI-input column, pause publishing even if all row-level assertions pass, and convene a SME review; a distribution shift can silently invalidate thresholds and targets.
- **Step 12 (Blocking policy).** Define upfront: which check criticalities block publish? Recommended: any `Critical` failure blocks, any `Important` failure opens a Sev-2 ticket but publishes if SME accepts risk, `Informational` failures alert only.

## Validation

- Every table/column/relationship in scope is labeled with a criticality.
- All six quality dimensions have explicit assertions and thresholds for every Critical item.
- A three-level accuracy reconciliation (technical, semantic, business) has been run for every Critical KPI against a named golden source for at least one baseline period.
- The continuous validation suite runs all assertions against a sample batch; results are visible in `dq_results` with every required metadata field populated.
- Referential integrity is asserted for every model join.
- Schema validation locks the schema for all Critical/Important columns.
- Distribution change detection is configured with a baseline and PSI/KS thresholds for at least the primary KPI inputs.
- Time-series anomaly detection is configured with a baseline and alerting on the primary KPI.
- Data contract (if produced) is signed by both teams.
- All non-passing assertions have an owner, a due date, and an accepted workaround (or publish is blocked).
- Decision-maker and SME sign-off on the baseline quality and accepted risks is on file.

## Expected outputs

- `DATA-QUALITY - <Engagement Name>.md` containing the criticality list, per-dimension design, thresholds, baseline scores, reconciliation results, contract summary, and incident-remediation plan.
- `dq_results` table schema + a populated sample run exported as CSV.
- `assertions/` directory containing the codified checks: `.sql`, `.yml`, `.py`, or `.ge.yml` files as appropriate to the framework.
- Reconciliation report(s): `reconciliation/<period>_<kpi_name>.csv` at all three equality levels.
- Data contract PDF or signed markdown (if applicable): `data-contract-<producer>-v<X.Y>.md`.
- Data quality dashboard link/screenshot showing pass rates and trends.
- Work tracking system updated with sign-off status and open remediation tickets.

## Common failure modes

1. **Confusing data quality with data cleanliness.** Removing every "odd" value to get 100% validity is called data fabrication, not quality. Remedy: validity rules come from SME-approved value ranges/enums, never from an analyst's intuition. Row quarantines exist so bad data is preserved for investigation, not silently discarded.
2. **Only technical equality is checked.** Technical mismatches (e.g., timezone differences, currency sign conventions) can be 0 at technical level but 100% at business level. Remedy: step 6 explicitly runs all three layers. Business equality is the gate; the other two are diagnostics.
3. **Completeness checks miss sentinels.** Remedy: step 2 defines missing as NULL OR sentinel, using the sentinel list from references.
4. **Assertion suite is defined but never integrated into the pipeline.** Checks run "sometime" after publishing, so regressions hit users first. Remedy: step 12 explicitly wires the suite between transform and publish steps with a blocking policy.
5. **Thresholds are pulled out of thin air.** 95% sounds good but is arbitrary. Remedy: derive thresholds from (a) BUSINESS-SPEC decision impact, (b) current observed quality baseline + 10–20% improvement, (c) contractual SLA if present.
6. **Golden source is the same system as the candidate.** "We compared sales to the source table" is circular. Remedy: golden source must be an independent channel (signed paper, physical count, finance GL tie-out, legacy report signed off). If no independent channel exists, step 6's decision point applies.
7. **Distribution shifts are ignored because row-level checks pass.** A KPI that "passes" all row-level tests can still be meaningless if its underlying distribution has shifted so much that thresholds and targets are obsolete. Remedy: step 10 triggers SME review on severe shift independent of row checks.
8. **Anomaly detection cries wolf too often, so alerts are muted.** Remedy: step 11 requires SME classification loop; use robust baselines (seasonal naive, STL) and wider bands initially, tighten as trust builds.

## References to load

- `references/data-quality-dimensions-definitions.md` — canonical definitions of the 6 dimensions with 30+ industry examples each, including decision impact templates.
- `references/three-level-equality-reconciliation-template.xlsx` — spreadsheet template with three tabs (Technical, Semantic, Business), pre-written formulas for delta%, and a summary dashboard.
- `references/assertion-sql-library.sql` — ANSI SQL snippets for each check type (completeness, uniqueness, validity range/enum/pattern/ref, row invariants, RI, schema diff, period missing).
- `references/psi-ks-distribution-tests.py` — Python module for PSI (categorical) and KS/Wasserstein (numeric) stability tests with default thresholds and annotated output.
- `references/seasonal-anomaly-detection.py` — Python module implementing STL + MAD and seasonal-naive baselines with a pluggable alert interface.
- `references/data-contract-template.md` — fillable markdown data contract with schema, SLA, thresholds, change-notice, escalation, breach-consequence sections.
- `references/dq-results-schema.sql` — DDL for the `dq_results` table with all required metadata columns and indexes.
- `references/tolerance-setting-for-financial-reconciliation.md` — decision-tree for zero-tolerance vs immaterial-tolerance based on decision threshold crossings and GAAP materiality.
- `references/data-quality-review-checklist.md` — 30-item pass/fail checklist covering every step.
- `references/referential-integrity-and-late-arriving-dims.md` — patterns for grace windows, inferred members, manual correction queues, and "Unknown" bucketing with worked SQL examples.

## Completion criteria

- `DATA-QUALITY - <Engagement Name>.md` exists and contains the criticality list, all 6 dimension designs, RI/schema/distribution/anomaly sections, baseline reconciliation, and data contract summary (if applicable).
- Every Critical column has at least one assertion in each applicable quality dimension.
- The continuous validation suite has been executed on at least one batch and results are persisted in `dq_results` with all metadata.
- A signed-off baseline period has been reconciled against a named golden source at all three equality levels; deltas (if any) are documented with owners and due dates.
- Schema validation is in place and a breaking-schema-change runbook exists.
- Distribution-change and time-series-anomaly alerting are wired for at least the primary KPI inputs.
- Data contract (if produced) is signed by the producer and consumer team leads.
- All open remediation items are tracked in the ticketing system with owners and due dates.
- Decision-maker, SME, and data engineering written sign-off is on file accepting the quality baseline, any temporary workarounds, and the blocking policy.
- The work item transitions to the next phase: Data Modeling or Analytics Engineering.
