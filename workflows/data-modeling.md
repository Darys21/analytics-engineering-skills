# Workflow: DATA MODELING — Dimensional Modeling and Semantic Design

## Purpose

Translate a signed-off BUSINESS-SPEC and profiled sources into a correct, performant, maintainable dimensional model (fact and dimension tables) that matches the decision grain, supports all KPIs and driver-tree diagnostics, and feeds a semantic layer that end users and BI tools can consume without writing joins. The model is the durable foundation of every dashboard, report, and downstream analysis. A bad model guarantees years of rework and shadow BI.

## When to use

- After `data-discovery.md` and `data-quality.md` have produced a signed-off fact base and quality baseline.
- When designing a new mart, adding a new business process to an existing warehouse, or re-modelling a legacy mart whose grain or KPIs have drifted.
- When designing a Power BI semantic model (TMDL / Dataset) or a Looker LookML model on top of warehouse tables.
- When refactoring a model to resolve long-standing join-fanout, double-count, or performance bugs.

## Inputs

- Signed-off BUSINESS-SPEC (grain, KPIs with technical definitions, dimensions with cardinality, timeframe).
- DATA-DISCOVERY report (actual source grain, keys, relationship map, RI%).
- DATA-QUALITY baseline thresholds and accepted workarounds.
- Source system ERDs and any existing warehouse models or conformed dimensions already in production.
- Target platform documentation (Synapse, BigQuery, Snowflake, Databricks, Fabric, Postgres) for syntax, indexing, partitioning, and distribution best practices.

## Preconditions

- BUSINESS-SPEC grain is finalized; KPIs are validated computable from sources at that grain.
- Source data access is stable; at least one complete baseline period is loaded in staging.
- Any existing conformed dimensions (date, product, site, customer, asset, employee) are inventoried and their reuse is assessed before creating new ones.

## Procedure

1. **Select the business process and declare the grain.**
   1. Name the business process the model represents (e.g., "Truck Load Dispatch Event", "Sales Invoice Line", "Warehouse Inventory Snapshot", "Employee Payroll Run").
   2. Copy the grain declaration from BUSINESS-SPEC step 8. Refine it using actual source grain from DATA-DISCOVERY step 4. Write a one-sentence grain declaration: "One row in the central fact table represents exactly one ___." Do not use vague phrases like "sales information".
2. **Identify candidate fact types.** Classify the central fact table as one of:
   - **Transaction fact**: one row per discrete event (invoice line, truck trip, machine fault ticket). Grain = event. Facts are mostly additive.
   - **Periodic snapshot**: one row per entity per fixed period (inventory per site per day-end, headcount per department per month-end). Grain = entity × period. Facts are semi-additive (sum across some dims, not across time).
   - **Accumulating snapshot**: one row per entity's lifetime, with multiple date foreign keys tracking milestone events (order received → packed → shipped → delivered → invoiced → paid). Grain = entity lifetime. Facts span a workflow.
   - **Factless fact**: one row per event that has no numeric measure but records a state or coverage (classroom attendance, product promotion listing, employee training completion). Grain = coverage event.
   Select the correct type. Hybrid designs (transaction + snapshot for the same process) are acceptable but require two separate fact tables with explicit documented grain for each.
3. **Design dimension tables.**
   1. **Identify dimensions.** From BUSINESS-SPEC step 7, list every analysis dimension. Map each to either: (a) an existing conformed dimension in the warehouse, or (b) a new dimension to be built.
   2. **Conform first.** Reuse conformed dimensions wherever possible, even if you need to add a handful of new attributes. A dimension is conformed when its keys, attribute names, attribute values, and definitions are identical across every fact table that uses it.
   3. **Natural vs surrogate keys.** Every dimension has exactly one primary key:
      - **Surrogate key (SK)**: an integer or UUID with no business meaning, assigned at dimension load time. Prefer SKs for slowly-changing attributes, type changes, and integration across sources.
      - **Natural key (NK)**: a persistent business identifier from the source (e.g., `employee_number`, `site_code`). Always store the NK alongside the SK in the dimension for traceability.
      On dimension tables, expose the SK to facts. Never join facts to dimensions on NKs that may change.
   4. **Date dimension.** Create or reuse a conformed `dim_date` table at day grain with at minimum: date key (int YYYYMMDD), full date, day of week, day name, week number, ISO week, month number, month name, quarter, semester, year, fiscal variants, holiday flag, working-day flag. For intraday processes, pair with a conformed `dim_time` (second- or minute-grain, 86,400 or 1,440 rows).
   5. **Slowly changing dimension (SCD) strategy per attribute.** For every attribute of every dimension, choose an SCD type:
      - **Type 0 (Retire Original)**: attribute never changes once written. E.g., date of birth, original order date.
      - **Type 1 (Overwrite)**: attribute is overwritten in place; no history. E.g., customer email, product short description when correction only.
      - **Type 2 (Row Versioning)**: new dimension row on every change, with `row_effective_date`, `row_expiry_date`, `current_row_flag` and a new SK. E.g., employee department, site cost center, product category. Use this as the default for any attribute whose change may affect historical KPI attribution.
      - **Type 3 (Add Previous-Value Column)**: add an attribute `previous_<attr>` and optionally `last_changed_date`. History of exactly one change. Rarely appropriate; prefer Type 2 unless business explicitly needs only "current vs previous".
      - **Type 4 (Mini-Dimension + Outrigger)**: for fast-changing high-cardinality attributes (e.g., risk score, temperature band), split into a separate mini-dimension with its own SK, referenced via a fact table FK or an outrigger. Avoids exploding a main dimension.
      - **Type 6 (Type 1 + 2 + 3 Hybrid)**: on a Type 2 dimension, also carry a Type 1 current attribute and optionally a Type 3 previous attribute, so historical reporting can choose lens. Document this explicitly; it adds complexity.
      Document the SCD type per attribute in the data dictionary. Consistency matters.
   6. **Degenerate dimensions.** If a dimension attribute exists only on the fact and has no other attributes (e.g., invoice number on invoice-line grain, ticket number on fault grain), leave it as a column on the fact table (a degenerate dimension). Do not build a one-column dimension.
   7. **Role-playing dimensions.** When one physical dimension is referenced multiple times by a fact via different FKs (e.g., `ship_date_key`, `order_date_key`, `delivery_date_key` all referencing `dim_date`), declare role-playing views or semantic-layer aliases; do not duplicate the date dimension.
   8. **Junk dimensions.** When a fact has 5–20 low-cardinality flags or statuses (e.g., order status, payment method, is_rush, is_gift), combine them into a single junk dimension with one SK per unique combination, rather than adding 20 tiny dimensions or 20 FKs.
   9. **Dimension enrichment.** Add commonly requested textual attributes to dimensions, not to facts. E.g., on `dim_asset`, include `asset_make`, `asset_model`, `purchase_date`, `current_age_years`, `site_name` so facts only carry the `asset_key` FK.
4. **Design the central fact table.**
   1. **Choose the fact table primary key (grain key).** For transaction facts, this may be a degenerate dimension + sequence, or a generated SK. For snapshot facts, it is the cross-product of entity key(s) + period key(s).
   2. **Foreign keys.** Add one FK column per dimension table. FKs match the dimension SK type exactly. Declare FK constraints if the platform enforces them; always declare them logically even if the platform only enforces them in tests.
   3. **Add degenerate dimensions** (step 3.6).
   4. **Add measures.** Separate measures into:
      - **Additive**: sum across all dimensions (e.g., `gross_amount`, `quantity_sold`, `fuel_liters`). These are the backbone of transaction facts.
      - **Semi-additive**: sum across some dimensions but not others. E.g., snapshot inventory balance sums across sites but not across dates (you end with the last balance, not the sum of all balances). For semi-additive measures, document exactly which dimensions support summation and which require LASTNONBLANK / AVERAGE / MAX aggregation.
      - **Non-additive / ratios**: never store in the fact table as a pre-computed ratio (e.g., unit_price, margin%). Always store the numerator and denominator as additive measures and compute the ratio in the semantic layer or BI tool, so slice-and-dice never double-counts ratios of aggregates.
   5. **Null handling.** Foreign keys to missing dimension members should resolve to a designated "Unknown" row (SK=0 or -1) with descriptive attributes like `site_name = 'Unknown Site'` rather than SQL NULL. NULLs in measures (e.g., a `return_amount` on a non-returned sale) are acceptable if documented; decide whether they are treated as 0 or as missing in aggregations and write that rule into the semantic layer.
   6. **Audit columns.** Every fact and dimension table carries: `_loaded_at_utc TIMESTAMP`, `_source_batch_id STRING`, `_source_filename STRING` (if file-based), `_hash_diff STRING` (for incremental CDC detection). Audit columns never appear in the semantic layer exposed to users but are mandatory for traceability and backfills.
5. **Design bridge tables, aggregations, and outriggers.**
   1. **Bridge tables for many-to-many.** When a fact row legitimately relates to N members of a dimension (e.g., one sales-opportunity has N salespeople sharing commission, one repair order touches N asset components), introduce a bridge table between the fact grain key and the dimension SK, plus an allocation factor `bridge_weight` summing to 1 per fact row. Document the allocation method (equal split, revenue-weighted, user-entered). For less-sophisticated BI tools, alternatively create a factless bridge and use `CROSSFILTER` / bidirectional filtering with extreme caution.
   2. **Outrigger dimensions.** If a dimension references another dimension (e.g., `dim_product` references `dim_product_category`), resolve the snowflake into a single denormalized dimension unless the outrigger is shared independently across multiple dimensions. Kimball prefers star over snowflake for usability and performance.
   3. **Aggregate fact tables.** For heavy dashboards querying years of data at month-grain, build an aggregate fact table at a coarser grain (e.g., `fct_sales_monthly_site_product`) pre-aggregated from the atomic fact. Aggregates must align 100% with atomic when rolled up. Prefer automated aggregate navigation in the semantic layer rather than asking users to choose the table.
6. **Define the relationships, cardinality, and filter direction.**
   1. For every (fact FK, dimension SK) pair:
      - Declare cardinality explicitly. Standard Kimball star is fact `N : 1` dimension single-direction (dim filters fact).
      - Confirm with DATA-DISCOVERY step 11 RI rates. Any known exceptions route to the Unknown member row.
   2. **Filter direction rule.** In the semantic layer (Power BI, Analysis Services, Looker):
      - Default to single-direction filter propagation from dimension to fact.
      - Use bidirectional filtering only when strictly required for a specific pattern (bridge tables with allocation, M2M patterns) and document every bidirectional edge. Uncontrolled bidirectional filtering is the #1 cause of ambiguous path errors and silent wrong totals.
   3. **Ambiguous paths.** If a dimension can reach a fact via two routes (e.g., `dim_date` joins directly to `fct_sales` and also via `dim_customer.activation_date_key`), declare a single active relationship and mark the rest `INACTIVE`, using `USERELATIONSHIP` (DAX) or equivalent only where that alternate lens is needed.
7. **Define metric definitions and the semantic layer contract.**
   1. For every KPI and diagnostic measure from the BUSINESS-SPEC, write a formal semantic-layer metric definition independent of any particular BI tool:
      - **Metric name and description.**
      - **Base measures (from fact) and the aggregation function applied to each (SUM, AVERAGE, MAX, LASTNONBLANK).**
      - **Semi-additive handling rules per dimension type.**
      - **Applicable filters and their default scope.**
      - **Time intelligence variants (YoY, WoW, MTD, QTD, YTD, Running Total, Moving Avg 7/30/90).** Use the conformed date dimension rather than native date functions.
      - **Ratio and derived metric formulas using base measures; ensure numerator and denominator respect filters independently.**
   2. Publish the metric contract to a catalog (dbt docs, semantic hub, data dictionary). This contract is the single source of truth: two reports using the same metric name must compute the same formula.
8. **Implement the physical model (DDL + load logic).**
   1. Write DDL for every table: column names, types, nullability, primary keys, foreign keys (or assertions for columnar platforms that don't enforce FKs), distribution / sort / partition keys.
      - Partition large fact tables on the primary date key (year-month or ingestion date).
      - Distribute fact tables on a high-cardinality evenly-distributed key; co-locate frequently-joined dimensions if the platform supports it.
      - Index dimension SK columns on facts and SK + NK + frequently-filtered attributes on dimensions.
   2. Write idempotent load logic (dbt model, stored procedure, Spark job, etc.):
      - Dimensions: SCD Type 1 overwrite or Type 2 merge, producing correct SKs.
      - Facts: full refresh or incremental (merge by grain key, insert-or-update by CDC hash).
      - Include assertions for uniqueness of grain keys, FK integrity (all fact FKs present in dims or Unknown member), and additivity sanity checks (sum at month grain from atomic = sum from monthly aggregate).
9. **Validate the model against the BUSINESS-SPEC.**
   1. **Grain test:** take 10 random grain keys and show the team one row each with all columns populated; confirm it represents exactly one instance of the declared grain.
   2. **KPI recomputation test:** manually compute the primary KPI for the baseline period directly from sources using the BUSINESS-SPEC technical formula. Compute it via the semantic-layer metric. They must match at business equality tolerance.
   3. **Dimension-slice test:** compute the primary KPI for each member of each analysis dimension, both from source and via model. Totals must still match; no slice may be 0 when source had data, no slice may be inflated by fan-out.
   4. **Time-comparison test:** compute YoY and WoW variants for the baseline period; confirm period-over-period deltas match expected SME values.
   5. **Semi-additive sanity:** for snapshot facts with semi-additive measures, confirm rolling up across dates produces LAST-period values, not SUM-of-all-periods.
10. **Document and publish.**
    1. Update the data dictionary with every table, every column, SCD type per attribute, grain declaration, measure additivity, Unknown row conventions, audit column usage.
    2. Publish an ERD (star schema diagram) with cardinality labels on every relationship.
    3. Walk the SME, data engineering, and BI team through the model. Resolve open questions.
    4. Obtain sign-off on the KPI recomputation test results and the semantic metric contract.

## Decision points

- **Step 1 (Grain ambiguity).** If stakeholders want "a sales dashboard" that simultaneously reports invoice-line grain and invoice-header grain (e.g., freight cost lives at header and product revenue lives at line), build two fact tables sharing conformed dimensions, plus a conformed `dim_invoice` degenerate-header dimension. Never pack two grains into one fact table; it produces unfixable double-count.
- **Step 2 (Snapshot vs Transaction).** If the KPI is "inventory at day-end" and the only source is individual movement transactions, build both an atomic `fct_inventory_movement` (transaction) and a `fct_inventory_snapshot_daily` (periodic snapshot) derived from it. The atomic fact answers "why did inventory change?"; the snapshot answers "what was the balance?".
- **Step 3.5 (SCD type disputes).** Default to Type 2 for any attribute that changes and whose historical value would change KPI attribution (e.g., a sales rep's territory). Only use Type 1 when the change is explicitly a correction, not a real-world state change.
- **Step 5.1 (Many-to-many without allocation factor).** If a bridge is needed but no agreed allocation method exists, do not default to equal split; equal split silently misstates 90% of slices. Either pause to negotiate an allocation rule, or expose the bridge without allocation and require users to consciously pick an aggregation rule (documented as a caveat).
- **Step 6.2 (Bidirectional filtering).** If a BI developer requests bidirectional filtering outside bridge/outrigger patterns, reject the request and ask for the exact calculation they want. 95% of the time, the need is met with a `CALCULATE` containing `CROSSFILTER` scoped to that one measure, not a global model setting that affects every query.
- **Step 7 (Metric re-definition conflicts).** If two teams want the same metric name to compute different formulas, create two distinct metric names and retire the ambiguous one. Metric name uniqueness is non-negotiable in the semantic layer.

## Validation

- The grain declaration is written as a one-sentence, row-level concrete statement with no ambiguous nouns.
- A signed-off grain test on 10 sample rows is on file.
- Every dimension has exactly one SK primary key and stores its NK for traceability.
- SCD type is documented per dimension attribute; Type 2 rows carry effective/expiry/current flags.
- A conformed `dim_date` is referenced via all date FKs; role-playing dates are views/aliases, not physical duplicates.
- Every fact FK resolves to a dimension row or the Unknown member (0 hard SQL NULLs on FKs in production).
- Semi-additive measures are explicitly labeled and their valid-aggregation dimensions listed.
- No pre-computed ratios exist in fact tables; ratios are semantic-layer formulas over additive numerator/denominator.
- Bridge tables exist for every M2M relation; bridge_weight sums to 1 per fact row.
- KPI recomputation test passes at business-equality tolerance for baseline period across every dimension.
- Physical DDL includes partitioning, distribution, and indexing strategies matching the target platform.
- ERD with every relationship and its cardinality exists.
- Semantic metric contract is published and contains every KPI + standard time-intelligence variants.
- SME, data engineering, and BI team written sign-off is on file.

## Expected outputs

- `DATA-MODEL - <Engagement Name>.md` containing: business process, grain declaration, fact-type classification, dimension list (with SCD plan per attribute), fact table design (FKs + measures + additivity), bridge and aggregate plan, relationship map, semantic metric contract, and KPI validation results.
- Physical DDL script(s): `ddl/<platform>/create_<mart>.sql` with all tables, keys, distribution/partition/index directives.
- Load models/logic: dbt SQL models, Spark notebooks, or stored procedures implementing SCD and incremental loads.
- Star schema ERD: `erd/<mart>-star-erd.png` + editable source (draw.io / Mermaid).
- Data dictionary export: `data-dictionary-<mart>.csv` — table, column, type, nullability, description, SCD type, additivity, source lineage.
- Semantic metric contract: `semantic-metrics-<mart>.yml` or equivalent, importable by the semantic layer tool.
- KPI reconciliation workbook: `validation/kpi-reconciliation-<period>.xlsx` proving 3-way match (source SQL → model SQL → semantic layer).
- Work tracking system updated with sign-off status and any open remediation items.

## Common failure modes

1. **Fact table packs two grains.** Sales invoice line and header amounts in one table cause freight cost (header) to multiply by line count. Remedy: step 1 decision point + two separate fact tables with documented grain.
2. **Join on NK instead of SK.** An employee's department changes and historical reports are silently re-attributed to the new department. Remedy: only SKs in fact FKs; enforce in DDL and tests.
3. **SCD Type 1 overwrites everything.** History is lost on every attribute change. Remedy: default to Type 2, explicitly justify Type 1 per attribute in the data dictionary.
4. **Semi-additive measures summed across time.** Inventory balance is summed across days, producing nonsensical year totals. Remedy: step 4.4 labels additivity; step 9.5 validates; semantic-layer metrics must use LASTNONBLANK or equivalent.
5. **Pre-computed ratios stored in facts.** Unit price × SUM(quantity) ≠ SUM(line_amount) because of rounding. Remedy: store numerator/denominator, compute ratio in semantic layer.
6. **Snowflakes everywhere.** Dimensions reference subdimensions reference subdimensions, BI users need 7 joins to report a KPI. Remedy: denormalize into stars, accept minor dimension storage cost for huge usability and query-plan wins.
7. **Bidirectional filter spaghetti.** Power BI model throws ambiguous-path errors or computes incorrect grand totals. Remedy: step 6.2 default single-direction; document every bidirectional edge individually.
8. **Unknown dimension keys set to NULL.** `LEFT JOIN`s silently drop rows when users filter by dimension. Remedy: explicit Unknown SK=-1 with populated descriptive attributes on every dimension.
9. **Missing audit columns.** When a production KPI goes wrong, no one can tell which source batch produced it or when it landed. Remedy: step 4.6 audit columns are non-negotiable.
10. **No conformed date dimension.** Time intelligence uses built-in `DATEADD`/`CALENDAR` functions that don't know the company fiscal calendar or holidays. Remedy: step 3.4 mandates a conformed `dim_date` with fiscal/holiday variants.

## References to load

- `references/kimball-grain-declaration-examples.md` — 30 well- and poorly-stated grain declarations across 10 industries, with red-pen corrections.
- `references/fact-type-decision-tree.md` — decision tree: Transaction vs Periodic Snapshot vs Accumulating Snapshot vs Factless, with worked examples and when to build hybrid pairs.
- `references/scd-types-cheatsheet.md` — one-page Type 0/1/2/3/4/6 cheat-sheet with SQL merge examples for a Kimball Type 2 dimension (dbt macro + raw SQL variants for 5 platforms).
- `references/conformed-dim-date-ddl.sql` — production-grade `dim_date` DDL + seed script with 100 years of dates, fiscal variants, holiday flags, working-day flags (configurable by country).
- `references/semi-additive-measure-patterns.dax` — DAX patterns for LASTNONBLANK, LASTDATE, AVERAGEX over dates, opening/closing balance, YTD average balance; equivalent SQL and LookML patterns.
- `references/bridge-table-m2m-patterns.md` — bridge patterns: equal split, weighted allocation, coverage factless; DAX/CALCULATE + CROSSFILTER patterns, allocation-factor validation SQL.
- `references/unknown-member-conventions.md` — standard SK=-1 row values for 15 common dimension types (date, site, product, customer, asset, employee, etc.) and SQL to insert them.
- `references/star-schema-erd-stencils.drawio.xml` — draw.io stencil kit for star ERDs with fact/dim shapes, cardinality labels, bridge/outrigger shapes.
- `references/kpi-reconciliation-workbook-template.xlsx` — 3-way (source SQL → model SQL → semantic layer) reconciliation template with delta columns and pass/fail conditional formatting.
- `references/semantic-metric-contract-yml-schema.md` — YAML schema for the semantic metric contract with examples, plus conversion scripts to dbt metrics, Power BI TMDL, and LookML.
- `references/data-modeling-review-checklist.md` — 40-item pass/fail checklist covering every step.

## Completion criteria

- `DATA-MODEL - <Engagement Name>.md` exists with every required section; grain declaration is a single concrete row-level sentence.
- Physical DDL scripts exist for every table and include target-platform distribution, partitioning, and indexing.
- DDL implements the declared PK/FK conventions, Unknown member placeholder conventions, and audit columns on every table.
- Load logic is idempotent and implements the documented SCD types for every attribute.
- Semantic metric contract exists as a machine-readable YAML (or equivalent) containing every KPI and standard time-intelligence variant.
- KPI recomputation test passes for baseline period: source direct SQL, model SQL, and semantic-layer metric all agree at business-equality tolerance.
- Dimension-slice tests pass for every analysis dimension: per-member totals match source, no fan-out, no zero-slice where source had data.
- Star ERD exists with every relationship and its cardinality labeled.
- Data dictionary CSV exists for the mart: every column described, SCD type per attribute, additivity per measure.
- SME, data engineering, and BI team written sign-off is on file accepting the model design and KPI validation results.
- Work tracking system transitions the engagement to Analytics Engineering (build pipelines/tests/docs) or TMDL/Visualization as appropriate.
