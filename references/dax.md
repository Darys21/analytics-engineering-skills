# DAX Reference Guide (Data Analysis Expressions)

## Claim categories
This reference uses five categories of guidance. Do not treat all recommendations as equally strict.

| Category | Meaning | Action if violated |
|----------|---------|--------------------|
| **Hard correctness rule** | Breaking this produces provably wrong numbers (wrong totals, wrong filter context, silent wrong semantics) in all or nearly-all cases. | MUST fix before merge. |
| **Preferred pattern** | An established approach that is more readable, more testable, or less bug-prone than alternatives. Functional alternatives exist but this is the default unless there is a specific reason. | SHOULD use; document deviation if not. |
| **Performance heuristic** | An observation correlated with better performance in most workloads; the actual bottleneck must be measured, not assumed from the pattern alone. | INVESTIGATE when performance baseline shows the bottleneck is in this area. |
| **Maintainability recommendation** | Improves readability, debugging, modularity, or onboarding cost. Not a correctness or performance driver. | SHOULD use; weight against local-team conventions. |
| **Context-dependent recommendation** | The right choice depends on model shape, business semantics, or engine version; no universal default. | EVALUATE against the specific case; do not apply mechanically. |

Throughout this document, guidance is implicitly **preferred pattern** or **maintainability recommendation** unless explicitly labeled otherwise. Labels are called out inline where the distinction matters.

## When Used
DAX is the **calculation language for Microsoft tabular engines**:
- **Power BI semantic models** — measures, calculated columns, calculated tables, calculation groups
- **Azure Analysis Services (AAS) / SQL Server Analysis Services (SSAS) Tabular**
- **Excel Power Pivot**
- **Fabric semantic models / Power BI datasets**

Specifically for:
- **Measures**: dynamic aggregations computed at query time based on report filter context (time intelligence, ratios, KPI targets)
- **Calculated columns**: pre-computed row-level logic persisted in Vertipaq (simple categorization, flags, denormalised attributes)
- **Calculation groups**: reusable templates to reduce measure explosion (e.g., Time Intelligence calc group with "YTD", "PY", "YoY%" as items)
- **Row-level security (RLS) roles**: filter predicates on tables per security role
- **Dynamic segmentation**: top-N / what-if / dynamic ranking that respond to slicers

## When NOT Used
- **Large ETL / transformation logic** — DAX is for analytical calculations on *already-modeled* data; use SQL/dbt/Python in the warehouse layer
- **Text mining, regex-heavy parsing** — DAX has limited string functions; push to ETL
- **Fetching source data** — DAX does not read external data sources; Power Query (M) or warehouse ETL does
- **Machine learning / statistical inference** — use Python (PBI Python visuals / Fabric Data Science), R, or warehouse ML; DAX has no built-in statistical distributions beyond basic averages
- **Single-row business rules on write** — those belong in application logic or SQL constraints; DAX measures are read-only & recomputed at query-time
- **Joins / schema modeling** — relationships are modeled in the tabular model (M/TMDL/Power BI Desktop), not in DAX. DAX *traverses* them.

---

## Common Mistakes

1. **Confusing row context vs filter context** — Calculated columns compute row-by-row; measures compute under the report filter context. Using `SUM('Sales'[Amount])` inside a calculated column yields the same value on every row (filter context is empty unless CALCULATE transitions it).
2. **`CALCULATE(<measure>, FILTER(ALL(...), ...))` when `ALLSELECTED`/`KEEPFILTERS` is intended** — FILTER(ALL) overwrites user filters entirely; users lose slicer selections silently.
3. **`SUMX(Table, [Measure])` without understanding context transition** — iterators call measures per row, which triggers a context transition from the iterator row context into filter context. This is powerful but expensive on large tables; test cardinality.
4. **Missing `ALLSELECTED()` for visual totals** — percent of grand total with `DIVIDE(SUM(Sales[Amt]), CALCULATE(SUM(Sales[Amt]), ALL(Sales)))` ignores slicers; use `ALLSELECTED` to respect visual filters.
5. **Semi-additive measures with plain `SUM` + date at day grain** — "Account Balance" summed across months double-counts; must use `LASTDATE` / `LASTNONBLANKVALUE`.
6. **`IF(CALCULATE(COUNTROWS(...)) > 0, [MeasureA], [MeasureB])`** — Evaluates COUNTROWS *and* both measures every time (EAGER evaluation plan); anti-pattern. Use `IF(ISBLANK([Base]), …)` or variables + `HASONEVALUE`.
7. **`EARLIER` / `EARLIEST` without variables** — Variables are almost always preferred over EARLIER for readability. EARLIER remains valid DAX. EARLIER/EARLIEST access an outer row context; variables achieve the same and are clearer. Use `VAR CurrentRowCol = Table[Col]` before the inner iterator and reference the variable.
8. **Using `RELATEDTABLE` in a calculated column on the 1-side of a 1:many** — Expensive, materializes a table only to aggregate; better to push to measure with CALCULATE or pre-aggregate in SQL.
9. **Ignoring blank handling in division** — `X / Y` returns NaN/Infinity in DAX when `Y = 0` or blank; always use `DIVIDE(numerator, denominator, <alternate>)`.
10. **Bi-directional relationships + ambiguous paths** — creates subtle filter-direction bugs with diamond schemas; prefer single-direction and explicit bidirectional only when required + tested.
11. **`ALL(Table)` vs `ALL(Table[Column])` vs `REMOVEFILTERS`** —
    - `ALL(Table)` removes filters on *every* column and also returns the full table as a table expression (usable as iterator input).
    - `ALL(Table[Column])` removes filters only on that single column and returns the distinct column values as a table.
    - `REMOVEFILTERS(Table)` or `REMOVEFILTERS(Table[Column])` removes filters *only* — it does not return a table input to iterators. **Context-dependent recommendation:** `REMOVEFILTERS` is preferred over `ALL()` when the intention is *only* to clear filters (not to provide a table to an iterator), because the intent is explicit and it avoids accidentally materializing rows. `REMOVEFILTERS` is available in modern Analysis Services (2019+), Power BI, and Microsoft Fabric; for older engines use `ALL()` in the same position.
12. **Hardcoding date literals as strings** — `"01/01/2024"` parses as MDY on some servers and DMY on others; use `DATE(2024,1,1)`.

---

## Trade-offs

| Decision | Advantages | Disadvantages |
|----------|-----------|---------------|
| **Measure vs Calculated Column** | Measure: computed on-demand, no storage, dynamic with filters. Column: pre-materialised, fast queries, consistent values. | Measure: CPU cost at query time. Column: consumes Vertipaq RAM/disk, static at refresh time, increases model size. |
| **Single large measure vs split + referenced measures** | Split: modular, testable, DRY. | Single: avoids nested CALCULATE overhead in hot paths. Use variables in the final measure to compose performance-sensitively. |
| **`FILTER(table, pred)` vs `table[col] = val` in CALCULATE** | Table-level filter: flexible, uses existing filter context. Column-boolean: 10–100× faster (column store scan + bitmap), preferred when possible. | Table-filter: must materialise rows. Column-boolean: only equality/in on single column. |
| **CALCULATETABLE vs FILTER** | CALCULATETABLE modifies filter context then evaluates a table; composes with existing context. | FILTER is a plain iterator with no context transition; prefer when you *don't* want transition. |
| **SUMMARIZE vs SUMMARIZECOLUMNS vs ADDCOLUMNS + SUMMARIZE** | SUMMARIZECOLUMNS: fastest, most memory-efficient for grouped queries, auto-exists aware, supports ROLLUPADDISSUBTOTAL. SUMMARIZE: legacy, has measure filter context bugs; never add measures within SUMMARIZE. ADDCOLUMNS(SUMMARIZE(...), "Meas", [Measure]): safest, portable, but slower than SUMMARIZECOLUMNS. | SUMMARIZECOLUMNS: not allowed in row context (e.g., iterators), not supported in DAX Studio EVALUATE in some contexts. |
| **Variables vs repeated expressions** | Variables: evaluate ONCE, readable, debuggable, avoid double evaluation. | Zero real downside. **Always use variables for reused sub-expressions.** |
| **Bidirectional vs single-direction relationships** | Bidirectional: auto-filter dims from facts, useful for M2M via bridge. | Bidirectional: introduces ambiguity, performance cost, subtle over-filter bugs; requires rigorous testing. |
| **Import vs DirectQuery (engine level)** | Import: Vertipaq, blazing-fast DAX, 99% of DAX function surface. | DirectQuery: DAX translated to SQL; many functions (TOPN, complex iterators) are unsupported or perform poorly. |

---

## Core Concepts: Filter Context, Row Context, Context Transition

### Filter Context (Measures Live Here)
The **set of active filters** from slicers, rows/columns of a visual, cross-highlight, roles, and CALCULATE modifiers. Two measures with identical formulae return different results because they run under different filter contexts.

```
Report state: Slicer Year = 2024, Matrix rows = Country, Columns = Month
→ Filter context on [Revenue] at (France, January 2024) cell is:
   Date[Year]=2024, Date[Month]=January, Customer[Country]=France
```

### Row Context (Calculated Columns & Iterators Live Here)
The **"current row" pointer** inside a table scan. Exists in:
- Calculated columns (`= 'Sales'[Qty] * 'Sales'[UnitPrice]` — per-row)
- Iterators (`SUMX`, `FILTER`, `ADDCOLUMNS`, `GENERATE`, etc.)

Row context does **NOT** automatically traverse relationships. Use `RELATED()` (many→1 side) or `RELATEDTABLE()` (1→many side) to reach related columns.

### Context Transition (CALCULATE bridges both)
`CALCULATE(expr, <filter1>, <filter2>, …)` does two things:
1. Takes any existing **row context** and converts it into an equivalent **filter context** on all columns of the current-row table(s).
2. Applies the explicit filter modifiers on top (overwriting, adding, or removing filters).

**Why it matters:** This is how a measure (which needs filter context) can be called inside an iterator or calculated column (which start with only row context).

```dax
-- Context transition in SUMX: per row, "current row" becomes filter context for [UnitRevenue] measure
Revenue SUMX =
SUMX(
    VALUES('Date'[Date]),
    [UnitRevenue]  -- context transition from VALUES(Date) row → filter context
)
```

---

## Good Implementation

### Variables First (Always)

```dax
Revenue YoY % =
VAR CurrentPeriod  = [Revenue]
VAR PriorPeriod    = CALCULATE([Revenue], SAMEPERIODLASTYEAR('Date'[Date]))
VAR Denominator    = COALESCE(PriorPeriod, 0)
VAR GrowthAbs      = CurrentPeriod - PriorPeriod
RETURN
    IF(
        NOT ISBLANK(CurrentPeriod) && NOT ISBLANK(PriorPeriod),
        DIVIDE(GrowthAbs, ABS(Denominator), BLANK()),
        BLANK()
    )
```

### CALCULATE with Column Filters (Fast)

```dax
Revenue US =
CALCULATE(
    [Revenue],
    Customer[Country] = "US"        -- Column predicate → bitmap scan; PREFERRED
)

Revenue US CA =
CALCULATE(
    [Revenue],
    Customer[Country] IN {"US", "CA"},
    KEEPFILTERS(Sales[Channel] = "Retail")  -- KEEPFILTERS: AND with existing filter, not overwrite
)

-- Slower equivalent (AVOID unless needed):
-- CALCULATE([Revenue], FILTER(ALL(Customer[Country]), Customer[Country] = "US"))
```

### Time Intelligence (Mark as Date Table → Reliable)

```dax
-- First: mark 'Date' as a date table (in Power BI: Mark as Date Table)
Revenue YTD =
CALCULATE(
    [Revenue],
    DATESYTD('Date'[Date])
)

Revenue MTD =
TOTALMTD([Revenue], 'Date'[Date])

Revenue Trailing 12 Months =
CALCULATE(
    [Revenue],
    DATESINPERIOD('Date'[Date], LASTDATE('Date'[Date]), -1, YEAR)
)

Revenue Same Period Last Year Complete (not partial) =
VAR LastFullDate  = CALCULATE(MAX('Sales'[OrderDate]), REMOVEFILTERS())  -- last day in fact, not max in slicer
VAR MaxDateVisual = MAX('Date'[Date])
VAR StopAt        = MIN(MaxDateVisual, LastFullDate)
VAR RangeThisYear = DATESBETWEEN('Date'[Date'], MIN('Date'[Date]), StopAt)
VAR RangeLastYear = SAMEPERIODLASTYEAR(RangeThisYear)
RETURN CALCULATE([Revenue], RangeLastYear, ALLSELECTED('Date'[Month Name]))  -- preserve month sort etc.
```

### Iterators & Semi-Additive Measures

```dax
-- Semi-additive: latest balance per account, then sum across accounts
-- (Do NOT SUM balances across dates!)
Balance Last Non-Blank =
VAR LastVisibleDate =
    CALCULATE(
        LASTNONBLANK('Date'[Date], [Balance Raw]),
        ALLSELECTED('Date')
    )
RETURN
    CALCULATE(
        SUMX(
            VALUES(Account[AccountKey]),
            CALCULATE(
                LASTNONBLANKVALUE('Date'[Date], SUM(Balance[Amt])),
                'Date'[Date] <= LastVisibleDate
            )
        ),
        KEEPFILTERS('Date'[Date])
    )
```

### SUMMARIZECOLUMNS for Grouped Queries (Fastest)

```dax
-- Used in DAX Studio / EVALUATE queries and Power BI
EVALUATE
SUMMARIZECOLUMNS(
    'Date'[Calendar Year],
    Customer[Segment],
    TREATAS({"US","CA","MX"}, Customer[Country]),    -- filter without adding to group-by
    "Revenue", [Revenue],
    "Orders",  [Order Count],
    "AOV",     [Average Order Value]
)
ORDER BY 'Date'[Calendar Year], [Revenue] DESC
```

### Calculation Groups (Eliminate Measure Explosion)

```
Calculation Group: Time Intelligence
  Precedence: 20
  Format String Expression: SELECTEDVALUE('Time Intelligence'[Format String], "General Number")
  Items (each is a CALCULATE modifier applied to the *selected measure*):
    - Current:   CALCULATE(SELECTEDMEASURE())
    - YTD:       CALCULATE(SELECTEDMEASURE(), DATESYTD('Date'[Date]))
    - PY:        CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Date'[Date]))
    - YoY %:     VAR _c = SELECTEDMEASURE()
                 VAR _p = CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Date'[Date]))
                 RETURN DIVIDE(_c - _p, ABS(_p), BLANK())
    — Format String Item for YoY%: "0.00 %;-0.00 %;- "

→ In the report, add one slicer on 'Time Intelligence'[Name], any base measure works.
```

### Dynamic Top-N with Others

```dax
Top 10 Customers =
VAR TopN = 10
VAR AllCustomers = ALLSELECTED(Customer[Customer Name])
VAR Ranked =
    ADDCOLUMNS(
        AllCustomers,
        "@Rev", [Revenue]
    )
VAR TopCustomers =
    TOPN(TopN, FILTER(Ranked, NOT ISBLANK([@Rev])), [@Rev])
VAR InTopN =
    INTERSECT(VALUES(Customer[Customer Name]), SELECTCOLUMNS(TopCustomers, "Name", [Customer Name]))
RETURN
    IF(
        ISINSCOPE(Customer[Customer Name]),
        IF(NOT ISEMPTY(InTopN), [Revenue], BLANK()),
        [Revenue]  -- total remains real total, not top 10
    )
```

---

## Storage Engine (SE) vs Formula Engine (FE) & Vertipaq

- **Storage Engine (Vertipaq)**: Columnar, in-memory, highly compressed data. Requests come as SCANs with simple filters/aggregations; returns data tables to FE. All data reads pass here.
  - **Superpowers**: ~100M cells/sec/core, bitmap filters, auto-exists on columns from the same table, bulk aggregation scans
  - **Limitations**: No measures, no CALCULATE, no iterators; only column-level grouping, simple filters, basic COUNT/SUM/MIN/MAX
- **Formula Engine (DAX Interpreter)**: Executes DAX plan, calls SE for data, handles CALCULATE, iterators, measure recursion, context transition, variables.
  - **Superpowers**: anything DAX can express
  - **Bottleneck**: single-threaded callback for each row when iterators call measures. 1M × measure-call = slow.

### Cardinality & Vertipaq Compression
- **High-cardinality columns** (GUID, timestamp, UUID, free-text): poor compression, cost more RAM, slow distinct counts. If not needed, exclude or hash-down.
- **Dictionary encoding** (default): value → integer ID (0–65535 or up to 2^31). Columns with few unique values compress to kilobytes even for 100M rows.
- **Value encoding**: for integer/date/float with narrow ranges; stores offsets.
- **Performance rule**: Minimize the # of distinct values in high-volume tables. Date tables have small cardinality → perfect. Fact PKs (billions unique) → never include unless strictly needed for DISTINCTCOUNT.

---

## DAX Studio: Debugging Workflow

1. **Clear cache between runs**: "Clear Cache" then "Run".
2. **Server Timings**: enable → measure SE vs FE CPU %, SE query count, and rows scanned per call. Establish baseline first; then identify the bottleneck. Measure storage engine vs formula engine; the bottleneck drives optimization, not an arbitrary count. A high FE share relative to your workload baseline typically indicates iterator callbacks (measure-per-row) or complex FILTER materialization; a high SE share indicates scan/aggregation bottlenecks.
3. **Query Plan** — Physical Plan shows:
   - `SpoolOperator_*`: materialised intermediate. Compare spool size against the model's working memory baseline; any spool that is large relative to expected intermediate cardinality is worth investigating.
   - `Iteration=Dense` / `Lookup`: dense iterate is efficient for in-memory column data; Lookup combined with dense iterate on high-cardinality tables correlates with high cost.
   - `Aggregation(...)` + `Scan_Vertipaq`: SE-heavy, usually efficient unless scan range is much wider than the filter context implies.
4. **Benchmark**: Capture baseline duration; then break the measure into pieces and identify which component contributes 80% of the cost (Pareto). Change one factor at a time and re-measure.
5. **`EVALUATE ROW("x", [Measure])`** against a representative filter context to isolate one measure.

### Example Anti-Pattern → Fix

```dax
-- ❌ ANTI-PATTERN: IF with COUNTROWS inside CALCULATE
Sales KPI Legacy =
IF(
    CALCULATE(COUNTROWS(Sales)) > 0,     -- evaluates COUNTROWS + both branches every time
    SUM(Sales[Amount]) / 1.2,
    BLANK()
)

-- ✅ FIX: use ISBLANK on base measure (fast), variables to compute once
Sales KPI =
VAR Base = [Revenue]
RETURN IF(NOT ISBLANK(Base), Base / 1.2, BLANK())
```

---

## How to Test DAX

1. **Golden-output tests with known seeds** — Load a small parquet/csv model with 50 rows; run measure via DAX Studio or Tabular Editor's `TOM` + script; assert exact numeric results.
2. **DAX Studio `EVALUATE` / `EVALUATEANDLOG`** — Write canonical queries for every core measure; store expected outputs in a regression suite.
3. **Cross-filter context matrix** — For a measure, test 4 cells: (no filter, A, B, A+B) to ensure CALCULATE modifiers respect slicers and visual totals.
4. **Boundary conditions** — BLANK facts, single row, first/last day of fiscal year, leap year DST transitions, multi-role date dims (DeliveryDate vs OrderDate).
5. **Numeric equivalence** — Floating-point rounding: `ABS(actual - expected) < 1e-6`.
6. **Tabular Editor Scripting / BISM Normalizer / ALM Toolkit** — Schema diff between DEV and PROD datasets to catch accidental column removals.
7. **Calculation group regression**: For each base measure × each calc group item, assert same result as the equivalent hand-written measure.

---

## Performance Behavior (Hot Spots to Watch)

| Pattern | SE/FE | Cost Driver | Mitigation |
|---------|-------|-------------|------------|
| `SUMX(5M-row-table, [Measure])` | FE heavy | 5M context transitions → 5M mini-measure evals | Pre-aggregate base columns first; move math into storage; use Calculation Groups; reduce iterator table size via ADDCOLUMNS(SUMMARIZECOLUMNS(…), …) |
| `CALCULATE(…, FILTER(ALL(big_table), …))` | FE + SE | Materialises full scan of big_table per call | Replace with column predicate `table[col] IN (...)`; narrow table to one column: `FILTER(ALL(table[col]), cond)` |
| `DISTINCTCOUNT(high-cardinality-col)` | SE | Large bitmap intersection; memory pressure on 100M+ distinct | Consider HyperLogLog approximation if exact precision not needed (Snowflake side); avoid DISTINCTCOUNT on GUID PKs if not required |
| Many bi-directional rels on large snowflake | SE plan bloat | Expanded filter via snowflake (many bitmap joins per cell) | Star-schema, single-direction; use USERELATIONSHIP explicitly for role-playing dims |
| `SAMEPERIODLASTYEAR` on non-contiguous date range | FE | Recomputes date ranges per-query cell; still fine for most cases | Pre-compute fiscal hierarchies; mark Date as Date Table for optimizer shortcuts |
| Nested measures with nested CALCULATE | FE recursion | Variable reuse fails if variables live inside callee | Hoist variables to top; do not nest CALCULATE when a single compound filter does the job |
| Calculated column using entire RELATEDTABLE aggregation | Refresh cost + RAM | Recomputed on each refresh, materialised in Vertipaq | Move to measure, or pre-aggregate in warehouse SQL |

---

## What to Inspect First (Wrong Numbers / Slow Queries)

1. **Is Date table marked & continuous?** Time intelligence silently returns wrong results otherwise. **Hard correctness rule.**
2. **Cardinality & direction of the relationship path:** Does a bidirectional or many-to-many silently filter a dimension where it shouldn't?
3. **ALL vs ALLSELECTED vs KEEPFILTERS vs REMOVEFILTERS:** If totals are wrong vs slicers, check whether the filter is using `ALL` where it should use `ALLSELECTED` to respect visual filters. When intent is only to clear filters (not provide a table to iterate), prefer `REMOVEFILTERS` over `ALL` for clarity on modern engines.
4. **BLANK propagation:** `COALESCE` vs `BLANK()`. Blank numerator or denominator returning unexpected non-BLANK? Use DIVIDE + `IF(NOT ISBLANK(base), …, BLANK())`.
5. **Context transition in iterator:** `SUMX(VALUES(...), [Measure])` — examine the cardinality of VALUES(); compare the actual cardinality against the baseline and decide if a better aggregation is possible. `CALCULATE` wrapping an aggregator inside an iterator or calculated column performs context transition (row context → filter context); this is valid and sometimes required. In simple standalone cases where no context transition is needed and no filter modifier is present, `CALCULATE(SUM(...))` is a POTENTIAL simplification — verify before removing; it is NOT universally incorrect.
6. **DAX Studio Server Timings:** Establish baseline and bottleneck. Measure storage engine vs formula engine; the bottleneck drives optimization, not an arbitrary count or percentage. If FE share is much higher than SE share for a given workload baseline, look for row-by-row measure callbacks. If SE query count is much higher than expected for a simple measure vs. similar patterns like "CALCULATE per dimension member" may be the driver.
7. **Physical plan Spool size:** Compare spool sizes against the expected intermediate cardinality and the model's working memory baseline; investigate any spool that is disproportionately large relative to the output. Break large spools into smaller calculations.
8. **Filter direction on roles / RLS:** Are RLS predicates applied to a dimension that bi-directionally filters a huge fact? Restructure to filter fact directly.
9. **Auto-exist subtleties:** Two slicers on the same table (Customer[Country], Customer[Segment]) auto-intersect; across tables they cross join. If totals differ, this is likely.
10. **Precision loss on currency:** `SUM` of decimals accumulated across float arithmetic → use DECIMAL type in model; avoid rounding at intermediate steps.

---
