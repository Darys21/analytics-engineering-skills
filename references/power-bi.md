# Reference: Power BI

## When to use
- Building Power BI semantic models (Import, DirectQuery, or Composite) for enterprise or departmental BI.
- Designing reports and dashboards in Power BI with maintainable DAX and strong data-model foundations.
- Using Power BI Desktop / Service / Embedded / Deployment Pipelines / PBIP + TMDL source control.

## When NOT to use
- Quick one-off analysis where a Python notebook or SQL query is sufficient.
- Situations where Power BI is not licensed, not approved, or cannot meet latency/freshness requirements via DirectQuery / Composite / XMLA.
- Cases where a semantic model already exists and the task only needs reports; use existing model, don't create a second one.

## Common mistakes
- Importing raw transactional tables directly without conforming a star schema.
- Mixing grains in a single fact table (e.g., header + line fact).
- Bidirectional relationships enabled by default → ambiguity, incorrect totals, bad perf.
- Giant Import models with unused columns; high cardinality string columns not optimized.
- Thousands of unorganized measures; no display folders, no descriptions.
- Hidden/implicit measures used in visuals instead of explicit base measures → brittle.
- DirectQuery on top of heavy views without query folding to source or aggregations.
- "Let me add one more column" feature creep → huge PBIX, slow refresh.

## Trade-offs
| Choice | Upside | Downside |
|--------|--------|----------|
| Import mode | Blazing fast queries, full DAX/Vertipaq | Refresh latency; memory footprint; long refresh on huge data |
| DirectQuery | Near-real-time, no data copy | Query limits; some DAX unsupported; source perf dependency |
| Composite mode | Best of both for warm vs hot data | Complex design; potential ambiguity |
| Single dataset / app workspace + apps | Central semantic, one metric truth | Requires good ownership + deployment |
| Many copied PBIXs | Fast individual work | Metric divergence, governance mess |
| PBIP + TMDL in git | Versioned, reviewable, deployable | Tooling + discipline required |

## What to inspect first
1. Mode: Import / DirectQuery / Composite.
2. Data view or Vertipaq Analyzer: which columns / relationships are largest?
3. Model view: star schema? Cardinality? Filter directions? Any many-to-many that shouldn't be?
4. Measure count, organization (display folders), base vs. derived measures.
5. Incremental refresh policies and effective ranges.
6. Performance Analyzer trace on key pages (KPI strip, most-used drill).

## Good implementation
### Star schema and relationships
- One semantic model → one star (or set of conformed stars). Denormalized dimensions; fact tables at clear grain.
- Enforce single-direction 1-to-many unless a bidirectional has a documented reason (use ADR).
- Role-playing dimensions (e.g., Order Date, Ship Date, Due Date) use a shared conformed date dimension with inactive relationships and `USERELATIONSHIP` in measures. Never duplicate the date table three times with data.
- Date dimension as a proper marked date table; not relying on auto date/time. Turn off Auto Date/Time globally.

### Measures
- **Base measures:** `SUM(Fact[Amount])` — one per additive column.
- **Derived measures:** time intelligence, ratios, comparisons — built from base measures.
- **Format strings** set for every numeric measure.
- **Display folders** group measures by area (Finance, Ops, Time Intel…).
- **Descriptions** on every measure (shown in tooltips if configured).
- Use variables to avoid recomputation and for readability. Avoid nested `IF(CALCULATE(...))` when a single `CALCULATE` with a filter expression works.
- Prefer `DIVIDE(numerator, denominator, 0)` over `/`.
- Prefer `SELECTEDVALUE(Dim[Col], <default>)` over `IF(HASONEVALUE(Dim[Col]), VALUES(Dim[Col]))`.
- Avoid `ALL(Table)` when you mean `ALLEXCEPT(Table, Dim)` or `REMOVEFILTERS()`.

### Performance in Import mode
- Remove unnecessary columns. Vertipaq compresses by column; unused columns still cost memory.
- Low cardinality columns → excellent. High cardinality strings (GUID, free text) → expensive. Consider Summary columns / category grouping or Hash IDs when appropriate (and document).
- Incremental refresh with Detect Data Changes when source has a reliable `updated_at`.
- Aggregations (Import) above large DirectQuery fact tables if composite.
- Keep DAX measures storage-engine-friendly: avoid large materialized virtual tables, push filters to storage engine. Use DAX Studio: xmSQL queries, number of SE queries, SE CPU vs Formula Engine.

### DirectQuery / Composite
- Favor query-foldable sources and avoid Power Query transformations that break folding.
- Define aggregations at the common grains.
- Push complex joins / filters back to the source (views) where possible.
- Assume-at-most-once semantics if needed; handle duplicates in source layer.

### Governance & deployment
- **PBIP + TMDL** in source control (never commit .pbix binaries as the canonical source). Use TMDL files via the Power BI Desktop project format.
- **Deployment pipelines** (Dev → Test → Prod) with rules for connections, gateways, parameters.
- **Dataset owners,** refresh cadence, SLO, data source owners documented in `CONTEXT.md` or the dataset's internal descriptions.
- **RLS (Row-level security)** with roles tested; never rely solely on workspace permissions.

### Report design
- Follow the `dashboard-ux` workflow hierarchy.
- One semantic model → many reports. Don't duplicate models for reports.
- Performance Analyzer targets: initial page < 5 s; interaction < 3 s. Investigate > 10 s.
- Drill-through pages with standardized fields.
- Report page tooltip design (don't leave default tooltips for key visuals).

## How to test
- Reconcile KPIs to source SQL at 3–5 slices (typical, edge, empty) for each base measure and each high-impact derived measure.
- Time intelligence: check partial periods, leap years, fiscal vs. calendar boundaries, DST shifts if relevant.
- RLS: as each role, confirm rows returned match expected. Try privileged account and unprivileged account.
- Incremental refresh: run refresh once, run again with a later watermark; confirm merge/no-duplicate semantics.
- Deployment pipelines: deploy to test, verify parameter/connection swap, smoke test key reports.
- Performance: capture Performance Analyzer baseline, then optimize, re-capture, confirm improvement (see `performance.md`).

## Performance behavior
- Import mode typically dominates by orders of magnitude for repeated queries. Cost = refresh + memory.
- DirectQuery scales with source; every visual interaction → potential round-trips. Sensitive to N+1 visual count.
- DAX: large virtual tables (e.g., `FILTER(EntireFact, ...)` inside iterators) are expensive; replace with filter arguments to CALCULATE, or use `TREATAS`/relationship-based filtering.
- Cardinality of columns in group-by columns (both natural and via relationships) drives SE query time. Keep low cardinality where possible.

---
*See also:* `references/dax.md`, `references/tmdl.md`, `references/data-modeling.md`, `references/performance.md`, `workflows/dashboard-ux.md`, `workflows/tmdl-analysis.md`, `workflows/dax-analysis.md`.
