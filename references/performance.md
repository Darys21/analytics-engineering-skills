# Reference: Performance

## When to use
- User reports slowness, missed SLA, or cost concerns.
- Before launching a pipeline, semantic model, query, or dashboard to production.
- After a material refactor to confirm no regression.

## When NOT to use
- On "feels slow" without a baseline. Always measure first.
- On correct-but-not-optimized logic before correctness is proven.
- Blindly "rewrite cleaner" without measurement; cleaner code ≠ faster code under every optimizer.

## Core methodology
1. **MEASURE.** Baseline with a representative workload. Record environment, data size, warm vs cold.
2. **IDENTIFY bottleneck.** Find the operation taking 80% of time/cost.
3. **FORM hypothesis.** "If I change X, I expect Y% improvement because Z."
4. **OPTIMIZE one meaningful factor.** Change only one thing at a time.
5. **BENCHMARK.** Same environment, same inputs, multiple runs, median + variance.
6. **VALIDATE correctness.** Numerical equivalence against baseline (see `testing.md`).
7. **DOCUMENT.** Baseline, change, new measurement, validation result, trade-offs.

If measurement shows no gain, revert. Never ship a "more elegant" rewrite that is slower or unverified.

## Common mistakes
- Measuring only end-to-end instead of per-step → misattribution.
- One measurement, no repeats → noise.
- Comparing cold cache baseline to warm cache new version → meaningless 10x "win."
- Changing 5 variables in one iteration → can't tell what worked.
- Optimizing a 5 ms step while a 30 s step exists.
- Accepting numeric drift after an optimization without a tolerance decision.

## What to inspect first (per-technology)

### SQL
- Actual execution plan (not estimated).
- Top operations by time/IO: table scans, key lookups, sorts, hash joins, spool.
- Estimated vs. actual rows (big skew = stats issue).
- Missing indexes on join/filter columns? Over-indexed on hot write tables?
- SARGability: functions on columns in `WHERE`/`JOIN` prevent index use.
- Parameter sniffing (plan cache issues) for stored procedures.

### Python / pandas
- `cProfile` hot path. `line_profiler` per-line inside hot function.
- `pandas.DataFrame.memory_usage(deep=True)` → object strings expensive; categoricals save memory.
- Iterating rows (`apply`, `iterrows`) instead of vectorization.
- Chained assignments triggering `SettingWithCopyWarning` and copies.
- Unnecessary copies (`df.copy()`, intermediate DataFrames inside loops).
- I/O: CSV vs. Parquet (columnar formats 10–100× faster for analytical reads).

### DAX / Power BI
- DAX Studio Server Timings: total, SE CPU, FE CPU, number of xmSQL queries.
- Vertipaq Analyzer: column cardinality, dictionary size, relationship size.
- xmSQL queries produced: many small SE queries often worse than one large one.
- `FILTER(Table, ...)` inside iterators over large tables — prefer `CALCULATE(..., filter_column IN ...)` or relationship-based filtering.
- Context transition inside `SUMX`/iterator over large fact — materializing full tables inside virtual context → heavy.
- Too many single-value measures on a page → many queries. Consider a calculation group for time intel.

### Pipelines (dbt, Spark, SQL scripts, orchestrators)
- Step-level duration graph. Long poles and stragglers.
- I/O: bytes read/written per step. Is data being re-scanned repeatedly?
- Skew: one partition / key value 100× larger than others (Spark/databricks).
- Full recompute instead of incremental (check watermarks).
- Fan-out on dbt models causing re-materialization of shared CTEs. Consider intermediate models.

### Power BI reports
- Performance Analyzer: visual-level breakdown (DAX query vs. visual render vs. other).
- Too many visuals on a page (N+1 queries).
- Slicers without bidirectional optimization; each slicer change re-renders 40 visuals.
- Large tables with hundreds of rows loaded client-side → paginate or summarize.

## Good implementation patterns

### SQL
- Covering indexes for frequent access patterns (include SELECT columns).
- Predicate pushdown, SARGable filters.
- Partitioning by date on very large tables (scan elimination).
- Materialized views / indexed views for expensive, frequent aggregations.
- Statistics up to date; rebuild if estimates drift.
- Replace correlated subqueries with joins / window functions.
- CTEs for readability; if optimizer struggles, intermediate temp tables with stats.

### Python / pandas
- Use `pd.read_parquet`, categorical dtypes, numeric downcasting.
- Vectorize: `np.where`, `.assign`, `groupby().transform` instead of loops.
- `numba` or `polars` for hot loops only after profiler identifies them.
- Stream / chunk large files instead of loading into RAM.
- `logging` + timestamps around big I/O and transformations.

### DAX
- Always define a proper star schema and relationships. Let the storage engine do the work.
- Base measures. Avoid implicit columns in values of visuals.
- Calculation groups for time intelligence families (YTD, PY, YOY, etc.).
- Variables to cache common sub-expressions.
- `REMOVEFILTERS()` / `ALLEXCEPT()` instead of broader `ALL(Table)`.
- Use `TREATAS` for filter transfer instead of physical temp tables when possible.

### Pipelines
- Incremental when data volume > threshold. Always idempotent.
- Staging + atomic swap for tables; never append-and-hope.
- Airflow sensors / Dagster assets / dbt `select` for targeted reruns, not full re-runs.
- Persist intermediate expensive joins as tables to avoid recomputation.

### Power BI Import
- Vertipaq: remove unused columns. Prefer numeric keys over strings. Group high-cardinality strings.
- Incremental refresh + detect-data-changes when reliable modified-at.
- Aggregations over DirectQuery if composite.

## How to validate performance tests
- Same environment, same input size, same cache state each time.
- Minimum 5 runs; report median and variance. Exclude first run if intentionally testing warm-cache steady state (and state that explicitly).
- Compare bottleneck metric (e.g., top query) AND end-to-end.
- Numerical equivalence on representative slices after optimization.

## Performance behavior heuristics
- I/O almost always dominates compute in analytical workloads. Reduce bytes read first.
- Cardinality drives group-by and join cost.
- Random lookups (key lookups, nested loops on big inputs) are the usual suspect.
- Skew kills distributed systems (Spark, DQ) and DAX (bad relationship high-cardinality columns).

## Pitfalls
- Microbenchmarks in dev that don't reflect prod data distribution.
- "Optimizations" that help one query by 10× but slow the overall workload by 2× because you broke a shared index.
- Blind index creation; every index slows writes and costs storage.
- Over-aggressive denormalization for speed → data quality bugs.

---
*See also:* `workflows/optimize.md`, `workflows/diagnose.md`, `references/testing.md`, and the per-technology references (`sql.md`, `python.md`, `dax.md`, `power-bi.md`, `analytics-engineering.md`).
