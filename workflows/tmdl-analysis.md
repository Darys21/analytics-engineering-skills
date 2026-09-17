# Workflow: TMDL ANALYSIS — Semantic Model Organization, Governance, and Deployment

## Purpose

Design, review, and maintain a Microsoft Tabular Model Definition Language (TMDL) semantic model (Power BI Dataset / Azure AS / Fabric) that is organized, fully described, source-controlled, validated, and deployable. The semantic model is the single contract between data engineers and BI consumers; a well-structured TMDL enables self-service without producing shadow-BI spreadsheets, while a messy TMDL guarantees governance failure and metric definition drift.

## When to use

- When designing a new semantic model from a signed-off DATA-MODEL star schema.
- When refactoring an existing Power BI dataset (converting from PBIX designer authoring to TMDL source control).
- When preparing a semantic model for cross-workspace deployment via Azure DevOps / Fabric deployment pipelines.
- When performing a governance review of existing datasets: missing descriptions, inconsistent naming, orphaned measures.
- When aligning a dataset with a semantic metric contract and preparing it for Microsoft Fabric OneLake integration.

## Inputs

- Signed-off DATA-MODEL: star schema, grain declarations, SCD plan, relationship map, semi-additive labels.
- Semantic metric contract YAML/CSV from DATA-MODEL step 7.
- Existing TMDL / `.bim` / PBIX model (if refactoring) or the target SQL/gold-mart schema (if greenfield).
- Tabular Editor 3 + TMDL plugin (or TMDL CLI).
- Deployment target: Power BI Workspace, Azure Analysis Services, or Microsoft Fabric workspace.
- Azure DevOps / GitHub repo with a CI runner, and the deployment pipeline configured (or to be configured as part of this workflow).

## Preconditions

- Data model design is signed off and gold mart tables exist in the target data warehouse.
- The user has Tabular Admin / Workspace Admin rights on the target workspace.
- Service principal or managed identity credentials have been created for CI/CD deployments.

## Procedure

1. **Organize the TMDL folder structure and enable source control.**
   1. Export the model to TMDL format if starting from a PBIX/BIM. The standard folder layout:
      ```
      /tmdl
        /model.tmdl                  # root model manifest
        /dataSources/                # one .tmdl per source
          gold_mart_sql.tmdl
        /tables/                     # one .tmdl per table + per-table partitions folder
          dim_date.tmdl
          dim_customer.tmdl
          fct_sales_line.tmdl
          /fct_sales_line/
            partitions.tmdl
            /columns/                # optional: per-column files for very large tables
          ...
        /relationships.tmdl          # central relationship definitions
        /measures.tmdl               # or per-table .tmdl inside each table's folder with measures
        /perspectives.tmdl           # optional: user-role views
        /cultures/
          en-US.tmdl                 # translations, display folders, format strings localized
        /roles.tmdl                  # RLS roles
        /expressions.tmdl            # shared M / calculation items
      ```
   2. Commit the TMDL folder to git as text files; enable line-ending normalization. Never commit the binary `.pbit` / `.pbix` as the source of truth — TMDL text is the source of truth.
   3. Adopt a `main` / feature-branch / PR flow; no direct edits to main.
2. **Design the table layer: naming, hidden/visible flags, row-level descriptions.**
   1. **Every table must have:**
      - **Table name:** PascalCase. `DimDate`, `FctSalesLine`, `BrgOpportunitySalesPerson`. Never `SalesFactTable` or `Dim_Dates` with underscores.
      - **Description:** 1–3 sentences including the table's grain, source, and any warnings. Example: "Sales line grain. One row per invoice line. Source: gold_marts.fct_sales_line, ingested from ERP invoices nightly. Excludes test invoices (is_test = 0) and voided lines via the dq_not_voided assertion."
      - **Data category tag:** Tag as `Dimension` / `Fact` / `Bridge` / `Date` / `Role Playing Dimension`.
      - **IsHidden flag:** True for bridge tables, intermediate M2M tables, utility tables. False for user-facing tables.
   2. **Date dimension conventions:** Tag one table with `IsDateTable = True`, mark its primary `Date` column as the date key. Ensure the date column is contiguous with no gaps for the entire model history range.
   3. **Role-playing dimensions:** Use a single physical `DimDate`; create role-playing perspectives or mark alternate date FK relationships INACTIVE (activated per-measure via `USERELATIONSHIP` in DAX). Never duplicate `DimShipDate` as a separate imported physical table.
3. **Design the column layer: metadata, descriptions, format strings, lineage tags, data categories.**
   1. **Every column must have:**
      - **Column name:** PascalCase. No spaces, no underscores. `SalesAmount`, `CustomerName`, `OrderDateKey`.
      - **Description:** Plain-language business definition, verified by SME. Source column lineage. Example: "Extended line amount = unit_price × quantity ordered before discount. Source: gold_marts.fct_sales_line.extended_amount. Owner: Finance KPI team."
      - **Display folder:** Nested, e.g., `Sales\Base Measures\Revenue` / `Customer\Geography`.
      - **Format string:** Explicit. `#,##0.00 €`, `#,##0`, `0.0%`, `yyyy-mm-dd`, `hh:mm:ss`. No "General".
      - **Data category:** When applicable: `Address`, `City`, `Continent`, `Country`, `County`, `ImageUrl`, `Latitude`, `Longitude`, `Place`, `PostalCode`, `StateOrProvince`, `WebUrl`, `Organization`. Enables Power BI map visuals and default behaviour.
      - **SummarizeBy property:** For numeric columns on dimension tables, explicitly set to `DoNotSummarize` (don't let Power BI default to SUM on a `CustomerAge` column). For fact measures, use `Sum`, `Average`, `Count`, `DistinctCount` matching the grain.
      - **IsHidden:** True for technical columns (SK, NK, batch_id, audit columns, partition keys). False for user-facing attributes.
      - **Nullability / Unique:** Set appropriately; flag PK/SK columns as unique.
   2. **Lineage tagging:** If lineage is tracked externally, add a custom annotation `SourceLineage` to each column with the full path: `gold_marts.dim_customer.customer_key | silver_crm.stg_contacts.id | CRM.dbo.Contact.Id`.
   3. **Synonyms (for Q&A / Copilot):** Add comma-separated synonyms in the `AlternateOf` / linguistic schema: for `SalesAmount` add synonyms "Revenue,Top line,Turnover,Chiffre d'affaires,Ventes".
4. **Design the measure layer: home tables, display folders, descriptions, calculation groups.**
   1. **Measures belong to a home table, never to a "Measures" standalone table.** Put sales measures on `FctSalesLine`, logistics measures on `FctShipment`. Enables natural tooling and user navigation.
   2. **Every measure has:**
      - **Name:** PascalCase noun phrase with no verbs. `GrossMarginPct`, `SalesYTD`, `InventoryClosingBalance`.
      - **Full description in step 1.1 format from dax-analysis.md: context spec + business definition + technical definition + owner.**
      - **Display folder:** Organize at minimum: `Base` / `Time Intelligence\YTD` / `Time Intelligence\YoY` / `Diagnostic` / `Ratios`.
      - **Format string + decimal places explicit.**
      - **Data type:** Double, Integer, DateTime, Boolean, String — match output.
      - **IsHidden:** False for all KPI and diagnostic measures. True for internal helper measures used only inside other measures.
   3. **Calculation groups:** Implement per dax-analysis.md step 7.3. Each calculation group has:
      - A descriptive name: `TimeIntelligence`, `AggregationMode`.
      - A single visible column, e.g., `Time Calculation`.
      - Calculation items with description + format string expression.
      - Precedence correctly set so that time intelligence wraps correctly around aggregation modes.
5. **Define relationships, cardinality, and filter direction explicitly; validate against the model ERD.**
   1. **Every relationship in `/relationships.tmdl` is written explicitly with:**
      - `FromTable` / `FromColumn` (fact FK) → `ToTable` / `ToColumn` (dim SK).
      - `Cardinality`: `ManyToOne`, `OneToOne`, `ManyToMany`.
      - `CrossFilteringBehavior`: `SingleDirection` default, `BothDirections` only for bridge tables (documented individually).
      - `IsActive`: `True` for primary relationship; `False` for role-playing alternates (e.g., ship date, invoice date) activated via `USERELATIONSHIP`.
      - `SecurityFilteringBehavior`: `BothDirections` only when RLS must filter dimension via fact path.
      - `Name`: `FctSalesLine_DimDate_OrderDate`.
   2. **Validate against DATA-MODEL step 6.** Every fact FK has a matching dim SK; no orphan FKs.
   3. **Bidirectional edges audit:** For every `BothDirections`, add a comment in the TMDL documenting justification. Fail PRs on undocumented bidirectional edges.
   4. **Ambiguous path audit:** Use Tabular Editor's "Detect Ambiguities" script; resolve by marking redundant relationships INACTIVE or by adding intermediate bridge tables.
6. **Add perspectives, cultures/translations, roles/RLS, display folders metadata.**
   1. **Perspectives (optional, for large models):** Create one per user persona from the BUSINESS-SPEC: `Executive`, `Site Manager`, `Finance Analyst`, etc. Each perspective hides tables/columns/measures irrelevant to that persona.
   2. **Cultures/translations:** For each required locale, populate `/cultures/<locale>.tmdl` with:
      - Translated table/column/measure names.
      - Translated display folders.
      - Translated descriptions.
      - Locale-appropriate format strings (decimal separator, date format).
   3. **Roles and RLS (Row-Level Security):**
      - One role per user job profile (from personas).
      - RLS filter expressions are explicitly unit-tested. E.g., `DimSite[SiteRegion] = "EMEA"` for the EMEA Manager role.
      - For dynamic RLS (user principal name maps to allowed values): use a dedicated `DimUser` table with `USERPRINCIPALNAME()` mapping; never hardcode email lists in RLS expressions.
      - Document each role's purpose and the list of members / AAD groups assigned.
7. **Configure partitions, incremental refresh, and M / SQL expressions.**
   1. **Partition strategy on every fact table:**
      - Monthly or yearly partitions aligned with the query date range patterns (most queries are <13 months → monthly partitions; most queries multi-year → yearly partitions).
      - A `Current` partition for the open period, plus `Next` (future-proofing), plus `Archive` if data older than N years is rarely queried.
      - Incremental refresh policy on Power BI / Fabric datasets defined in TMDL: `RangeStart` / `RangeEnd` parameters, with detect-data changes enabled on the max watermark column.
   2. **Source queries:** Write explicit SQL queries in each partition source (or M) that selects only required columns (no `SELECT *`), applies the global filters (exclude test, void, is_deleted = 0), and pushes date filters for incremental partitions.
   3. **Define refresh order:** Dimensions first, then facts. In TMDL this is controlled via `maxParallelism` on the refresh orchestrator or deployment pipeline.
8. **Perform structural validation, data-population validation, and deployment simulation.**
   1. **Structural validation (Tabular Editor BPA + TMDL schema check):**
      - Run the BPA rules from dax-analysis.md step 9.3 + TMDL-specific rules: no missing descriptions, no "General" format strings, no bidirectional without comment, no orphan measures, no duplicate display folder paths, no RLS without test cases.
      - Load the TMDL into Tabular Editor; confirm no schema-loading errors.
   2. **Deploy to dev workspace + data-population tests:**
      - Deploy the model to dev, run a full refresh.
      - Validate row counts per table match gold mart row counts (minus the known global filters).
      - Validate that every dimension SK exists on the fact side with ≤0.1% Unknown members (as per data quality).
      - Run the DAX measure test suite per dax-analysis.md step 10.2; assert 0 failures.
   3. **Deployment simulation to staging:** Run the deployment pipeline dry-run against staging (no overwrite yet); confirm the `what-if` diff report: tables added, columns added, measures added, relationships changed. No destructive changes to PROD are allowed without a signed-off migration plan.
9. **Wire up CI/CD: build server, PR gates, deployment pipeline, rollback plan.**
   1. **CI on every PR:**
      - Parse TMDL (schema-valid parse).
      - Run BPA rules; fail on Medium+.
      - Deploy to a transient sandbox workspace, refresh with a small sample partition.
      - Run DAX test assertions; fail on mismatch.
   2. **Staging deploy on merge to main:**
      - Deploy to staging workspace, full refresh.
      - Run full KPI reconciliation workbook against gold mart SQL; fail on delta > tolerance.
      - Run RLS tests: execute queries `EVALUATE ...` impersonating each role, confirm row filters work.
   3. **Production deployment (blue/green if supported):**
      - Deploy to a pre-production slot, full refresh, smoke tests.
      - Swap the dataset binding in Power BI apps / dashboards to the new version atomically.
      - Keep the prior version available for 24h to enable rollback.
   4. **Rollback runbook documented:** If PROD deployment fails KPI smoke tests, revert app/dashboard binding to the previous dataset version within 5 minutes.
10. **Publish to a catalog, document data lineage, and train users.**
    1. **Catalog publish:** Register the dataset in Microsoft Purview / Fabric Catalog / Collibra / internal data catalog with: owner, SLA, KPI coverage, supported personas, freshness SLA, lineage links.
    2. **Lineage end-to-end:** Connect catalog lineage: source system → bronze → silver → gold mart table → TMDL table/column → measure → dashboard tile.
    3. **User training materials:** Produce a "Getting Started with the Sales Semantic Model" guide: which persona uses which perspective, the 10 most-used measures, how to build a basic visual, where to file bugs, the owner contact.
    4. **Schedule a quarterly TMDL review:** Owner + SME review the model for orphaned measures, stale columns, unused tables, new KPI additions needed.

## Decision points

- **Step 1 (TMDL vs BIM vs PBIX).** For models >20 tables or with >5 stakeholders, TMDL text-in-git is mandatory. Small personal datasets can stay as PBIX files without TMDL, but they are not considered governed.
- **Step 4 (Calculation groups vs duplicated measures).** If N × variants >30 total measures, mandatory calculation groups. Under 30, either is acceptable.
- **Step 5.3 (Bidirectional without bridge).** If a developer requests bidirectional filtering for convenience on a star-schema non-bridge relationship, reject. Require a redesigned relationship (bridge table) or a measure-scoped `CROSSFILTER`.
- **Step 7 (Incremental refresh).** For fact tables with >10M rows, incremental refresh is mandatory. For smaller fact tables, full refresh is acceptable (simpler).
- **Step 8.3 (Destructive changes to PROD).** Any change in the TMDL diff that: deletes a table, deletes a column, changes a measure formula in a breaking way, or removes a relationship — requires a signed-off migration plan + a 2-week deprecation window and cannot be deployed as part of a routine release.

## Validation

- Every TMDL file validates against schema (Tabular Editor opens without errors; TMDL CLI parses cleanly).
- Every table has: name, description, category tag, hidden flag correctly set.
- Every column has: name, description, format string (not General), display folder, data category when applicable, SummarizeBy set, hidden flag, lineage tag.
- Every measure has: name, home table (correct), description (context spec + business + tech + owner), display folder, format string, data type, hidden flag.
- Every relationship is explicit in `/relationships.tmdl` with: name, FK→SK direction, cardinality, cross-filter direction, is-active flag. Bidirectional edges have inline comment justifying them; ambiguous-path audit passes.
- BPA rules pass: 0 Medium+ findings.
- Perspectives exist per persona; cultures exist per supported locale with populated translations.
- Roles exist per persona with unit-tested RLS filter expressions.
- Partitions defined with incremental refresh policy for large facts; partition sources use explicit column SELECT (no `SELECT *`), include global filters.
- CI runs BPA + transient sandbox deploy + DAX assertions on every PR, all green.
- Staging deploy: full refresh succeeds; row counts match gold mart within 0.1%; KPI reconciliation passes; RLS tests pass per role.
- PROD supports atomic swap + rollback with documented runbook.
- Catalog entry exists with owner, SLA, lineage end-to-end.
- TMDL review calendar event scheduled quarterly with owner + SME.

## Expected outputs

- A fully populated TMDL folder committed to git with the structure in step 1.1.
- `/docs/tmdl-governance.md` in the repo: naming conventions, description requirements, hidden-flag rules, format-string library, BPA rule exceptions approved.
- BPA report (HTML export from Tabular Editor) showing 0 Medium+ findings.
- Tabular Editor model diagram PDF with tables, relationships, cardinalities.
- KPI reconciliation workbook: staging-model DAX vs gold mart SQL, passing.
- RLS test script: `EVALUATE ...` per role, with expected row-count assertions.
- CI pipeline YAML (Azure DevOps / GitHub Actions) for PR gates.
- Deployment pipeline YAML for staging + PROD with atomic swap + rollback.
- Rollback runbook markdown, tested once successfully against staging before first PROD deploy.
- Catalog registration link + lineage map.
- User onboarding guide: "Getting Started with <Model Name>".
- Work tracking system: PR merged, sign-off from model owner + data governance + business owner.

## Common failure modes

1. **Descriptions are empty.** Users cannot self-serve and open tickets asking "what does SalesAmount mean?" Remedy: step 3.1 / 4.2 require descriptions. Add a BPA rule: "All visible tables/columns/measures must have non-empty description"; fail CI.
2. **Format string = "General".** Same KPI renders as 1.2M, 1234567, or €1,234,567.89 depending on visual defaults. Remedy: BPA rule + CI fail.
3. **Undocumented bidirectional filter edges.** Silent incorrect totals, ambiguous-path errors when adding a new relationship. Remedy: step 5.3 inline comment + audit script; fail PR on missing comment.
4. **Imported duplicate role-playing dates.** DimOrderDate, DimShipDate, DimInvoiceDate all copied. Remedy: step 2.3 single DimDate + inactive relationships.
5. **Partition `SELECT *` + 50 unused columns.** Dataset size balloons by 3×. Remedy: step 7.2 explicit column lists; BPA rule flags `SELECT *` in partition source queries.
6. **Dataset deployed to PROD but no one knows the owner.** A bug is discovered and no one can approve a hotfix. Remedy: step 10.1 catalog entry with named owner; descriptions include owner.
7. **RLS with hardcoded UPN lists.** `CONTAINSSTRING(USERPRINCIPALNAME(), "john@corp.com") || ...` — security hole when someone changes teams. Remedy: step 6.3 DimUser + USERPRINCIPALNAME pattern, BPA rule flags literal UPN strings in RLS.
8. **Destructive column rename deployed with no deprecation.** 15 downstream published reports break overnight. Remedy: step 8.3 what-if diff report; step 9 decision point blocks destructive changes without a plan.
9. **TMDL folder mixed with binary `.pbix` in git.** PR review is impossible; two developers overwrite each other's changes. Remedy: step 1 TMDL-only source of truth; `.pbix` files are gitignored build artifacts.
10. **Calculation groups with wrong precedence.** Time intelligence applied before aggregation mode gives nonsense values. Remedy: step 4.3 precedence documentation + CI test asserting `YTD of SUM = SUM of YTD for baseline.

## References to load

- `references/tmdl-folder-structure-template.zip` — Empty TMDL scaffold with a sample DimDate, one measure table, relationships.tmdl, cultures, roles, perspectives, and a sample partition strategy.
- `references/tmdl-naming-and-metadata-standards.md` — Full standard: PascalCase rules, display folder naming hierarchy, hidden-flag policy, format-string library per business domain (currency, units, percent, count, duration, dates, times).
- `references/tabular-editor-bpa-rules-tmdl.json` — 40 additional TMDL-specific BPA rules (on top of the DAX set): descriptions, format strings, bidirectional with comment, SummarizeBy DoNotSummarize on dims, SELECT* in partitions, hardcoded UPN in RLS, orphan measures.
- `references/tmdl-partition-and-incremental-patterns.md` — Patterns for monthly/yearly partitioning, RangeStart/RangeEnd incremental policies, partitioned Current/Next/Archive, detect-data-changes watermark column pattern.
- `references/rls-dynamic-patterns.tmdl` — Dynamic RLS pattern with DimUser + USERPRINCIPALNAME() + organization hierarchy recursive filter, plus role-based test EVALUATE assertions.
- `references/tmdl-ci-cd-devops.yml` — Azure DevOps multi-stage YAML: build (BPA + parse), test (transient sandbox deploy + DAX assert), deploy staging, deploy PROD with blue/green swap + automatic rollback on smoke-test fail.
- `references/tmdl-what-if-diff-report.py` — Python script (uses Tabular Editor APIs or TOM) to produce a human-readable diff of tables/columns/measures/relationships between two TMDL versions; suitable for PR comment.
- `references/tmdl-kpi-reconciliation-automation.ps1` — PowerShell script that loads a deployed model via ADOMD, runs a list of KPI DAX queries, runs equivalent SQL queries on the gold mart via SqlServer module, writes the reconciliation workbook, exits non-zero on delta > tolerance.
- `references/tmdl-migration-plan-template.md` — Template for destructive change plans: deprecation window (default 14 days), affected downstream report inventory, communication plan, rollback steps, owner sign-offs.
- `references/tmdl-user-onboarding-guide-template.md` — Fillable onboarding guide: personas, perspectives, top 10 measures, common visual recipes, support contacts, links to docs.
- `references/tmdl-analysis-review-checklist.md` — 40-item pass/fail checklist covering every step of this workflow.

## Completion criteria

- TMDL folder exists with full structure, parse-valid, committed to git as the sole source of truth.
- All tables/columns/measures have populated descriptions + explicit format strings (no "General") + display folders + correct hidden flags.
- Relationships are fully documented with cardinality, cross-filter direction, active/inactive. Bidirectional edges have inline comments; ambiguous-path audit passes.
- BPA rules pass 0 Medium+ findings.
- Perspectives per persona, cultures per locale, roles per persona with unit-tested RLS.
- Partitions defined; incremental refresh configured for large facts; no `SELECT *` in partition queries.
- CI pipeline passes on every PR: parse, BPA, transient sandbox deploy, DAX assertions.
- Staging workspace deploy passes full refresh, row-count match gold mart (0.1%), KPI reconciliation, per-role RLS tests.
- PROD deployment pipeline has atomic swap + rollback runbook; rollback tested once in staging.
- Catalog entry registered with owner, SLA, KPI coverage, end-to-end lineage.
- User onboarding guide exists. Quarterly review scheduled.
- Business owner + data governance + model owner all sign off.
