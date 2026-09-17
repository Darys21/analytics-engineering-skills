# Workflow: DATA DISCOVERY — Schema, Profiling, and Lineage Reconnaissance

## Purpose

Systematically explore every data source identified in the GRILL and BUSINESS-SPEC to understand what exists, at what quality, at what grain, with what freshness, and how it relates to other sources. The output is a fact base that eliminates guesswork during modeling, engineering, and analysis. Skip this workflow at your peril: assumptions about source structure, uniqueness, or freshness are the single largest source of bugs in analytics deliverables.

## When to use

- Immediately after `business-analysis.md` has produced a signed-off specification.
- When onboarding a new data source for the first time.
- When re-opening an existing project whose source data has changed (new columns, schema drift, new upstream system).
- When a bug investigation suggests the root cause may be upstream of models or dashboards.
- Before signing a data contract or committing to a freshness SLA.

## Inputs

- Signed-off BUSINESS-SPEC document listing required sources, KPIs, dimensions, and grain.
- Access credentials (read-only) to each source system, data warehouse schema, lake container, or exported file.
- Any existing data dictionary, ERD, or schema documentation from the source owner.
- A SQL client, Python environment, or profiling tool (e.g., Great Expectations, dbt-profiler, Soda) connected to the sources.

## Preconditions

- Read-only access has been granted to every source listed in the BUSINESS-SPEC Data section. Blockers from GRILL step 8 have been resolved or accepted with reduced scope.
- The BUSINESS-SPEC grain, KPIs, and dimensions are finalized; downstream work has not started.
- The profiling environment has enough resources to scan large tables (row counts in the millions or tens of millions should be sampled first, not full-scanned).

## Procedure

1. **Inventory schemas and tables.** For each source system:
   1. List every schema/database the source exposes.
   2. Within each schema, list every table, view, external table, and materialized view.
   3. For each object, record: object name, object type, owner, creation date, last modified date, and row count.
   4. Identify which objects are candidate sources for the KPIs and dimensions in the BUSINESS-SPEC. Label them `Relevant` / `Unclear` / `Irrelevant`.
2. **Extract column-level metadata.** For every `Relevant` and `Unclear` object:
   1. List every column with: name, ordinal position, data type, nullable flag, default value, collation, and character maximum length (if string).
   2. Flag any column name that matches a KPI or dimension term from the BUSINESS-SPEC as a candidate.
3. **Assess row counts and growth.**
   1. Record current row count.
   2. If a date column exists, compute row count per period (day / week / month) for the last 12 periods. Plot the distribution.
   3. Identify any periods with zero rows (gaps) or 10× the median (spikes). Flag gaps and spikes for investigation.
4. **Determine the actual grain of each candidate table.**
   1. From the BUSINESS-SPEC, write down the *expected* grain for each fact table candidate and each dimension candidate.
   2. Write a query that counts rows grouped by the proposed grain key columns. Use `HAVING COUNT(*) > 1` to find duplicates at that grain.
   3. If duplicates exist: (a) sample 10 duplicate groups to understand what differs between rows within a group, (b) record the actual grain (which additional column disambiguates rows), and (c) note the delta between expected and actual grain.
5. **Identify primary and natural keys.**
   1. For each dimension candidate, search for a single column or column-set whose uniqueness approaches 100% (allowing for a small known number of NULLs or data-quality issues).
   2. Label the unique column(s) the `Natural Key`. If no natural key exists, record that a surrogate key must be generated downstream.
   3. For each fact candidate, identify what the grain key is (even if non-unique) and whether any `Transaction ID`, `Event ID`, or `Batch ID` column exists for traceability.
6. **Detect duplicates.**
   1. For every candidate table, compute the exact percentage of rows that are duplicates at the proposed grain key.
   2. If duplicates > 0.1%, sample duplicates and categorize the cause: (a) true system duplicates (same event recorded twice), (b) re-processing artefacts (same ID, updated timestamps), (c) grain mismatch (our proposed grain is wrong), (d) test data not purged.
   3. Record the duplicate rate and category for each table.
7. **Profile nulls.**
   1. For every column in every candidate table, compute the NULL percentage.
   2. For columns with NULL% > 0%, investigate 10 rows with NULLs and classify: (a) legitimate NULL (missing by business design, e.g., a return date for a non-returned item), (b) data quality failure (source system should have populated), (c) truncation / encoding error.
   3. Produce a NULL-per-column report. Flag any column required by a BUSINESS-SPEC KPI or dimension whose NULL rate exceeds a threshold (default 5%) as a data-quality risk.
8. **Check for missing time periods.**
   1. Identify the primary date/timestamp column on each time-series table.
   2. Generate a complete date spine (day-level or finer) for the BUSINESS-SPEC history length.
   3. LEFT JOIN the source's period counts to the spine. Report every period where the source had zero rows.
   4. Cross-check missing periods against known source downtimes, holidays, or maintenance windows; annotate.
9. **Identify numeric outliers.**
   1. For every numeric column used or referenced in a KPI formula, compute: min, P1, P5, P25, median (P50), P75, P95, P99, max, mean, standard deviation.
   2. Compute Tukey fences (Q1 − 1.5×IQR, Q3 + 1.5×IQR) and count rows outside the fences.
   3. For any column with >1% of rows outside the fences, sample the extreme rows and investigate with the SME. Classify as: data entry error, legitimate edge case, currency/unit mismatch, test data.
10. **Plot distributions.**
    1. For every numeric KPI input column, plot a histogram (20 bins) and a boxplot.
    2. For every categorical dimension column, compute: number of distinct values, top 10 values by frequency, percentage of rows in the long tail (top 10 vs rest).
    3. For every primary date column, plot rows per period.
    4. Save plots to the discovery artifact.
11. **Map relationships and cardinality.**
    1. Between every pair of candidate fact and dimension tables that the BUSINESS-SPEC implies should join, attempt the join:
       - Identify the join key columns by name and type match.
       - Sample 100 rows from the "left" table, join to the right, and check for: (a) NULL right-side rows (missing dimension members), (b) fan-out (left row count < post-join row count).
       - Classify the relationship cardinality explicitly: 1-to-1, 1-to-many, many-to-1, many-to-many.
       - Compute referential integrity: what % of fact rows have an intact dimension lookup?
    2. Produce a relationship matrix (fact × dim) with cardinality and RI% in each cell.
12. **Assess data freshness and latency.**
    1. Record the maximum timestamp present in each fact table's primary date column.
    2. Compute the gap between `NOW()` and that maximum timestamp at the appropriate granularity (e.g., hours for near-real-time, days for daily).
    3. Compare the observed lag to the BUSINESS-SPEC as-of-time requirement (e.g., "as of 06:00 daily").
    4. If scheduled ingestion jobs exist, pull their last 30 run logs: compute success rate, average run duration, P95 run duration, and mode of failure.
13. **Trace data lineage (where possible).**
    1. Follow the data upstream: what source system / API / file feed populates the table we are looking at? Who owns that feed?
    2. Follow the data downstream (if it already has consumers): what models, reports, or dashboards depend on this table? What would break if this table's schema or grain changed?
    3. Draw a 3-level lineage diagram (upstream feed → current table → downstream consumers).
14. **Collect and validate business definitions.**
    1. For every candidate column that maps to a KPI term or dimension term, ask the SME: "What does this column actually represent in the business? When is it populated? When is it NOT populated? Can you give me three concrete examples?"
    2. Compare the SME's answer to the BUSINESS-SPEC KPI technical definition. Highlight any discrepancies.
    3. Record the canonical business definition of each candidate column in a data dictionary extract.
15. **Synthesize the data discovery report.** Compile all findings: schema inventory, column metadata, row count trends, grain determinations, key analyses, duplicates, nulls, missing periods, outliers, distributions, relationships, freshness, lineage, and business definitions. Include a `Risks` section ranking each discovered issue by severity (Blocker / High / Medium / Low) and impact on the BUSINESS-SPEC deliverables. Propose mitigations for every Blocker and High risk.
16. **Review and sign off.** Present the report to the data engineering team (for source ownership) and the SME (for business definition accuracy). Resolve disputed findings, confirm mitigations for Blocker/High risks, and obtain written sign-off that the fact base is accepted as ground truth for downstream work.

## Decision points

- **Step 4 (Grain mismatch).** If the actual table grain is finer than the BUSINESS-SPEC grain and can be aggregated up safely (additive measures), proceed and note the aggregation rule. If the actual grain is coarser, or fan-out is unavoidable, loop back to `business-analysis.md` step 8 to re-negotiate grain or KPI formulas.
- **Step 6 (Duplicates).** If duplicate rate at proposed grain is > 1%, present two options to stakeholders: (a) accept dedup logic in the silver layer (document the rule) or (b) raise the issue with the source system owner and delay the project. Do not silently drop duplicates without a documented rule.
- **Step 11 (Referential integrity).** If RI% < 95% for a required dimension join, three options: (a) accept "Unknown" dimension members and surface them explicitly in the dashboard, (b) fix upstream dimension onboarding, or (c) redesign the model to avoid the join. Record the choice and its business impact.
- **Step 12 (Freshness miss).** If observed latency exceeds BUSINESS-SPEC requirements, negotiate either (a) a more frequent ingestion schedule with data engineering or (b) an updated as-of-time SLA with the stakeholder. Do not ship a dashboard that is stale-by-design without explicit sign-off.
- **Step 15 (Blocker risks).** If any Blocker-risk issue has no agreed mitigation, pause downstream work and escalate per the project's risk register. Do not charge forward into known landmines.

## Validation

- Every source listed in the BUSINESS-SPEC Data section has been profiled; none are skipped.
- For every fact candidate, grain is stated and validated with a `HAVING COUNT(*) > 1` query (duplicate count reported).
- For every join implied by the KPI formulas, cardinality and RI% are computed and recorded.
- NULL% is computed for every column in every candidate table; columns feeding KPIs with NULL% > 5% are flagged.
- Missing periods are listed for every time-series table against a generated date spine.
- Tukey-fence outlier counts exist for every numeric KPI-input column.
- Maximum observed timestamp and computed lag are recorded for every fact table.
- A 3-level lineage diagram exists per critical source.
- A severity-ranked risk list with mitigations exists.
- SME and data engineering written sign-off is on file.

## Expected outputs

- `DATA-DISCOVERY - <Engagement Name>.md` (8–30 pages) with all 14 analysis sections + risks.
- Per-table profiling exports: `profiles/<table_name>.csv` containing row count, column types, NULL%, numeric stats, categorical value distribution.
- Plots exported to `discovery-plots/` directory (histograms, boxplots, period-count line charts, bar charts of top categorical values).
- Relationship matrix as a spreadsheet or markdown table.
- Data dictionary extract: `data-dictionary-extract.csv` with column → canonical business definition mapping.
- 3-level lineage diagrams (Mermaid or draw.io) per source.
- Work tracking system updated with sign-off status and link to report.

## Common failure modes

1. **Full scan on billion-row tables causes outages.** Remedy: in steps 3–10, always sample first (e.g., `TABLESAMPLE SYSTEM (1)` or a date-filtered recent 7-day slice) before committing to a full scan. Coordinate profiling windows with source DBAs for production systems.
2. **Grain validation uses only the key columns and misses silent fan-out from 1:N joins applied later.** Remedy: grain-check *after* joining to dimensions (step 11) as well as on the raw table.
3. **NULL profiling counts only SQL NULLs but misses sentinel values (0, -1, "", "N/A", "1900-01-01").** Remedy: in step 7, explicitly include a sentinel-value scan using a curated list appropriate to the data type.
4. **Outlier detection is confused with "interesting but legitimate data points."** Remedy: in step 9, never label a row an outlier without SME confirmation. Split output into "statistical outliers" and "SME-classified anomalies."
5. **Cardinality is inferred from column names only, not validated with a join.** Remedy: step 11 mandates a 100-row sample join. Name-type matches are frequently wrong (e.g., a `site_id` column in the fact may reference `dim_location`, not `dim_site`).
6. **Lineage stops at the warehouse table; no one traces to the actual operational source.** Remedy: step 13 requires naming the source system/API/file feed *and* its owner. Warehouse tables are rarely the origin.
7. **Business definitions are not validated with a SME.** Data dictionary text is copied from a stale Confluence page that no longer matches reality. Remedy: step 14 requires verbatim SME quotes (attributed) alongside the canonical definition.
8. **Low-severity risks drown out the blockers.** Remedy: sort the Risks table strictly by severity, then impact. Flag Blocker and High issues in the executive summary so they are not missed.

## References to load

- `references/profiling-query-library.sql` — parameterized SQL snippets for grain-check, duplicate-count, null-rate, outlier, distribution, missing-period, and referential-integrity checks (ANSI SQL + dialect variants: T-SQL, PostgreSQL, Spark SQL, BigQuery).
- `references/sampling-strategies.md` — when to use TABLESAMPLE, date-range slicing, stratified sampling, or full scan; sample-size math for desired confidence intervals.
- `references/sentinel-values-by-datatype.csv` — common sentinel NULL-mimicking values per data type (int, float, string, date, timestamp, boolean) with detection regexes.
- `references/tukey-fences-and-zscore-template.py` — reusable Python function for outlier detection with both Tukey and modified-Z-score methods, annotated output.
- `references/cardinality-and-ri-checklist.md` — step-by-step check procedure for validating a fact-to-dim join, including a pass/fail result on RI% thresholds.
- `references/freshness-sla-comparison-template.md` — template for documenting observed vs required freshness, including escalation contact and SLA breach procedure.
- `references/lineage-diagram-stencils.md` — Mermaid and draw.io stencils for 3-level lineage, plus iconography for sources, transformations, consumers.
- `references/data-discovery-review-checklist.md` — 25-item pass/fail checklist covering all 14 analysis sections.
- `references/risk-severity-matrix.md` — 4×4 likelihood × impact matrix with explicit threshold anchors for Blocker/High/Medium/Low.

## Completion criteria

- `DATA-DISCOVERY - <Engagement Name>.md` exists with all 14 sections populated and the Risks + Executive Summary sections on the first page.
- Every table listed in the BUSINESS-SPEC Data section has a corresponding profile CSV in `profiles/`.
- Every numeric KPI-input column has an outlier report; every categorical dimension column has a top-N frequency report.
- Missing periods are enumerated against a generated spine; every gap >1 period is annotated with a root cause or open investigation link.
- Join cardinality and RI% are recorded for every fact→dimension pair required by KPI formulas.
- Fact-table freshness lag is computed and compared to the BUSINESS-SPEC as-of-time; any delta is labeled a risk with a mitigation.
- 3-level lineage diagrams exist for every critical source.
- Data dictionary extract contains verified, SME-attributed business definitions for every candidate KPI and dimension column.
- Risks are severity-ranked; every Blocker and High risk has an assigned owner and a proposed mitigation.
- SME and data engineering written sign-off is on file; the work item is transitioned to the next phase (Data Quality or Data Modeling as appropriate).
