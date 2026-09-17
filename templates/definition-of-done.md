# Definition of Done (DoD) — Analytics Engineering Deliverables

> **Template Version**: 1.2
> **Usage**: Copy this page and *tailor* the checklists for each specific deliverable (a model, a dashboard, a report, a pipeline, or a full project). A deliverable is **NOT DONE** until every *Applicable* item below is checked **AND** the *Acceptance Sign-Off* section is signed.
>
> **Applicability key**: Not every item applies to every deliverable. Mark each row `✅ Applicable`, `N/A Not Applicable`, or `⛔ Blocked`. Any `⛔ Blocked` items require a documented *Deferral Rationale* signed off by both the Business Owner *and* the Analytics Engineering Lead — they do not become "N/A" silently.
>
> **Philosophy**: "Done" does not mean "code works on my machine." It means the deliverable is **production-ready, supportable, and will keep working reliably after the author moves on to the next project.**

---

## 0. Deliverable Metadata

| Field | Value |
|---|---|
| **Deliverable Name** | [e.g., "Wagon Turnaround Operational Dashboard (Power BI) + fact_wagon_cycle Gold Model"] |
| **Deliverable Type** | `Dashboard` / `Data Model (dbt/ELT)` / `Analysis Report` / `Data Pipeline` / `ML Model` / `Full Project` |
| **Related Business Question** | [Link to BQ-YYYY-NNN] |
| **Analytics Owner** | [Name] |
| **Business Owner** | [Name] |
| **Target Completion Date** | [YYYY-MM-DD] |
| **Actual Completion Date** | [YYYY-MM-DD — filled at sign-off] |
| **Linked ADRs (if any)** | [ADR-001, ADR-012…] |
| **Linked Data Contract(s)** | [contract/gold/logistics/fact-wagon-cycle.contract.yml] |

---

## 1. ✅ Business Requirement Alignment

> Did we build *the right thing*? Not "did it build successfully," but "does it actually answer the business question in §2 of the business-question.md?"

| # | Check Item | Applicable? (✅/N/A/⛔) | Evidence / Notes |
|---|---|---|---|
| 1.1 | Every **Decision Supported** listed in `business-question.md §5` has a corresponding output in the deliverable (table, chart, dashboard page, or report recommendation). | | |
| 1.2 | Every **Success Criterion** from `business-question.md §6` can be demonstrated with the deliverable output (e.g., a screenshot, a query result). | | |
| 1.3 | All **KPIs / Metrics** from `business-question.md §7` are produced and match the master definitions in `CONTEXT.md §4` (formula, source, grain). No "silent changes" to a KPI formula without written sign-off. | | |
| 1.4 | Deliverable uses only the **Dimensions / Grain / Timeframe** agreed in `business-question.md §8` (or deviations are logged and approved via scope change). | | |
| 1.5 | Business Owner (or designated delegate) has performed a **UAT walkthrough** on the deliverable in UAT/PROD environment, using real or UAT-masked data. Issues found are either (a) fixed before go-live or (b) formally deferred to a follow-up work item. | | |
| 1.6 | **No scope creep**: Deliverable does not include features, columns, or pages that were *not* in the agreed scope. Any additions are explicitly tagged as "out-of-scope bonus" with rationale. | | |
| 1.7 | **Scope exclusions honored**: Every item in `business-question.md §11 (Scope Exclusions)` is confirmed NOT present. If any *is* present, it was re-approved via written scope change. | | |

**Acceptance Bar**: Items 1.1–1.5 must all be ✅ Applicable → checked. If 1.1 is "not applicable" for a pure infrastructure deliverable, note rationale.

---

## 2. ✅ Implementation Correctness

> Did we build the thing *right*? Is the logic correct at the row/column/calculation level?

| # | Check Item | Applicable? | Evidence / Notes |
|---|---|---|---|
| 2.1 | **Grain documented**: Every fact table / tabular model table has its grain explicitly stated in 1 sentence (e.g., "1 row = 1 completed wagon port-to-port cycle") in the model `.yml` / `dbt_project` schema file. | | |
| 2.2 | **Primary Key correctness**: Every model/table has a documented PK, and the PK is unique + not null (validated via dbt tests or equivalent). | | |
| 2.3 | **Foreign Key integrity**: All FK columns point to a valid row in the parent dimension (or are explicitly nullable with a documented reason). Zero orphan rows on required FKs. | | |
| 2.4 | **SQL / transform logic peer-reviewed**: Another qualified engineer has read every CTE, JOIN, and WHERE clause, and agrees the logic implements the stated business rule correctly. | | |
| 2.5 | **Calculation cross-checks**: Headline numbers (totals, sums, averages, KPIs) from the new deliverable are independently cross-checked against: (a) a second implementation written by a different person, OR (b) a known-good legacy report, OR (c) manually-computed spot-checks on ≥ 10% of sample rows. | | |
| 2.6 | **No row/column drift**: Row counts and aggregated totals between Dev and Prod match (for equivalent data windows) within 0.5% before PROD deploy. | | |
| 2.7 | **Date/time handling verified**: All timestamps stored as UTC; display-timezone conversion happens only in the BI layer, not during ETL. No off-by-one-day or DST-shift bugs for dates around daylight-saving boundaries. | | |
| 2.8 | **Currency / UOM verified**: All monetary amounts go through a single UOM/currency conversion path (documented); no mixing EUR vs USD or tonnes vs kg within a single KPI column. | | |
| 2.9 | **SCD type logic correct**: Slowly changing dimensions use the right SCD type (1/2/3/6) per the documented decision; historical-as-at queries return the correct attribute values for past dates. | | |
| 2.10 | **Null handling explicit**: Every nullable column has a documented policy: "unknown" surrogate key, empty string, 0.0, or genuinely NULL. Aggregations `COUNT`/`SUM`/`AVG` ignore NULLs correctly. | | |

**Acceptance Bar**: 2.1–2.6 required for any model/dashboard with calculations. 2.7–2.10 required where applicable. Deviations must have a documented "We know this is slightly off because X, and we accept it per signed-off Y."

---

## 3. ✅ Data Quality (DQ)

> If the deliverable produces or depends on a dataset, does it meet the quality bar in the data contract?

| # | Check Item | Applicable? | Evidence / Notes |
|---|---|---|---|
| 3.1 | **Data contract exists**: Any Gold / published Silver model has a corresponding `data-contract.yml` (see templates/) that fully describes schema + quality rules + SLOs. | | |
| 3.2 | **Completeness ≥ SLO**: Required columns are 100% populated. Optional columns meet their completeness threshold (e.g., ≥ 98% per contract). | | |
| 3.3 | **Uniqueness**: No duplicate rows on the PK or any other column set marked `unique:true` in the contract. Zero tolerance for PK duplicates. | | |
| 3.4 | **Validity / range**: All numeric values fall within the documented min/max. All categorical values are in the `allowedValues` list. String patterns match the regex. | | |
| 3.5 | **Temporal ordering sanity**: For event-series data, event timestamps are logically ordered (start < end; no time-travel within a transaction). | | |
| 3.6 | **Referential integrity**: 100% of required FKs resolve; no orphan rows. | | |
| 3.7 | **Freshness meets SLO**: Last partition / data-as-of date is ≤ the SLO window (e.g., ≤ 90 min late for real-time; ≤ 07:30 local for daily batch). | | |
| 3.8 | **Known data issues handled**: Every row in `CONTEXT.md §8 (Known Data Issues)` that touches this deliverable has an implemented mitigation (fallback, filter, watermark) and the mitigation is working correctly per test. | | |
| 3.9 | **Distribution sanity checks pass**: Mean/median/std/percentiles of numeric columns are within 5% of the 30-day trailing baseline. No sudden 20%+ jumps or drops without a documented business reason. | | |
| 3.10 | **DQ dashboard green**: The data quality monitoring dashboard (Great Expectations / dbt tests / custom) shows a green / pass state for this model at deploy time. | | |

**Acceptance Bar**: Items 3.1–3.7 must be green. 3.8–3.10 are required for any Gold model or critical Silver model. A single failed DQ rule with severity=error blocks PROD deploy.

---

## 4. ✅ Tests

> Do tests prove the deliverable is correct? And will tests catch regressions when someone touches the code in 6 months?

| # | Check Item | Applicable? | Evidence / Notes |
|---|---|---|---|
| 4.1 | **Unit tests exist**: Pure functions / macros / SQL transformations have unit tests with 2 or more edge cases (e.g., empty input, out-of-range input, default values). | | |
| 4.2 | **Integration tests exist**: End-to-end pipeline from staged sample input to model output runs successfully in CI; checks row count, PK uniqueness, and ≥ 3 business rules. | | |
| 4.3 | **dbt schema tests**: Every dbt model has `.yml`-declared tests: `not_null` + `unique` on PK; `relationships` for FKs; accepted values or range checks on all critical columns. | | |
| 4.4 | **Custom business-rule tests**: At least 2 business-rule tests beyond generic schema tests (e.g., "total_cycle_duration = sum of leg durations ± 5 min"; "OTIF flag TRUE only when both date and qty conditions met"). | | |
| 4.5 | **Tests run in CI**: All tests above run automatically on every PR (or every merge to main) via the 06_cicd/ pipeline. No "run tests locally if you feel like it." | | |
| 4.6 | **No skipped / xfail tests without rationale**: Any skipped test has an inline comment explaining *why* and *when* it will be re-enabled. | | |
| 4.7 | **Code / logic coverage ≥ target**: (Python only) Line coverage ≥ 80%; branch coverage ≥ 70%. (dbt only) ≥ 90% of models have ≥ 1 schema test each. Coverage report published as a CI artifact. | | |
| 4.8 | **Negative test cases**: At least 1 test per "bad input" class (wrong type, null PK, out-of-range date) verifies that the pipeline either rejects, logs, or correctly handles the bad row — not silently produces garbage output. | | |
| 4.9 | **Regression tests**: Where a bug was fixed during development, a regression test was added that reproduces the exact bug scenario and asserts the fix. | | |
| 4.10 | **Test run output reviewed**: The last CI test run is green (0 failures). If warnings exist, each was reviewed and acknowledged (not just ignored). | | |

**Acceptance Bar**: 4.2, 4.3, 4.5 required for every deliverable touching data pipelines or models. 4.1, 4.7–4.9 required where code is non-trivial (> 50 lines of logic).

---

## 5. ✅ Documentation

> Can a new team member, who has *never spoken to the original author*, fully understand, maintain, and extend the deliverable in 4 hours or less? If not, documentation is incomplete.

| # | Check Item | Applicable? | Evidence / Notes |
|---|---|---|---|
| 5.1 | **Top-level README updated**: Root README links to the deliverable location, its purpose, and how to run it locally. | | |
| 5.2 | **CONTEXT.md updated** (if the deliverable changes any shared KPI def, source system, convention, or assumption). | | |
| 5.3 | **Inline code comments**: Every non-trivial SQL CTE, Python function, or DAX measure has a 1–2 line comment explaining *why*, not just *what*. "Calculate 90th percentile per corridor" is not enough — add "Per stakeholder request in BQ-2025-047 §7 M2." | | |
| 5.4 | **Model / column descriptions**: Every dbt model + column has a description in the `.yml` schema file. Column descriptions are business-meaningful, not just "the wagon code column." | | |
| 5.5 | **Data contract published**: For Gold models, the data contract YAML is committed, validated with the contract linter, and linked from the data catalog (Purview) entry. | | |
| 5.6 | **Runbook exists**: For anything that needs an operator action (deploy, backfill, fix a failure, rollback), a step-by-step runbook exists under `03_docs/runbooks/` and has been *actually followed* by someone other than the author to verify correctness. | | |
| 5.7 | **How-to guide for end users**: For dashboards / reports, a 1-page user guide exists: "How to read this dashboard", "What do the colors mean", "Who to contact with questions", "Known caveats". | | |
| 5.8 | **Architecture decision recorded**: If the deliverable introduced a new pattern, tool, or approach that future maintainers should follow, an ADR is filed (or an existing ADR updated) with rationale + alternatives considered. | | |
| 5.9 | **Report reference-able**: For analysis reports, the `analysis-report.md` has a unique RPT ID, links to reproducible notebooks/code, and all appendices referenced exist. | | |
| 5.10 | **Onboarding-knowledge capture**: Any "tribal knowledge" learned during the project (e.g., "This column is populated only after 3 AM because X batch job runs first") is written into the relevant runbook or CONTEXT.md — not left in Slack or someone's head. | | |

**Acceptance Bar**: 5.1, 5.2 (if applicable), 5.3–5.5 required for *every* deliverable. 5.6 required for anything deployed to PROD that can page someone at 3 AM. 5.7 required for dashboards/reports distributed to non-analytics users.

---

## 6. ✅ Performance

> Does it run fast enough, cheaply enough, and at the required scale?

| # | Check Item | Applicable? | Evidence / Notes |
|---|---|---|---|
| 6.1 | **Model refresh SLO met**: Daily model/dataset refresh runs in less than the allotted batch window (e.g., full nightly Gold ELT ≤ 2.5 hours between 01:00–04:00 UTC). | | |
| 6.2 | **Dashboard load time ≤ target**: Primary dashboard page loads in ≤ 5 seconds at peak concurrency (50 concurrent users for dashboards; 200 for management scorecards). Measured with a load-test tool (k6 / Locust) or documented manual spot-check across 3 different locations. | | |
| 6.3 | **Query performance verified**: The top-5 most-executed dashboard queries each run in ≤ 2 seconds (DirectQuery) or import model refresh ≤ allotted time. Execution plans reviewed; no obvious full-table scans on fact tables without partition pruning. | | |
| 6.4 | **Cost within budget**: Databricks / ADF / Synapse spend for the new workload estimated and signed off against the project budget. No surprise $10k/month from a 100 TB table scan. | | |
| 6.5 | **Partitioning strategy correct**: Fact tables partitioned by the most-commonly filtered date column. Partition size in the "Goldilocks zone" (~1 GB per file for Parquet/Delta; not too many tiny files, not too few huge ones). | | |
| 6.6 | **Maintenance jobs configured**: Delta `VACUUM` + `OPTIMIZE ZORDER` (or equivalent for Iceberg/Hudi) scheduled, configured with appropriate retention (e.g., 168 hr = 7 days for Gold), and log-growth monitored. | | |
| 6.7 | **No N+1 / per-row operations**: ETL uses set-based SQL or vectorized pandas/Spark. No Python `for` row in df: iterrows() or similar antipatterns on datasets > 10k rows. | | |
| 6.8 | **DAX optimizations (Power BI only)**: Import model reviewed with Performance Analyzer + DAX Studio. Measures use `SUMX`/`SUMMARIZECOLUMNS` efficiently. No unnecessary `ALLSELECTED` or implicit measures on large tables. VertiPaq size ≤ target (e.g., < 10 GB for Premium P1). | | |

**Acceptance Bar**: 6.1, 6.3 required for models/pipelines. 6.2 required for any dashboard > 5 users. 6.4 required if spend will change > 10% vs baseline.

---

## 7. ✅ Security & Compliance

> Will the Security / Compliance team sign off? No PII leaks, no over-permissioned access, no audit-trail gaps.

| # | Check Item | Applicable? | Evidence / Notes |
|---|---|---|---|
| 7.1 | **No hard-coded secrets in code or config**: API keys, passwords, connection strings, SAS tokens are **never** committed. All secrets come from `.env` (gitignored) + Azure Key Vault. A `git grep` for "Bearer", "password=", "sk-" returns 0 matches. | | |
| 7.2 | **PII handling correct**: Any column containing PII (phone, email, national ID, driver name, salary) is: (a) masked/pseudonymized in Silver+ layers, (b) protected by CLS (Column-Level Security) policies, or (c) explicitly excluded from the model per scope. PII is never visible to dashboard end users outside HR/Payroll roles. | | |
| 7.3 | **Row-Level Security (RLS) implemented**: For any report with > 1 user-role accessing it, RLS rules match the `01_src/config/rls/*.yaml` definitions: Site managers see only their site; Operations sees no cost data; Finance sees cost data. RLS tested with 3 personas: "What User A sees is not what User B sees." | | |
| 7.4 | **Access review done**: PROD workspace / dataset permissions reviewed. No "everybody in the company has contributor access." Permission list matches documented RACI in `CONTEXT.md §2`. | | |
| 7.5 | **Data residency compliance**: All PII / operational data stays in the required Azure region (West Europe / Amsterdam). No cross-region replication or export outside region for sensitive tables. | | |
| 7.6 | **Audit logging enabled**: Power BI tenant audit logs, dbt run logs, ADF pipeline runs, and storage account access logs are retained per policy (minimum 1 year for SOX-relevant data). Calculation-logic changes for SOX KPIs have a change log. | | |
| 7.7 | **Labor-law compliance (individuals)**: Where the deliverable contains workforce data, no drill-down below 5-individual cohort size. RLS + dashboard filters enforce this minimum cohort size; tested with an analyst trying to drill to 1 person. | | |
| 7.8 | **External data license compliance**: Any third-party data source (SRC-07 weather, SRC-04 GPS) used has its license terms respected: no external sharing, no re-selling, attribution where required. | | |
| 7.9 | **Dependency vulnerabilities scanned**: Python dependencies scanned with `pip-audit` or `safety`. High/Critical CVEs (≥ 7.0) either fixed or a risk-acceptance ticket filed with Security. | | |

**Acceptance Bar**: 7.1, 7.2, 7.5, 7.9 **ZERO TOLERANCE — any open issue blocks PROD deploy.** 7.3–7.4 required for dashboards distributed beyond the analytics team. 7.6 required for KPI feeding financial reports.

---

## 8. ✅ Observability / Monitorability

> If the deliverable breaks at 3 AM, will the on-call engineer (a) know it's broken *before* the business calls, and (b) have enough telemetry to diagnose it in under 15 minutes?

| # | Check Item | Applicable? | Evidence / Notes |
|---|---|---|---|
| 8.1 | **Pipeline failure alerting**: Every scheduled ADF/dbt pipeline triggers a Teams/Slack alert + on-call page (for severity=critical SLO breaches) on failure. No "silent failures" where pipeline red-lights in ADF but nobody gets a notification. | | |
| 8.2 | **Data quality failure alerting**: Severity=error DQ rule failures (from §3) trigger the same alerting path. A failure page lists which rules failed, sample failing rows, and links to the runbook. | | |
| 8.3 | **SLO dashboards visible**: Weekly/monthly SLO compliance (freshness, contract pass rate) is shown on a team dashboard visible to the Business Owner and analytics management. | | |
| 8.4 | **Structured logging**: ETL pipelines emit JSON-structured logs with `run_id`, `model_name`, `row_count`, `duration_ms`, `status`, and `error_stack` (on failure). Logs flow to Azure Monitor / Log Analytics with a 30-day minimum retention. | | |
| 8.5 | **Lineage captured**: Data lineage (source → Bronze → Silver → Gold → dashboard) is available in Purview or dbt docs lineage view. When a stakeholder asks "where does this KPI come from?" you can answer in 2 clicks without reading code. | | |
| 8.6 | **Cost monitoring**: Monthly spend per pipeline / dataset tagged in Azure Cost Management; alert when spend > 120% of trailing 3-month average. | | |
| 8.7 | **User-facing status page** (for critical dashboards): A simple status indicator page (green/yellow/red) + last-refreshed timestamp is embedded in the dashboard footer so users self-serve "is this data up to date?" | | |

**Acceptance Bar**: 8.1 + 8.2 required for any production pipeline or critical Gold model. 8.4–8.5 strongly recommended; make them mandatory if the team has the tooling.

---

## 9. ✅ Peer & Stakeholder Review

> Nobody's perfect. Was this deliverable looked at by another pair of eyes *before* go-live?

| # | Check Item | Applicable? | Evidence / Notes |
|---|---|---|---|
| 9.1 | **Code review completed**: All code changes (dbt models, Python, SQL, DAX, YAML configs) went through a GitHub PR / ADO Pull Request with at least 1 required reviewer approval. No "push directly to main" except emergency hotfixes (which have post-hoc review within 24 hr). | | |
| 9.2 | **Review checklist applied**: PR reviewer checked the substantive parts of this DoD (not just LGTM with no comment). Reviewer called out at least 2 issues or explicitly stated "I found 0 issues after reviewing [X files / Y lines]." | | |
| 9.3 | **SME review signed off**: At least 1 business-domain SME (Rail Ops, Port Ops, Finance — whichever is relevant) reviewed the output for plausibility and signed off. Counter-intuitive findings were discussed, not ignored. | | |
| 9.4 | **Data steward consulted**: For changes that touch shared reference data, column naming conventions, or ERP master data, the relevant data steward (per CONTEXT.md §2) was consulted and any feedback incorporated. | | |
| 9.5 | **Accessibility review for dashboards**: Public-facing or 50+ user dashboards meet basic WCAG 2.1 AA: color contrast 4.5:1, alt text on every chart, keyboard navigation works, no "red = bad" color-only indicators. | | |

**Acceptance Bar**: 9.1 mandatory for everything. 9.2 is a "culture check" — do reviews have teeth? 9.3 required for analysis reports and new KPI dashboards.

---

## 10. ✅ Deployment Readiness

> Is this ready to go into PROD without a panic weekend?

| # | Check Item | Applicable? | Evidence / Notes |
|---|---|---|---|
| 10.1 | **Deployment checklist in runbook**: `03_docs/runbooks/runbook_deploy_prod_release.md` exists, and every step has been successfully executed in UAT exactly as written. No "we'll figure it out on go-live day." | | |
| 10.2 | **Backfill strategy documented & tested**: If deployment requires backfilling historical data (e.g., new column added to fact table), the backfill job has been run in UAT on ≥ 3 months of data; row count + totals match the "before backfill" baseline where expected. Backfill ETA for full PROD history is known (e.g., "2 hr window Saturday 02:00–04:00"). | | |
| 10.3 | **Change freeze window respected**: No PROD deployments during Finance month-end close (T+0 to T+5), or any other freeze documented in `CONTEXT.md §7.2`. Deployment scheduled outside freeze, or freeze exemption signed by CFO + CIO. | | |
| 10.4 | **Stakeholder notification sent**: 48 hours before PROD deploy, an email / Teams post goes to all affected users: "What's changing", "When", "Who to contact with issues", "Known temporary limitations". | | |
| 10.5 | **Blue/green or canary if high-risk**: If the deliverable is a critical pipeline or flagship dashboard, deploy either (a) in parallel with the old version for ≥ 3 business days, or (b) to 10% of users first (canary) then ramp. Compare KPIs side-by-side before cutover. | | |
| 10.6 | **Post-deploy smoke test**: Within 30 minutes after PROD deploy, someone (not the deployer, ideally the Business Owner or QA) runs a 10-item smoke-test script: "Dashboard opens, KPI A = X, filter Y works, export to PDF works." Smoke test pass before anyone signs off. | | |
| 10.7 | **CI/CD pipeline gates**: The 06_cicd/ PROD pipeline requires (a) green CI, (b) green UAT tests, (c) manual approval from 2 named approvers (Analytics Lead + Platform). No "click deploy without checks." | | |

**Acceptance Bar**: 10.1 + 10.3 + 10.6 required. 10.5 required if users > 10 or downtime cost ≥ €100/hr.

---

## 11. ✅ Rollback Plan

> If deploy goes wrong, can we get back to the *previous good state* in under 30 minutes? If not, don't deploy.

| # | Check Item | Applicable? | Evidence / Notes |
|---|---|---|---|
| 11.1 | **Rollback runbook exists**: `03_docs/runbooks/runbook_rollback_release.md` has step-by-step rollback instructions. It was *actually executed* in UAT (or a non-critical moment in DEV) and works — no "the rollback is 'just revert the code'." | | |
| 11.2 | **Time to rollback (TTR) estimated ≤ 30 min**: From decision "we're rolling back" to users seeing the old good version, total time ≤ 30 min. If longer, a *downtime communication plan* is pre-written. | | |
| 11.3 | **Previous version retained**: Previous PROD version of dbt models, Power BI dataset, pipeline configs is retained (not overwritten) for at least 14 days. This means: tagged Docker image, dbt `snapshots` / versioned tables, or Power BI deployment pipeline "previous stage" copy. | | |
| 11.4 | **Rollback decision pre-authorized**: Business Owner and Analytics Lead have pre-agreed: "If, 60 minutes post-deploy, smoke test fails or > 5% DQ failure rate, rollback immediately — no need to schedule a meeting." | | |
| 11.5 | **Post-rollback communication**: Template for the "We rolled back" email / Teams message is pre-written, with: (a) what users experience, (b) when we'll try again, (c) support contact. | | |

**Acceptance Bar**: All 5 items required for anything deployed to PROD that users depend on. "We've never had to roll back yet" is not an excuse to skip this.

---

## 12. Acceptance Sign-Off

> The deliverable is **OFFICIALLY DONE** only when at least the Business Owner + Analytics Lead sign below, AND all Sections 1–11 pass (with documented rationales for N/A / Deferred items).

### Signatures

| Role | Printed Name | Written Approval (e.g., "Approved via email dated YYYY-MM-DD") | Date |
|---|---|---|---|
| **Analytics Engineering Lead** (implementation + DoD integrity) | | | |
| **Business Owner** (requirement met + go-live authority) | | | |
| **Data Steward** (if shared data touched) | | | Optional |
| **Security / Compliance** (if classified Restricted / SOX) | | | Optional |
| **Platform / DevOps** (if infra/CI-CD changes) | | | Optional |

### Residual Open Items (Deferred, Not Blocking Go-Live)

Any `⛔ Blocked` items from Sections 1–11 that were approved for deferral:

| # | Deferred Item from DoD §X.Y | Why Deferral Is Acceptable | Owner to Close | Target Close Date |
|---|---|---|---|---|
| R1 | [e.g., §8.7 User-facing status page not ready] | Dashboard launches to 6 supervisors first; status page 4 weeks later acceptable | [Name] | [YYYY-MM-DD] |
| R2 | | | | |

> **A deferred item is NOT forgotten.** Each one has a work item tracked in ADO/Jira, assigned to an owner, with a committed date. The Analytics Lead reviews deferred items monthly.

---

*DoD Template Owner: Analytics Engineering Guild*
*Last Revised: 2025-07-01 (v1.2 — added §2.9 SCD logic, §8.6 cost monitoring)*
*Next Scheduled Review: 2025-10-01*
