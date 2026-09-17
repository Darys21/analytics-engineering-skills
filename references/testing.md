# Reference: Testing

## When to use
- Any non-trivial transformation, analytical pipeline, model, or BI semantic logic.
- Before release of a new feature or fix.
- When "it worked on my machine" is not enough.

## When NOT to use
- Purely exploratory, throwaway analysis that will never be re-run or relied upon. Even then, ad-hoc sanity checks still apply.

## Common mistakes
- Only happy-path tests; edge cases (empty, single-row, null inputs, min/max date) uncovered.
- Reconciliation tests only compare total sums, never by dimensions — a cross-canceled bug passes.
- Data tests with `dbt test` (or equivalent) but no schema tests or uniqueness checks on grain.
- Testing dev data only and never against a realistic production-scale sample.
- Numerical equivalence checked to too many decimal places on float aggregations → flaky tests.
- "Manual tests" not documented → next person cannot reproduce them.
- Snapshot tests of full tables with natural volatility (timestamps, UUIDs) → spurious diffs.

## Trade-offs
| Approach | When | Cost |
|----------|------|------|
| Unit tests (logic functions / DAX baseline assertions) | Complex reusable logic. | High value, low maintenance. |
| Schema tests (not-null, unique, accepted values, ref integrity) | Every table and column in a marts/semantic layer. | Cheap, catches 80% of preventable issues. |
| Data tests (business rules, row-level assertions) | Every business-critical rule. | Medium effort; high ROI. |
| Reconciliation tests (source vs. mart, v1 vs. v2 of a pipeline) | Refactors, migrations, backfills. | High effort; mandatory for migrations. |
| Property-based (numerical invariants across slices) | Aggregations with complex joins. | Medium effort; great for catching missed cases. |
| Snapshot tests (output hash or stored CSV) | Stable, non-volatile outputs. | Cheap; careful with timestamps/volatile columns. |
| Integration tests (end-to-end pipeline with sample data) | New pipelines or major refactors. | Expensive; keep one green end-to-end case. |
| Performance regression tests | High-impact workloads. | Medium; requires baseline storage. |

## What to inspect first
- **What is the highest-risk piece of logic?** Test that first.
- **What are the grain-defining columns?** These are your uniqueness and referential integrity test targets.
- **What joins / window functions / DAX context transitions are present?** Every one is a test candidate.

## Good implementation

### 1. Schema tests
For every table/column that defines a grain:
- Primary key columns: `not null` + `unique`.
- Foreign keys: `exists_in` the referenced dimension.
- Accepted values on enums / status columns.
- Numeric ranges (e.g., `discount between 0 and 1`, `quantity >= 0`).
- Date logic: `order_date <= ship_date`, `order_date within calendar` etc.

### 2. Data / business-rule tests
- Aggregation totals match independent roll-up (e.g., daily sums match monthly totals within tolerance).
- Trend / YOY / MOM sanity (a known-period tie-out).
- Ratio bounds (e.g., "return rate not > 100% unless data has reversals — if reversals, document the case and test it explicitly").
- Slices: a test per critical segment (region, brand, etc.).

### 3. Reconciliation tests (the gold standard for refactors)
- Build two pipelines: OLD and NEW.
- Compare at several levels:
  - Total rows, total sum / count distinct per metric.
  - Group by each high-cardinality dimension independently.
  - Sample per-cell level comparison (random 1000 cells of the grouped cube).
- Tolerance: exact integer equality for counts; e.g., `1e-9` relative tolerance for floats; define the tolerance in the test, not by feel.
- If differences exist, attribute them (known rounding due to order of operations? legitimate bug? upstream fix?). Record every difference.

### 4. Numerical equivalence
- When you replace a SQL/DAX/Python transformation with a rewritten version: compare outputs, not just intent.
- `sum(abs(a - b)) / sum(abs(b)) < tol` catches drift.
- Compare in both directions; compute per-slice residuals.
- Document: why a tolerance exists and where rounding happens.

### 5. Edge-case test menu (always ask these)
- Empty input dataset.
- Single row dataset.
- All measure columns = 0 or NULL.
- Minimum date in dataset, maximum date, missing date gap.
- Duplicate input rows.
- Foreign key to a dimension missing (unknown member handling).
- Time logic: leap year, fiscal year boundaries, month with 5 vs 4 weeks, DST boundary, partial periods.

### 6. Testing DAX / semantic models
- Use DAX Studio / EVALUATE against a known sample dataset.
- For each base and high-impact derived measure, run a row-level check against source SQL.
- Verify totals and subtotals match granular sums (semi-additive logic explicit).
- Test RLS roles with `USERNAME()` overrides.

### 7. Testing pipelines (integration)
- Run with a small but representative seed dataset in CI.
- Verify row counts, primary keys, outputs match a committed snapshot.
- Run with synthetically injected edge cases (duplicates, late data, schema changes) via staging seeds.

## How to test the tests
- **Mutation testing** of logic (manual or tool-assisted): introduce a known bug; does at least one test fail? If not, tests are too weak.
- **Flakiness**: run the same test 20 times with no changes; it must pass 20/20.
- **Coverage heuristic**: every complex CTE/function/measure has at least one dedicated assertion or reconciliation path.

## Performance behavior
- Good tests catch bugs early → net time saved.
- Don't over-test trivial code. Pareto principle: tests on 20% of logic prevent 80% of incidents.
- Integration tests are slow; keep them few but green. Unit tests and schema tests fast; run on every commit.

## Pitfalls
- **Vanishing tests**: tests disabled because they fail. Treat failing tests as a production signal, not an annoyance.
- **Overly strict comparisons on float**: relative tolerance usually preferred; absolute tolerance only when magnitude is known.
- **No owner for test failures**: pipeline broken → nobody looks → tests ignored. Assign owners in CI alerts.
- **No tests during refactors**: rewrite, cross fingers, deploy → regrets. Reconciliation test before merge.

---
*See also:* `workflows/review.md`, `workflows/diagnose.md`, `workflows/optimize.md`, `references/performance.md`, `references/ci-cd.md`.
