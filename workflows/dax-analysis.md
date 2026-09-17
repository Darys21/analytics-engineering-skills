# Workflow: DAX ANALYSIS — Filter Context, Iterators, and Performance

## Purpose

Write correct, debuggable, performant DAX measures for Power BI / Analysis Services / Fabric semantic models that respect filter context, row context, context transition, relationships, virtual tables, time intelligence, semi-additive behavior, calculation groups, and the Storage Engine vs Formula Engine divide. Avoid anti-patterns that produce silent wrong totals, ambiguous paths, or seconds-long query latency on 100k-row models. DAX is the #1 source of production issues in semantic models; a disciplined workflow eliminates 90% of them.

## When to use

- When writing, reviewing, or refactoring any DAX measure, calculated column, or calculation group in Power BI Datasets / Azure Analysis Services / SQL Server Analysis Services / Microsoft Fabric.
- When porting a BI model from Tableau/Looker to Power BI and translating table calculations to DAX.
- When investigating a "numbers look wrong" complaint that localizes to a measure definition rather than the data model.
- When optimizing semantic model query performance (see also `optimize.md`).
- When designing a semantic layer metric contract to be consumed by DAX writers.

## Inputs

- Signed-off DATA-MODEL document: star schema, grain, relationships, cardinality, filter direction, semi-additive labels.
- Semantic metric contract: KPI formulas, time-intelligence variants, ratio definitions.
- Model `.bim` / TMDL files or access to the open Power BI Desktop file (PBIX).
- DAX Studio or Tabular Editor 2/3 connected to the model, with Server Timings enabled, Query Plan view, and All-Selects enabled.
- Baseline KPI values from the data warehouse (direct SQL query on gold mart) for reconciliation.

## Preconditions

- The data model is designed per `data-modeling.md`: conformed star, single-direction filtering by default, Unknown members, SCD documented, role-playing dates via inactive relationships.
- The analyst has access to DAX Studio + Tabular Editor and is trained on their use.
- Baseline reconciliation values from gold mart SQL are available for the comparison period.

## Procedure

1. **Confirm the evaluation context requirements explicitly before writing any DAX.**
   1. For each measure, write in English:
      - **Filter context expected on report:** which columns (slicers, rows/cols of a matrix, report-level filters) should change this measure's result?
      - **Row context required for calculation:** does the measure need to iterate rows of a table (e.g., margin = revenue - cost on each invoice line, then sum)?
      - **Context transition needed:** do we need to turn row context into filter context (typically inside an iterator, to call another measure)?
   2. Draw a 1-sentence context spec. Example: "`[Gross Margin %]` iterates each row of `fct_sales_line`, computes (amount - cost) per line in row context, sums the result across filtered lines (filter context from matrix and slicers), then divides by sum of amount; it is also used inside per-product/market matrix cells where date/slicer filters apply."
   3. Document the spec as a comment in the measure metadata (description field in Tabular Editor/TMDL).
2. **Use CALCULATE correctly; avoid anti-patterns.**
   1. **CALCULATE = modify filter context.** Every argument after the first is a filter modifier. Know exactly what each modifier does:
      - `Table[Col] = value` → replaces filter on `Table[Col]` with a single value.
      - `FILTER(Table, ...)` → adds a filter by keeping rows that match; FILTER is an iterator and is expensive on large tables. Prefer `CALCULATE(..., KEEPFILTERS(Table[Col] IN {..}))` or `TREATAS` when possible.
      - `ALL(Table)`, `ALL(Table[Col])`, `REMOVEFILTERS(...)`, `ALLEXCEPT(...)` → remove filters; used for percentages of grand total.
      - `USERELATIONSHIP(Table[FK], Dim[SK])` → activate an inactive relationship for this measure ONLY; use for role-playing dates (order date, ship date, invoice date).
      - `CROSSFILTER(Col1, Col2, Both/None/Single)` → override relationship direction for this measure; dangerous outside M2M bridges.
      - `KEEPFILTERS` → intersect an existing filter with the new filter instead of replacing; mandatory inside CALCULATE when you don't want to overwrite user slicer choices.
   2. **Anti-patterns to avoid:**
      - `CALCULATE` wrapping a single aggregator with no filter modifier: `CALCULATE(SUM(...))` is always redundant. Remove it.
      - Boolean predicates on whole tables inside CALCULATE: `CALCULATE([measure], fct_sales[amount] > 1000)` is internally rewritten to `FILTER(ALL(fct_sales), ...)` which can expand to the entire fact table. Always scope to a column: `CALCULATE([measure], FILTER(VALUES(fct_sales[amount]), fct_sales[amount] > 1000))` or use `KEEPFILTERS`.
      - Nested `CALCULATE(CALCULATE(CALCULATE(...)))` — unnest and reason about the filter stack. If more than 2 levels, the measure should be split into helper measures.
3. **Use iterators (X-suffix functions) for row-context logic and ratio safety.**
   1. **Know when to SUM vs SUMX.**
      - `SUM(column)` is a single storage-engine scan. Use for simple additive base measures.
      - `SUMX(Table, Expression)` evaluates Expression in row context for each row of Table, then sums. Required when:
        - The computation has mixed grain (e.g., `SUMX(invoice_header, header_level_amount)` across invoice lines).
        - The expression is an arithmetic combination of columns that must be computed per-row, then aggregated.
        - The numerator or denominator of a ratio is itself a measure, and you need context transition: `SUMX(VALUES(DimDate[Month]), [Monthly Measure])`.
   2. **Ratio and percent-of-total pattern (standard):**
      ```dax
      Margin % =
      VAR Numerator = [Total Gross Profit]
      VAR Denominator = [Total Revenue]
      VAR Result = DIVIDE(Numerator, Denominator, BLANK())
      RETURN Result
      ```
      Then a percent-of-total variant:
      ```dax
      Revenue % of All Markets =
      VAR MarketRevenue = [Total Revenue]
      VAR AllMarketsRevenue = CALCULATE([Total Revenue], ALL(DimMarket))
      RETURN DIVIDE(MarketRevenue, AllMarketsRevenue, BLANK())
      ```
      Never `SUMX(fact, fact[a] / fact[b])` when the ratio should be computed on totals — ratio-of-sums and sum-of-ratios differ. Choose explicitly.
   3. **Other iterators by pattern:**
      - `COUNTROWS(...)` over `FILTER(...)` for conditional counts (preferred to `COUNTX` when expression is a boolean).
      - `MAXX` / `MINX` when comparing expressions, not columns directly.
      - `AVERAGEX(VALUES(DimDate[Date]), [Daily Measure])` to average a daily measure across days in filter context; `AVERAGE([Measure])` as a column measure is rare.
      - `CONCATENATEX` for string aggregation over distinct values.
4. **Master context transition in iterators.**
   1. Context transition rule: inside an iterator, when a measure is referenced, the row context is translated into an equivalent filter context (one filter per column of the iterated table's row, with that row's value). This is `CALCULATE` being called implicitly.
   2. Correct pattern: aggregate a per-day measure over every day in the filtered month.
      ```dax
      Month Avg Daily Balance =
      AVERAGEX(
          VALUES(DimDate[Date]),
          [End of Day Inventory Balance]
      )
      ```
      The row context from each `Date` value transitions to filter context; the semi-additive balance measure runs per day; then the average is taken.
   3. Common bug: iterating the fact table instead of the distinct dimension values.
      ```dax
      -- WRONG: iterates every fact row; if a day has 1000 fact rows, that day is counted 1000x in the average
      AVERAGEX(fct_inventory_movement, [End of Day Inventory Balance])
      -- RIGHT: iterates each distinct day in filter context
      AVERAGEX(VALUES(DimDate[Date]), [End of Day Inventory Balance])
      ```
5. **Leverage variables, relationships, and virtual tables; avoid calculated columns on facts.**
   1. **Variables for readability + single evaluation.** Use `VAR` / `RETURN` extensively. Variables are evaluated once in their definition context and immutable. Splits complex measures into testable chunks:
      ```dax
      Sales WoW % =
      VAR CurrentPeriod = [Sales]
      VAR PriorPeriod = CALCULATE([Sales], DATEADD(DimDate[Date], -7, DAY))
      VAR Delta = CurrentPeriod - PriorPeriod
      RETURN DIVIDE(Delta, PriorPeriod, BLANK())
      ```
      This also makes server timings easier: each variable can be tested individually in DAX Studio.
   2. **Relationships over TREATAS/TREATAS only when needed.** Prefer a proper model relationship (even inactive, used via `USERELATIONSHIP`) to `TREATAS({...}, Dim[Col])` in measures. Relationships provide SE materialization and cardinalities the optimizer can use. `TREATAS` is reserved for ad-hoc bridges and column-name mismatches that cannot be modeled.
   3. **Virtual table techniques:**
      - `SUMMARIZE(...)` for grouping; never add columns in SUMMARIZE that are not the grouping columns — use `SUMMARIZE ... ADDCOLUMNS` pattern or `GROUPBY` for aggregations to avoid the known SUMMARIZE bug in computed subtotals.
      - `ADDCOLUMNS(VALUES(Dim[Col]), "@Metric", [Measure])` pattern is the canonical "add a measure per dimension value" and can be iterated with `SUMX`.
   4. **Avoid calculated columns on large fact tables.** Calculated columns are evaluated at refresh, inflate model size, and almost always can be pushed to the ETL/SQL layer where they process faster and compress better. Exception: small dimension calculated columns (<100k rows) that compute on-the-fly from model relationships are acceptable.
6. **Implement time intelligence on the conformed date dimension; never on the fact date column.**
   1. **Mandatory pattern:** Every time-intelligence function references `DimDate[Date]` (a contiguous date column in the conformed date dimension), never `fct_sales[order_date]`. This is non-negotiable.
   2. **Standard patterns (all reference DimDate):**
      - YTD: `TOTALYTD([Sales], DimDate[Date])` or `CALCULATE([Sales], DATESYTD(DimDate[Date]))`.
      - Same period last year: `CALCULATE([Sales], SAMEPERIODLASTYEAR(DimDate[Date]))`.
      - MTD/QTD/YTD closing balance (semi-additive): `CLOSINGBALANCEMONTH([Balance], DimDate[Date])`.
      - Rolling 30 days: `CALCULATE([Sales], DATESINPERIOD(DimDate[Date], LASTDATE(DimDate[Date]), -30, DAY))`.
   3. **Fiscal variants:** If the fiscal calendar is defined in `DimDate`, pass the year-end-date parameter to `DATESYTD(..., "6-30")` or use custom date ranges via `CALCULATE + FILTER(DimDate, ...)` on fiscal attributes.
   4. **Handling missing dates:** If no sale exists on a date, `LASTDATE(DimDate[Date])` with `LASTNONBLANK` gives the last date with a sale; always wrap semi-additive balance lookups: `CALCULATE([Balance], LASTNONBLANK(DATESBETWEEN(DimDate[Date], STARTOFMONTH(DimDate[Date]), LASTDATE(DimDate[Date])), [Balance])`.
7. **Handle semi-additive measures, dynamic measures, and calculation groups.**
   1. **Semi-additive patterns:**
      - Closing balance across time: `LASTNONBLANKVALUE(DimDate[Date], [Balance])`.
      - Average balance across time: `AVERAGEX(VALUES(DimDate[Date]), [Balance])`.
      - Opening balance: `OPENINGBALANCEMONTH([Balance], DimDate[Date]) = CALCULATE([Balance], PREVIOUSDAY(STARTOFMONTH(DimDate[Date])))`.
      - Never allow `SUM([Balance])` across time in any base measure; wrap the aggregation in a semi-additive wrapper.
   2. **Dynamic measures (switch by slicer):** Use `SELECTEDVALUE` + `SWITCH`, but NEVER write a 50-case SWITCH by hand.
   3. **Calculation groups (preferred for metric variants):** Use Tabular Editor to create a calculation group with a column of calculation items (time intelligence: YTD, YoY, WoW, MOM %; metric aggregations: Sum, Avg, Max, Min, P95).
      - Each calculation item applies a `SELECTEDMEASURE()` transformation.
      - Attach format string expressions so "YoY %" auto-renders as percent.
      - Calculation groups reduce measure count from N×M (base measures × variants) to N + M; mandatory when variants exceed 3 per base measure.
8. **Measure performance: optimize Storage Engine (SE) scans, reduce Formula Engine (FE) serial work, debug cardinality.**
   1. **Run every measure through DAX Studio with Server Timings ON + Query Plan ON.**
   2. **Interpret Server Timings:**
      - Total = SE CPU + FE CPU + Wait. If FE is >50% of total on a simple aggregation, an iterator or a complex FILTER is forcing serial FE work.
      - Look for "SE Queries Count": ideally 1–3 for a simple measure; >10 indicates the formula engine is running many small scans.
      - If "Number of Rows Scanned" in SE is orders of magnitude larger than expected output, the filter is not being pushed to SE (likely because a column predicate was written as a table FILTER anti-pattern).
   3. **Reduce FE work:**
      - Convert FILTER(fact, predicate) patterns to column-scoped filters where possible.
      - Replace `SUMX(fact, expression)` on large facts with a SQL-pushdown computed column + base SUM measure (most impactful single optimization).
      - Reduce iterator cardinality: `SUMX(VALUES(DimProduct[ProductKey]), [Measure])` iterates the distinct count of products, not the fact row count.
   4. **Cardinality checks:** Use `EVALUATE ROW("Cardinality", COUNTROWS(VALUES(fact[col])))` in DAX Studio for every column in a relationship. High-cardinality joins (>1M distinct values) slow SE; if possible, reduce grain upstream in SQL.
   5. **Avoid `ALLSELECTED` traps:** `ALLSELECTED` depends on the exact visual's query shape and can silently break when the user adds/removes columns. Prefer explicit `ALL/ALLEXCEPT/REMOVEFILTERS` + `KEEPFILTERS` when possible.
9. **Debug with DAX Studio; use anti-pattern detector rules.**
   1. **Catch silent wrong totals before stakeholders do:** For every measure, test it in these scopes: (a) grand total row of a matrix, (b) a single cell, (c) a subtotal row, (d) filtered by a slicer that excludes the relationship, (e) filtered to a single date. Compare every result to the gold mart SQL baseline.
   2. **Use Server Timings + Query Plan to localize performance issues:**
      - Vertipaq SE scans: column segments scanned, dictionary hits.
      - Formula Engine callbacks: look for "CallbackDataID" entries in the query plan — they indicate a FE callback per row, which is catastrophic for performance on large cardinality.
   3. **Tabular Editor Best Practice Analyzer (BPA):** Run the community BPA rules against the model; fix every Medium+ severity finding (missing relationships, single direction not default, bidirectional edges, large calculated columns on facts, SUMMARIZE computed column subtotals).
10. **Document, test, and reconcile measures against gold mart.**
    1. **Metadata fields:** Populate for every measure:
       - Description: the step 1 context spec + business definition.
       - Display folder: group by business domain (Sales, Logistics, Finance, etc.).
       - Format string: fixed; never auto. Use calculation groups for variants.
       - Home table: assign each measure to the fact/dim table that owns its semantic meaning (not an "orphan measures" table).
    2. **Testing:**
       - In Tabular Editor / TMDL: use a measure testing framework (e.g., DAX Template or Tabular Editor scripts) that asserts `MEASUREVALUE = expected_value` for 5 known-row cells + baseline grand total.
       - Integrate measure assertions into CI: deploy BIM to a sandbox workspace, run assertions, fail pipeline on mismatch >0.01% of baseline.
    3. **Gold mart reconciliation:** For each KPI, in the baseline period:
       - SQL: `SELECT kpi_formula FROM gold_mart GROUP BY ...`
       - DAX: run the measure in DAX Studio with equivalent filters.
       - Assert `|DAX - SQL| / max(|SQL|, 1e-9) < tolerance` (tolerance typically 0 for integer counts, ≤1e-6 for financials).
       - Publish a reconciliation report as part of every model release.

## Decision points

- **Step 3.2 (Ratio-of-sums vs Sum-of-ratios).** If the stakeholder says "margin percent" and has not specified which, explicitly ask: should the regional margin % be (sum(profit)/sum(revenue)) in that region, or the average of customer-level margin %? The two differ; the default is ratio-of-sums unless stated otherwise.
- **Step 5.4 (Calculated column on fact).** If the computed column is simple arithmetic and the fact is >1M rows, move it to the ETL/SQL layer. Approve calculated columns on facts only when they require cross-table model relationships that the SQL layer cannot conveniently compute, and the fact is small.
- **Step 7.3 (Calculation groups vs SWITCH).** If N base measures × M variants >30 total measures, mandatory calculation groups. Under 30, either is fine; SWITCH is simpler for <5 variants.
- **Step 8.3 (Pushdown to SQL vs DAX optimization).** If `SUMX` over a fact table dominates FE time and the formula is a static per-row computation, push to SQL. If it requires dynamic filter context (e.g., user-selected FX rate), keep in DAX.

## Validation

- Every measure has a populated description field containing its context spec (step 1).
- No orphaned `CALCULATE(agg)` with no filter modifier; every CALCULATE has at least one filter argument.
- Time-intelligence functions reference only `DimDate[Date]`, never fact-table dates.
- Semi-additive measures use LASTNONBLANK / AVERAGEX / CLOSINGBALANCE* wrappers; plain `SUM` is not applied across time.
- Iterators iterate the smallest cardinality possible (dimension key VALUES tables, not fact tables full rows) unless row-level fact columns are required.
- Variables are used for all complex measures; no nested IF/AND/OR spaghetti without VARs.
- Calculation groups are used when variants × base >30.
- No bidirectional filter edges outside M2M bridge patterns; each bidirectional edge is individually documented.
- No `SUMMARIZE` with computed columns (potential subtotal bug); use SUMMARIZE + ADDCOLUMNS or GROUPBY.
- DAX Studio Server Timings show FE CPU ≤50% of total CPU for all KPI measures on the baseline dataset.
- No "CallbackDataID" entries in Query Plan for KPI measures.
- BPA scan shows 0 Medium+ severity findings.
- 5 known-cell values + grand total + YoY + YTD reconcile to gold mart SQL within tolerance.
- Format strings are explicit.
- CI pipeline runs measure tests and reconciliation; fails on mismatch.

## Expected outputs

- A fully documented `.bim` / TMDL semantic model or PBIX with all measures, calculation groups, and metadata per step 10.1.
- A spreadsheet reconciliation workbook: baseline period × KPI × cell × SQL_value × DAX_value × delta × pass/fail.
- A DAX Studio `.dax` query script file for each measure: defines filter context via EVALUATE + ROW or SUMMARIZECOLUMNS, runs the measure, suitable for CI.
- Tabular Editor BPA report (HTML export) with 0 Medium+ findings.
- Server Timings export (CSV) for every KPI measure with annotations.
- Work tracking system: PR with the TMDL/PBIX change, CI green, reconciliation green, review approved.

## Common failure modes

1. **`CALCULATE(SUM(...))` with no filter argument.** Runs but is a warning sign the author did not understand CALCULATE; usually follows bugs when they later add filter logic. Remedy: remove it.
2. **Time intelligence on fact dates.** `SAMEPERIODLASTYEAR(fct_sales[order_date])` silently returns nothing because the fact table has no contiguous dates. Remedy: step 6 mandates DimDate only.
3. **Semi-additive balance summed across time.** Inventory balance sum across January + February = nonsense. Remedy: step 7.1 semi-additive wrappers; base measure never exposes plain `SUM(Balance)` without a wrapper.
4. **Sum-of-ratios vs ratio-of-sums confusion.** Margin % per region = 12% when it should be 9%. Remedy: step 3.2 explicit choice in context spec; the default is always ratio-of-sums.
5. **Iterator over fact table when VALUES(Dim) suffices.** `AVERAGEX(fct_movement, [Daily Balance])` counts movement rows, not days. Remedy: step 4.3 rule.
6. **Boolean table predicates inside CALCULATE.** `CALCULATE([M], fct[a]>1000)` rewrites to FILTER(ALL(fct), ...) and scans 100M fact rows in FE instead of 1M SE. Remedy: step 2.2 anti-pattern detection + scope to column with FILTER(VALUES(...)).
7. **ALLSELECTED silently changes meaning in visuals.** A measure that works in a card breaks in a matrix. Remedy: step 8.5 recommendation to use explicit ALL/REMOVEFILTERS; add UI tests in CI that run a measure in 3 different visual filter shapes.
8. **50-case SWITCH measures with copy-paste.** 1 measure becomes 200 per variant; impossible to maintain. Remedy: step 7.3 calculation groups.
9. **Format string "General".** Numbers auto-format between visuals; users see 1.23M vs 1,234,567 in different tiles. Remedy: step 10.1 explicit format strings, per business domain.
10. **Bidirectional filter spaghetti.** Ambiguous-path errors at design time or silent wrong totals in production. Remedy: default single-direction; documented exceptions only.

## References to load

- `references/dax-context-cheatsheet.pdf` — 1-page visual cheat-sheet: Row Context / Filter Context / Context Transition / CALCULATE modifiers, with 10 worked mini-examples of right vs wrong.
- `references/dax-common-patterns.dax` — 60+ copy-paste DAX patterns: time intelligence (YTD, YoY, WoW, QoQ, Rolling 30/90, custom fiscal), semi-additive (closing/opening/average balance, nonblank period), ratios and percent-of-total, dynamic ranking (TOPN with others), ABC classification, moving averages, basket analysis.
- `references/dax-anti-patterns-and-fixes.md` — Top 20 DAX anti-patterns with exact before/after code and explanation of why the pattern is broken (includes the 10 failure modes above plus 10 more).
- `references/tabular-editor-bpa-rules.json` — Community BPA rule set with 80 rules; import into Tabular Editor.
- `references/dax-studio-server-timings-analysis.md` — Step-by-step interpretation of Server Timings output: SE vs FE, SE Queries Count, Rows Scanned, CallbackDataIDs, xmSQL snippet analysis, missing columns, filter pushdown.
- `references/calculation-groups-cookbook.md` — Cookbook: time-intelligence calc group, aggregation-switch calc group, currency-conversion calc group, KPI-status-with-format-strings calc group; with TMDL JSON fragments and deployment steps.
- `references/dax-measure-testing-ci-template.yml` — Azure DevOps/GitHub Actions template: deploy BIM/TMDL to sandbox workspace, execute DAX queries via `daxado` / `Invoke-ASCmd`, assert values, produce JUnit report, fail on mismatch.
- `references/dax-vs-sql-reconciliation-template.xlsx` — Reconciliation workbook: 5 known cells + grand total + 4 time variants, columns for SQL, DAX, abs delta, rel delta, tolerance, pass/fail; VBA macro to pull SQL via ODBC + DAX via ADOMD.
- `references/semi-additive-measure-patterns.dax` — Complete patterns for inventory balance (LASTNONBLANK, opening/closing/monthly-average), headcount snapshot, project pipeline status with DATESINPERIOD/DATESBETWEEN.
- `references/dax-review-rubric.md` — 25-item pass/fail PR review rubric covering every step in this workflow.
- `references/dax-analysis-review-checklist.md` — 30-item checklist.

## Completion criteria

- Every measure in the scope has been authored/refactored per procedure steps.
- Context spec descriptions exist for every measure.
- DimDate-only time intelligence; 0 uses of fact dates in TI functions.
- Semi-additive measures wrapped; no plain SUM across snapshot time.
- BPA shows 0 Medium+ findings.
- All KPI measures pass gold mart reconciliation within tolerance across: 5 known cells, grand total, YTD, YoY, WoW.
- DAX Studio Server Timings for KPI measures: FE CPU ≤50% of total; 0 CallbackDataID entries; SE queries count ≤10 for baseline.
- CI runs measure test suite; green.
- Calculation groups are used when base × variant >30.
- Format strings are explicit.
- PR description links to: BPA report, Server Timings export, reconciliation workbook export.
- PR reviewed against rubric and merged.
