# Workflow: ANALYTICS ENGINEERING — Medallion Architecture, Modularity, Contracts, Delivery

## Purpose

Implement an end-to-end analytics engineering solution using a layered medallion architecture (Bronze → Silver → Gold → Marts) that is modular, reproducible, idempotent, lineage-rich, incrementally refreshable, data-contract protected, tested, documented, convention-named, dependency-managed, CI/CD deployed, and observable. This workflow turns a validated dimensional model into production-grade pipelines that survive six months of turnover, schema drift, and requirement changes.

## When to use

- After `data-modeling.md` has produced a signed-off dimensional model, semantic metric contract, and KPI validation.
- When building or refactoring any repeatable data pipeline that ingests source data and produces analytical tables/models for consumers.
- When onboarding a new data source to an existing medallion lakehouse or warehouse.
- When institutionalizing pipelines that were previously ad-hoc notebooks or one-off scripts.
- When establishing or revising the team's dbt/SQLMesh/dagster/Airflow project structure, testing strategy, or deployment pipeline.

## Inputs

- Signed-off DATA-MODEL document, DDL, semantic metric contract, KPI reconciliation workbook.
- DATA-QUALITY baseline thresholds, assertion suite, data contract (if any).
- Source connection details, credentials, ingestion mechanisms (EL tool, Fivetran, Airbyte, custom extract, Kafka, fileshare).
- Chosen stack: transformation framework (dbt Core/Cloud, SQLMesh, dbt-fabric), orchestrator (Airflow, Dagster, Prefect, Fabric Pipelines, Databricks Workflows), data platform (Snowflake, BigQuery, Synapse Dedicated, Fabric Warehouse, Databricks SQL, Postgres).
- Existing repo conventions: monorepo vs polyrepo, naming conventions, PR process, CI runner access, deployment slots (dev / staging / prod).

## Preconditions

- The dimensional model and KPI formulas have passed step 9 of `data-modeling.md` (source → model → semantic equality).
- Credentials and network access exist for every source and the target platform in all environments.
- A repository exists (or will be created as part of this workflow) with branch-protection rules and CI runner configured.
- The team has agreed (or will adopt in this workflow) a transformation framework and an orchestrator; tool choice is not in debate.

## Procedure

1. **Lay out the medallion layers and repository structure.**
   1. **Bronze (Raw Landing):** Exact copy of source data, 1-to-1 with source tables/files, no transformations beyond type coercion of ingest format artifacts (e.g., CSV strings typed to dates/numbers if preserved exactly). Bronze tables are append-only or overwritten-full per ingestion batch; never update in place. Namespace/schema: `bronze_<source_system>`.
   2. **Silver (Cleaned, Conformed):** Deduplicated, schema-normalized, type-cast, SCD-processed dimension tables and cleaned fact tables with surrogate keys assigned, referential integrity enforced, Unknown members resolved, audit columns populated. Namespace/schema: `silver_<domain>` (e.g., `silver_logistics`, `silver_finance`).
   3. **Gold (Business Facts & Dimensions, Star Schemas):** Final dimensional marts — the stars from DATA-MODEL, conformed across the organization. Namespace/schema: `gold_marts`.
   4. **Exposure Layer (Reports / Semantic Ingest / Feature Store):** Purpose-built views or tables feeding specific dashboards, the semantic layer, or ML feature stores. Namespace/schema: `gold_exposures` / `gold_semantic` / `ml_features` as appropriate.
   5. **Repository structure (dbt-style example, adapt per framework):**
      ```
      /analytix
        /models
          /bronze
            /src_<system1>           -- one subdir per source
              sources.yml
              stg_<system1>_orders.sql
              ...
          /silver
            /<domain1>
              int_<domain1>_order_items_deduped.sql
              dim_customer.sql
              ...
          /gold
            /marts
              fct_sales_line.sql
              dim_date.yml
              mart_sales.yml
            /exposures
              exp_dashboard_sales_exec.sql
              exp_semantic_metrics.yml
        /tests                        -- singular/generic tests + data quality assertions
          /dq_<domain>.sql
        /seeds                        -- CSV reference data (countries, sites, mapping tables)
        /macros                       -- reusable SQL Jinja (SCD Type 2, hash_diff, incremental predicates)
        /analyses                     -- ad-hoc analyst queries, versioned
        /snapshots                    -- framework-managed SCD snapshots
        /target                       -- compiled output (gitignored)
        dbt_project.yml
        packages.yml
        profiles.yml                  -- environment templated, secrets via env vars
      ```
   6. Establish separate environments: `dev` (developer sandboxes), `staging` (CI-built, runs full test suite on production data clone or masked copy), `prod` (publishing to consumers).
2. **Establish naming conventions and enforce them via lint.**
   1. **Table prefixes by layer:** `stg_` (bronze stage), `int_` (silver intermediate), `dim_` (dimension), `fct_` (fact), `brg_` (bridge), `agg_` (aggregate), `mart_` (business mart), `exp_` (exposure).
   2. **Column prefixes:** `sk_` (surrogate key), `nk_` (natural key), `fk_` (foreign key), `is_`/`has_` (booleans), `_at`/`_date`/`_ts` (dates/timestamps with timezone suffix `_utc`), `amt_`/`_amount` / `qty_` / `pct_` / `_id` / `_code` / `_name`.
   3. **Units:** `_kg`, `_usd`, `_eur`, `_km`, `_kwh`, `_per_tonne_km` explicitly in column names; no implicit units.
   4. **Case:** snake_case for SQL identifiers, PascalCase only where the semantic layer TMDL/PBI requires it (bridge via views).
   5. **Timezone:** all timestamps stored as UTC; local timezone is a dimension attribute. Record this rule in the repo README.
   6. Wire in a linter (sqlfluff with a custom ruleset, dbt-codegen, or framework-native lint) as a pre-commit hook and CI gate. Fail PRs on lint violations.
3. **Implement ingestion and bronze staging.**
   1. Wrap each source in a `sources.yml` with metadata: owner, freshness SLA, database/schema/table, loader, tags.
   2. Build one `stg_<system>_<entity>` model per source table. Stage models are 1:1 selective re-naming, type casting, unit normalization of source artifacts (e.g., "all amounts to USD at transaction date FX rate if source is multicurrency", "all timestamps to UTC"). No joins, no deduplication, no business logic in stage models.
   3. Every stage model includes `_source_batch_id`, `_loaded_at_utc`, `_source_filename` audit columns inherited from the ingestion mechanism.
   4. Configure source freshness snapshots in the transformation framework; alert if `loaded_at_field` age exceeds the SLA.
4. **Implement modular silver transformations with reproducibility + idempotency.**
   1. Break business logic into small, single-purpose `int_` intermediate models. Each intermediate does exactly one thing: dedupes, assigns SKs, joins one dimension, applies one business rule. Name the intermediate after the transformation it performs: `int_order_items_dedupe_latest_version.sql`, `int_customer_scd_type2_merge.sql`.
   2. **Reproducibility:** For any given input, running the model twice produces byte-identical output. Implement:
      - Deterministic sort orders in window functions (`ROW_NUMBER() OVER (PARTITION BY nk ORDER BY updated_at DESC, id ASC)` — tiebreakers matter).
      - Pinning of lookup seeds (CSV refs under version control, not live editable).
      - Avoidance of `NOW()` in transformation output; use the batch's watermark timestamp or source timestamp.
   3. **Idempotency:** Running the model N times on the same input yields the same state as running it once. Implement via:
      - Full-refresh models for small tables.
      - Incremental models for large tables with a unique merge key (`incremental_strategy: merge` on mergeable platforms, `insert_overwrite` partitioned for columnar/lakehouse), plus a lookback window for late-arriving data.
      - Idempotent seeds (re-seeding same CSV is safe).
      - Snapshot strategies (framework-managed SCDs) that are rerun-safe.
   4. **Modularity + DAG hygiene:** No circular imports. No model references a model more than 2 layers removed without a documented justification. Keep the DAG shallow; wide, short DAGs are easier to test and debug than deep, narrow ones.
5. **Implement gold marts (dimensional stars) per DATA-MODEL.**
   1. One model per dimension, per fact, per bridge, per aggregate from DATA-MODEL.
   2. Apply the semantic metric contract as a framework-native semantic layer definition (dbt metrics, semantic layer YAML) imported into the `gold/marts` exposure.
   3. Ensure every fact FK resolves to a dimension row or the Unknown member (0 hard NULLs in production).
   4. For every semi-additive measure, write explicit tests that rolling up across time uses the correct aggregation.
6. **Implement incremental processing, late-arriving data, and backfill strategy.**
   1. For incremental models, define the incremental predicate: typically `_loaded_at_utc >= (SELECT MAX(_loaded_at_utc) - INTERVAL '3 DAYS' FROM {{ this }})` — a lookback window larger than the maximum expected late-data delay (per DATA-QUALITY timeliness investigations).
   2. For late-arriving data older than the lookback window, expose a backfill macro or operator that takes `start_date` and `end_date` parameters and re-materializes the affected partitions end-to-end through the DAG.
   3. Never do point-updates on individual rows outside the backfill operator; keep the DAG's behavior explainable.
   4. Configure orchestrator dependencies so that a model runs only after its parents have successfully produced their latest batch.
7. **Define data contracts and test strategy (schema + generic + singular + DQ assertions).**
   1. **Schema tests (every column):** Not null where applicable, accepted values for enums, relationships (FK → SK), unique on SKs and grain keys.
   2. **Generic tests:** Reusable parameterized tests (row count within bounds, sum within tolerance of another model, accepted range, regex pattern) applied via YAML.
   3. **Singular tests (business logic invariants):** SQL queries that return 0 rows on success. Examples:
      - `fct_sales.total_amount = sum of line items ± rounding tolerance`
      - `monthly aggregate = sum of daily rows at that month`
      - `SCD Type 2 rows for a given NK have non-overlapping effective periods and exactly one current_row_flag = 1`
   4. **DQ assertion integration:** Import the `assertions/` suite from `data-quality.md`, tag tests with criticality, and configure the run policy:
      - On PR (dev/staging): run ALL tests.
      - On prod schedule run: run all Critical + Important tests before publish; publish fails on Critical.
      - Post-publish: run remaining Informational tests and alert only.
   5. **Data contract enforcement:** For every contracted source or consumer interface, add contract tests (schema, types, nullable, thresholds per contract). Fail the build on contract breach and notify both producer and consumer leads.
8. **Add documentation and lineage as first-class artifacts.**
   1. Every model has a `description:` in its YAML. Every column of every gold mart has a description sourced from the DATA-MODEL data dictionary.
   2. Attach upstream and downstream `depends_on:` and `exposures:` metadata so the framework can draw a full lineage graph from source table → bronze stage → silver intermediate → gold mart → dashboard/report.
   3. Publish docs on every staging/prod build to an internal static site (dbt docs, SQLMesh docs, Marquez/OpenLineage).
   4. Maintain an `ADR/` directory in the repo: `ADR-001-medallion-architecture.md`, `ADR-002-incremental-lookback-window.md`, etc. Record irreversible architectural decisions with context, decision, consequences.
9. **Implement dependency management, packaging, and secrets management.**
   1. Pin framework versions (dbt-core, adapter, packages) in `packages.yml` / `requirements.txt` / lock files. No floating `latest`.
   2. All secrets (DB passwords, API keys) injected via environment variables or a secret manager; never hardcoded. `profiles.yml` uses `env_var()`.
   3. Reproducible developer environment: `devcontainer.json` / `conda-lock.yml` / `poetry.lock` so a new hire runs one command and gets an identical toolchain.
10. **Configure CI/CD pipeline and deployment strategy.**
    1. **CI on every PR:**
       - Lint (fail on violation).
       - Compile/project parse (fail on broken refs).
       - Spin up an ephemeral dev environment, seed reference data, run a full build of changed models + parents/children.
       - Run full test suite (schema/generic/singular/DQ). Fail on any test failure.
       - Generate a PR diff report: which models changed, which tests would be newly introduced, estimated data-impact on downstream exposures.
    2. **Staging promotion (on merge to main):**
       - Deploy to staging (or production-cloned environment with masked PII).
       - Full build + full test suite.
       - Run KPI reconciliation against signed-off baseline; fail on drift.
    3. **Production deployment:**
       - Blue/green or rolling deployment where supported: new version builds to alternate schema, views swap atomically on successful test pass.
       - Smoke-test post-swap: run 10 critical KPI queries against swapped views, compare to pre-swap stored values, roll back on drift.
       - Post-deploy, tag the commit with the deployed semantic version (e.g., `mart_sales/v1.4.2`).
    4. **Rollback runbook:** Document how to swap views back or restore the immediately previous successful table versions. Practice quarterly.
11. **Build observability, monitoring, alerting, and run history.**
    1. Capture every model run's metadata to a `run_observability` schema:
       - `model_runs`: model_name, env, start_ts, end_ts, status, rows_inserted, rows_updated, bytes_processed, commit_sha, ci_job_id, triggering_user.
       - `test_runs`: test_id, test_name, criticality, passed, observed_value, threshold, sample_count, run_ts.
       - `freshness_checks`: source_name, max_loaded_at, age_minutes, sla_minutes, passed.
    2. Build 3 mandatory dashboards:
       - **Pipeline health:** last 100 runs status, P50/P95 duration per model, top 10 slowest models, failure mode Pareto.
       - **Data quality health:** pass rate by criticality over time, top 10 failing tests, time-to-repair per open incident.
       - **KPI monitoring:** primary KPI per period over last 13 periods with baseline and anomaly band; auto-annotate with pipeline run IDs and schema-change events.
    3. Alert routing:
       - Critical test failures + SLA breaches → PagerDuty/OpsGenie page to on-call data engineer.
       - Important failures → Slack/Teams channel to the analytics team + assigned owner.
       - Informational failures → weekly digest email.
12. **Final review, handoff, and sign-off.**
    1. Walk data engineering and operations through the CI run, lineage graph, observability dashboards, and rollback runbook.
    2. Execute a documented practice rollback: deploy a known-good previous tag end-to-end, confirm KPIs return to baseline values.
    3. Obtain written sign-off from engineering (build passes, tests pass, observability wired) and from the SME/Business owner (gold mart KPIs match baseline reconciliation).
    4. Transition the mart into steady-state operations: add it to the on-call rotation, update the team's service catalog, link runbooks.

## Decision points

- **Step 1.5 (Monorepo vs polyrepo).** Default to monorepo for all analytics code. The cost of coordinating cross-repo lineage, contracts, and CI is higher than the cost of a larger repo. Split only when two teams' deployment cadences and environments are completely decoupled AND contracts between them are stable.
- **Step 4.4 (DAG depth vs breadth).** If a DAG has chains deeper than 5 hops from bronze to gold, split into parallel intermediates where possible. Each additional serial hop adds end-to-end latency and blast radius when a parent fails.
- **Step 6 (Incremental vs full refresh).** Default to incremental for any fact table >10M rows or with >1M new rows per batch; default to full refresh for dimension tables <1M rows unless SCD2 volume justifies incremental. Full refresh is simpler and correct by construction; incremental is a performance optimization with correctness risk.
- **Step 7.4 (What fails the build?).** Define a clear policy in ADR: "Any Critical test fails build on dev/staging/prod; Important fails dev/staging but only pages on-call in prod if SME confirms decision impact; Informational alerts only." Publish this policy to consumers.
- **Step 10.3 (Atomic swap vs in-place rebuild).** Always prefer atomic view swap (blue/green schemas) for gold marts that feed live dashboards. An in-place `CREATE OR REPLACE` during a 10-minute rebuild leaves consumers reading empty or half-loaded tables.
- **Step 11 (Alert fatigue risk).** If more than 3 pages/week leak through to on-call, widen thresholds, add de-duplication (same test failing 3x in 24h = 1 page), or reclassify failing tests. Page-level alerts that are ignored 80% of the time must be fixed or downgraded.

## Validation

- Repository structure matches step 1.5; all four medallion layers are distinct namespaces/schemas.
- Naming conventions are enforced via lint and pass 100% (no exceptions).
- Every source has a `sources.yml` with freshness configured and an SLA.
- Stage models (bronze) perform no joins and no deduplication; silver intermediates are single-purpose.
- Every gold model has documented lineage upstream to at least one source table and downstream to at least one exposure.
- Incremental models have documented lookback windows and a working backfill macro/operator.
- Test suite includes: schema tests (≥1 per column of gold tables), at least 3 singular business invariants per mart, and every DATA-QUALITY assertion tagged with criticality.
- A CI run on a sample PR passes lint/compile/build/test end-to-end.
- Staging full build + KPI reconciliation against signed-off baseline passes at business-equality tolerance.
- Production deployment implements atomic swap (blue/green) and has a practiced rollback runbook.
- Observability dashboards exist for pipeline health, DQ health, and KPI monitoring; alert routing is wired per criticality.
- ADR directory documents all irreversible architectural decisions made in this workflow.
- Engineering and business sign-offs are on file.

## Expected outputs

- Version-controlled repository with the structure from step 1.5, populated end-to-end for the engagement.
- `ANALYTICS-ENGINEERING - <Engagement Name>.md` summarizing: layer layout, naming conventions adopted, incremental/backfill strategy, test policy, CI/CD pipeline, rollback runbook, observability setup, ADR index.
- CI/CD pipeline definition (GitHub Actions, GitLab CI, Azure DevOps, Jenkinsfile) per step 10.
- `ADR-XXX-*.md` files for each irreversible decision (medallion, incremental window, test fail policy, deployment strategy).
- Framework docs site published (dbt docs / SQLMesh docs) with lineage and column descriptions for gold models.
- Three observability dashboards live and populated with at least one successful run of metadata.
- Successful practice rollback recorded as a runbook test.
- Signed-off sign-off sheet from engineering and business owners.
- Work tracking system transitioned to "Steady State Operations" or handed to TMDL/Visualization for exposure building.

## Common failure modes

1. **Logic dumped into a single `fct_` model.** A 1,200-line SQL file does staging, dedupe, joins, business rules, and final aggregation all at once. Remedy: step 4.1 breaks into `int_` intermediates, each <200 lines, each single-purpose. Lint for maximum lines-per-model.
2. **Bronze models contain business logic.** Stage casts "1" to TRUE but also applies a regional-specific FX conversion. Remedy: stage only type-casts/renames; business logic lives in silver. Audit the DAG periodically for strayed logic.
3. **Non-deterministic window functions without tiebreakers.** Two rows tie for `MAX(updated_at)` and different runs pick different winners. Remedy: step 4.2 mandates tiebreakers (`ORDER BY updated_at DESC, id ASC`); add a lint rule.
4. **Incremental lookback window smaller than actual late-data delay.** Rows arrive 4 days late; lookback is 3 days; they are silently dropped. Remedy: derive lookback window from DATA-QUALITY timeliness analysis (max observed late delay × 1.5 safety factor).
5. **Test suite is schema-only.** "All not-null and unique tests pass, yet KPI totals are 2× expected." Remedy: step 7 requires singular business invariants (cross-model totals, additivity, SCD overlap checks) that catch logical bugs schema tests cannot.
6. **No atomic deploy.** Prod rebuild runs 40 minutes. During that window, dashboards are half-loaded. Remedy: step 10.3 blue/green schemas + view swap.
7. **Secrets in repo.** Accidentally committed profiles.yml with passwords. Remedy: step 9.2 env_var-only; add pre-commit secret scanning (gitleaks, detect-secrets) to CI.
8. **Lineage stops at gold.** No one knows which dashboards break if a source column changes. Remedy: step 8.2 requires `exposures:` metadata linking each gold mart to its consuming dashboards/reports/APIs; publish the full graph in docs.
9. **No practice rollback.** When the first prod deployment breaks, no one remembers how to roll back and 3 hours are wasted. Remedy: step 12.2 mandates a practice rollback before sign-off. Rehearse quarterly.
10. **Alert fatigue.** 20 pages/day, all "Informational threshold slightly exceeded." On-call mutes everything; when a real Critical failure happens, it is missed. Remedy: step 11.3 decision point sets a 3 pages/week upper bound.

## References to load

- `references/medallion-architecture-checklist.md` — 25-item checklist validating correct layering between bronze/silver/gold/exposure with examples of common layer violations and how to refactor.
- `references/dbt-repo-template-scaffold.zip` — A ready-to-clone dbt monorepo scaffold with the exact structure in step 1.5, pre-configured sqlfluff rules, example SCD2 macro, example backfill macro, sample ADRs, and a GitHub Actions CI file.
- `references/naming-convention-sqlfluff-rules.toml` — Custom sqlfluff ruleset enforcing prefixes (stg_/int_/dim_/fct_/brg_/agg_/mart_/exp_, sk_/nk_/fk_, units, timezone suffix, snake_case).
- `references/scd-type2-macro.sql.j2` — A battle-tested dbt macro for Type 2 merge with `row_effective_date`, `row_expiry_date`, `current_row_flag`, overlap-prevention assertion, and idempotent re-run handling (5 platform variants).
- `references/incremental-and-backfill-patterns.sql.j2` — Patterns: merge on unique key, insert_overwrite by partition, dynamic 3-day lookback window, date-range backfill macro, orchestrator backfill operator for Airflow/Dagster.
- `references/data-contract-enforcement-dbt-package.yml` — dbt packages.yml + macros for schema-contract enforcement at CI time, including a custom `dbt test contract` command that loads the data-contract YAML from DATA-QUALITY.
- `references/singular-business-test-library.sql` — 30 ready-made singular tests: cross-model additivity, SCD2 overlap, bridge-weight-sum-1, semi-additive-time-sum-check, grain-duplicate, period-close reconciliation.
- `references/github-actions-ci-cd-analytics.yml` — Production GitHub Actions workflow: lint, compile, ephemeral dev env build, test, staging deploy, KPI reconciliation check, blue/green prod deploy with smoke swap + automatic rollback, pager notification.
- `references/run-observability-schema-ddl.sql` — DDL for `model_runs`, `test_runs`, `freshness_checks` tables + ingestion hooks for dbt/SQLMesh to post run metadata automatically.
- `references/pipeline-health-and-dq-dashboards.pbit` — Power BI template (and equivalent Looker LookML) for the 3 observability dashboards, KPI anomaly annotations, and incident MTTR reporting.
- `references/adr-template.md` — Standard ADR template (Context / Decision / Consequences / Alternatives Considered) with 10 pre-filled examples common to analytics engineering.
- `references/analytics-engineering-review-checklist.md` — 50-item pass/fail checklist covering every step of this workflow, usable as a PR rubric.

## Completion criteria

- End-to-end medallion pipeline runs successfully in dev, staging, and prod from source ingestion → gold mart with 0 Critical test failures.
- KPI reconciliation against signed-off baseline passes in prod post-deploy at business-equality tolerance.
- Repository enforces naming conventions with lint; 0 lint violations.
- CI/CD pipeline is wired and passes on every PR with lint / compile / build / full test suite.
- Prod deploy uses atomic swap with smoke KPI tests; rollback runbook exists and has been practiced once successfully.
- DQ assertions run with documented criticality; Critical failures block publish.
- Lineage graph is published and traces every gold mart KPI column back to its source table column and forward to its dashboard/exposure.
- Observability dashboards are live and populated; alerting is wired per criticality, with <3 pages/week leakage.
- ADR directory documents every irreversible architectural decision.
- Engineering and business written sign-offs are on file.
- Work item transitions to steady-state operations or to TMDL / Visualization / Dashboard-UX phases.
