# Workflow Catalog

This document is the master index of agent workflows. Each row is a repeatable
task the agent knows how to perform. Use it to discover the right workflow
for a job, to understand what inputs are required, and to see how workflows
compose into larger pipelines.

> New workflows should be added to both this table and to `SKILL.md` so the
> agent can discover them.

## Workflow Table

| ID / File | Purpose | When to Use | Composes With / Calls | Outputs |
|---|---|---|---|---|
| **1. Source Data Onboarding**<br>`workflows/onboard_source_system.md` | Bring a new source system or feed into the warehouse staging layer end to end. | A new data source is identified, extraction credentials are available, and business owner has signed off on freshness/SLA. | `profile_source_data.md`, `design_staging_schema.md`, `create_staging_sql.md`, `review_staging_sql.md`, `run_data_quality_checks.md` | Staging tables (DDL + SQL), data quality report, staging ERD snippet, load schedule entry. |
| **2. Profile Source Data**<br>`workflows/profile_source_data.md` | Measure structure, completeness, uniqueness, value distribution, and anomalies of a raw or staged dataset. | Before any SQL model is designed; when validating a new external feed; periodically to detect drift. | `scripts/quality_check.py`, `references/iqr_outliers.md`, `references/naming_conventions.md` | Data quality report (JSON + summary), completeness matrix, uniqueness per column, PK candidate list, known-issues tracker. |
| **3. Design Staging Schema**<br>`workflows/design_staging_schema.md` | Define column names, types, nullability, and audit fields for 1:1 landing zone tables. | Source profile is in hand; before writing staging SQL. | `references/naming_conventions.md`, `references/audit_columns.md`, `templates/tmdl_table_template.tmdl` (if semantic model is part of scope). | Column list (table), staging-ERD, list of type coercions and why. |
| **4. Create Staging SQL**<br>`workflows/create_staging_sql.md` | Write the transformation SQL that moves source columns into staging schema (cast, rename, add audit fields). | Staging schema is approved by review. | `templates/sql_model_template.sql`, `references/sql_style.md`, `scripts/validate_sql.py` | Stored SQL model per source table. |
| **5. Review Staging SQL**<br>`workflows/review_staging_sql.md` | Structured pre-merge review of a staging SQL model. | A staging SQL model is submitted for PR. | `scripts/validate_sql.py --strict`, `references/sql_style.md`, `evals/sql_staging_review/` | Review checklist with pass/fail, actionable comments, approval or rejection. |
| **6. Run Data Quality Checks**<br>`workflows/run_data_quality_checks.md` | Run the `quality_check.py` validator against a model's output and compare to thresholds. | After every staging load; on every PR that changes SQL; on schedule. | `scripts/quality_check.py`, `references/data_quality_thresholds.md` | Quality report JSON, diff vs previous run, alert on threshold breach. |
| **7. Star Schema Design**<br>`workflows/star_schema_design.md` | Design a star schema: identify facts, dimensions, grains, conformed keys. | Business process is well-understood and source data has landed. | `dimension_table_design.md`, `fact_table_design.md`, `references/slowly_changing_dimensions.md`, `templates/tmdl_table_template.tmdl` | Star schema ERD, list of tables with grains, SCD-type decisions, relationship matrix. |
| **8. Dimension Table Design**<br>`workflows/dimension_table_design.md` | Design one dimension: keys, attributes, SCD strategy, audit columns. | A dimension is identified by the star schema workflow. | `references/slowly_changing_dimensions.md`, `references/naming_conventions.md`, `templates/sql_model_template.sql` | Per-dimension column list, SQL template populated, TMDL column stub. |
| **9. Fact Table Design**<br>`workflows/fact_table_design.md` | Design one fact: grain, measures, foreign keys, additivity, degenerate dims. | A fact is identified by the star schema workflow. | `references/fact_additivity.md`, `references/naming_conventions.md`, `templates/sql_model_template.sql` | Per-fact column list, SQL template populated, additivity notes per measure. |
| **10. Write SQL Model (Star Layer)**<br>`workflows/create_star_sql.md` | Write the SQL that produces a dimension or fact table output. | Dimension/fact design is approved. | `templates/sql_model_template.sql`, `scripts/validate_sql.py --strict`, `references/sql_cte_patterns.md` | Validated SQL model, materialization hint (view vs table/incremental). |
| **11. Semantic Model — TMDL**<br>`workflows/create_tmdl_model.md` | Create or update TMDL (Tabular Model Definition Language) artifacts for tables, columns, measures, hierarchies, relationships. | Star schema SQL models exist and are validated; semantic layer is in scope. | `scripts/validate_tmdl.py`, `templates/tmdl_table_template.tmdl`, `references/tmdl_relationship_patterns.md` | TMDL files per table, relationship manifest, measure folder layout. |
| **12. Semantic Model — DAX Measures**<br>`workflows/create_dax_measures.md` | Implement DAX measures on top of a semantic model. | TMDL tables and relationships exist. | `references/dax_patterns.md`, `scripts/validate_dax.py --strict`, `references/dax_calculate_semantics.md` | `.dax` files or embedded expressions, display folder assignments, format strings. |
| **13. Review DAX Measures**<br>`workflows/review_dax_measures.md` | Structured review of a DAX measure implementation: correctness, performance hints, readability. | A measure is submitted; before merging to the semantic model. | `scripts/validate_dax.py --strict`, `references/dax_patterns.md`, `evals/dax_measure_review/` | Measure scorecard, anti-pattern list, refactor suggestions, approval. |
| **14. Review TMDL Model**<br>`workflows/review_tmdl_model.md` | Structural review of a TMDL semantic model: attributes, relationships, naming, formats. | TMDL is submitted for merge or deployment. | `scripts/validate_tmdl.py --strict`, `references/tmdl_relationship_patterns.md` | Structural review report, relationship integrity check, naming/format issues. |
| **15. Impact Analysis (Change)**<br>`workflows/impact_analysis.md` | Before changing a model, identify downstream artifacts affected. | PR proposes changes to a SQL model, TMDL column, or DAX measure. | `evals/impact_analysis/` | Downstream dependency list, affected reports, suggested owners to tag on PR. |
| **16. Backfill / Re-run**<br>`workflows/backfill.md` | Safely re-process a historical range for an incremental model. | A bug was fixed and historical outputs are wrong; or a new column is added and must be populated historically. | `profile_source_data.md`, `run_data_quality_checks.md` | Backfill window selection, load order, pre/post quality snapshots, runbook. |
| **17. New Contributor Onboarding**<br>`workflows/new_contributor_onboarding.md` | Walk a new contributor through creating their first workflow or evaluation case. | A new engineer joins the team, or an external contributor opens their first PR. | `CONTRIBUTING.md`, `docs/contribution-guide.md`, `scripts/validate_project.py` | First PR opened, validator passes, reviewer assigned. |

## Composing Workflows: Example Pipelines

The table above describes atomic workflows. In practice the agent will chain
them into larger jobs. These are typical compositions — not hard-coded, but
worth knowing about so that references can be shared.

### Pipeline A: Onboard a New Source

```
onboard_source_system.md
 ├─ profile_source_data.md        ──► quality_check.py + profile report
 ├─ design_staging_schema.md      ──► column list + types
 ├─ create_staging_sql.md         ──► SQL models
 ├─ review_staging_sql.md         ──► validate_sql.py --strict
 └─ run_data_quality_checks.md    ──► quality_check.py vs thresholds
```

### Pipeline B: Build a Star Schema + Semantic Model

```
star_schema_design.md
 ├─ (for each dim) dimension_table_design.md
 │   └─ create_star_sql.md          ──► validate_sql.py --strict
 ├─ (for each fact) fact_table_design.md
 │   └─ create_star_sql.md          ──► validate_sql.py --strict
 ├─ create_tmdl_model.md            ──► validate_tmdl.py --strict
 ├─ create_dax_measures.md          ──► validate_dax.py --strict
 ├─ review_tmdl_model.md
 ├─ review_dax_measures.md
 └─ run_data_quality_checks.md      ──► quality_check.py on fact outputs
```

### Pipeline C: Review a PR Touching the Semantic Layer

```
impact_analysis.md
 ├─ review_staging_sql.md / review_star_sql.md
 ├─ review_tmdl_model.md
 └─ review_dax_measures.md
```

## Adding a New Workflow

1. Copy `templates/workflow_template.md` (if it exists — otherwise create a
   new file with the sections: **Inputs**, **Steps**, **Validator Gates**,
   **Outputs**, **Failure Modes**).
2. Give it a stable, descriptive filename. Do not rename existing IDs.
3. Add a row to the table above.
4. Add a one-line entry to `SKILL.md` so the agent can discover it.
5. Add at least one evaluation case under `evals/<workflow-id>/`.
6. Run `validate_project.py --strict` and open the PR.

The full step-by-step walkthrough with examples is in
`docs/contribution-guide.md`.
