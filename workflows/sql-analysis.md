# Workflow: SQL ANALYSIS — Readable, Performant, Correct Queries

## Purpose

Produce correct SQL that is readable by teammates, modular via CTEs and staged queries, join-safe (no silent fan-out or row-dropping), aggregation-accurate (no double-count), window-function precise, NULL-safe, date-dedupe-aware, performance-optimized for the target dialect, and portable across ANSI, T-SQL, PostgreSQL, Spark SQL, BigQuery, and Databricks SQL. SQL is the interface between analytics engineers and their data; bad SQL is the single most frequent cause of "the numbers don't match" tickets.

## When to use

- When writing any SQL query longer than 30 lines that will be reviewed by another human, version-controlled, or used as the basis of a dashboard/report/exposure.
- When building dbt/SQLMesh models, ad-hoc analyses, data-quality assertions, or reconciliation queries.
- When refactoring existing SQL that is known to be slow, wrong, or unreadable.
- When teaching, reviewing, or auditing SQL written by teammates.

## Inputs

- A precise analytical question or the KPI/diagnostic metric to compute, with its technical definition and grain.
- The DATA-MODEL star schema ERD and data dictionary for the target tables.
- Target platform documentation (dialect-specific SQL, indexing, distribution, partitioning, UDFs, cost-based optimizer behavior).
- Profiled data samples: row counts, NULL rates, column cardinality, join-key distributions from DATA-DISCOVERY.
- Access to an EXPLAIN / query plan viewer and a query-profile/execution-stats output (BigQuery job stats, Snowflake Query Profile, Databricks Spark UI, Synapse DMVs).

## Preconditions

- The analyst knows the grain of every table they will query; grain declarations exist in DATA-MODEL.
- Join keys have been profiled: cardinality, NULL rate, referential integrity, and any one-to-many traps are known.
- Date/timestamp columns have documented timezone semantics (UTC vs local, DST handling).

## Procedure

1. **State the question and expected output grain explicitly in a comment header.**
   1. At the top of every SQL file, write a block comment with:
      - **Purpose:** One sentence describing what the query computes.
      - **Grain:** "One output row represents exactly one ___."
      - **Input tables:** List every table/view with its grain.
      - **Output columns:** Describe each.
      - **Owner / last modified.**
   2. If the purpose cannot be written in one sentence, the query is doing too much; split it.
2. **Decompose the query into Common Table Expressions (CTEs) of one logical transformation each.**
   1. **CTE design rules:**
      - Each CTE does exactly one of: filter/select columns, join exactly two inputs, aggregate exactly one grain, window-function exactly one partition spec, union, deduplicate.
      - Each CTE has a verb-prefixed name describing what it does: `orders_filtered`, `customers_enriched`, `order_lines_aggregated_by_order`, `sales_ranked_by_customer_month`. Avoid generic names like `cte1`, `temp`, `data`.
      - Chain CTEs linearly from inputs to final; never nest CTE references inside other CTEs more than 1 level (the CTE after a join references the join CTE, not both its inputs).
   2. **Order of operations inside each CTE:** FROM/JOIN first, WHERE second, GROUP BY/aggregation third, HAVING fourth, WINDOW fifth, SELECT/column aliasing sixth, ORDER BY/LIMIT last (only in final).
   3. Do not use subqueries in `WHERE` or `SELECT` clauses when a CTE + explicit join produces the same logic; subqueries hide intermediate results and complicate debugging.
3. **Write JOINs explicitly and safely.**
   1. Always use explicit `INNER JOIN`, `LEFT JOIN`, `RIGHT JOIN`, `FULL OUTER JOIN`, `CROSS JOIN` syntax. Never comma-list tables in FROM with join conditions in WHERE (`FROM a, b WHERE a.id = b.id`); this is ambiguous and error-prone.
   2. **Pre-join checks (run separately as queries, not in comments):**
      - For each join key on the left table: count of rows, count of distinct keys, NULL key count.
      - For each join key on the right table: count of rows, count of distinct keys, NULL key count.
      - If left is N rows and right is M rows per key → fan-out to N×M rows. Decide whether this is desired (true M2M with bridge/aggregation) or a bug (silent double-count).
   3. **Join-type decision guide:**
      - Use `INNER JOIN` only if the business requirement explicitly says "rows must exist in both" (e.g., sales matched to shipped product where shipped is mandatory).
      - Default to `LEFT JOIN` from the grain-driving table outward. In a star query, the fact table drives and dimensions are LEFT JOINed on (so fact rows with Unknown dimension members are preserved, not silently dropped).
      - Use `RIGHT JOIN` only in rare outer-join inversion cases; avoid. Prefer rewriting with LEFT JOIN for readability.
      - Use `FULL OUTER JOIN` only for reconciliation (comparing two tables); never in a KPI-producing query.
   4. **Equality NULL handling:** SQL `NULL = NULL` evaluates to UNKNOWN, not TRUE, so NULL join keys never match. Use `IS NOT DISTINCT FROM` (where supported) or `(a.key = b.key OR (a.key IS NULL AND b.key IS NULL))` explicitly if NULL-matching is intended.
   5. **Non-equi joins and range joins:** If a join uses `BETWEEN`, `>`, `<`, or temporal validity (`a.effective_date <= b.event_date AND a.expiry_date > b.event_date`), profile row counts before and after; non-equi joins easily explode to cross joins. Precompute indexed bridge tables or use window functions where a non-equi join can be replaced by `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY effective_date DESC)`.
4. **Aggregate safely and eliminate double-count.**
   1. **Before aggregating:** Confirm the input to the GROUP BY has exactly one row per `(grain key)` or that additive measures will sum correctly across duplicate rows of the same grain key. If duplicates exist (e.g., a dimension attribute joined 1:N to the fact), dedupe in a preceding CTE or reorder so aggregation happens before the problematic join.
   2. **Split multi-grain aggregations into separate CTEs then JOIN.** If a report needs "total sales by customer" (1 row per customer) and "total orders by customer" (1 row per customer), aggregate sales in one CTE, orders in another, then join on customer_key. Do not compute both in one GROUP BY on a fact that is at order-line grain; order-level additive measures (e.g., freight) will multiply by line count.
   3. **Explicit COUNT semantics.** Decide and document:
      - `COUNT(*)` — count rows including full-NULL rows (almost always correct for fact row counts).
      - `COUNT(col)` — count non-NULL values of col.
      - `COUNT(DISTINCT col)` — count distinct non-NULL values of col. Beware of `COUNT(DISTINCT)` over non-key columns on grouped results; it is easy to double-count when joining 1:N before the aggregation.
   4. **Safe division and ratios.** Never compute `numerator / denominator` without guards: `NULLIF(denominator, 0)` to avoid division-by-zero, and cast to a decimal/float type to avoid integer division where applicable. Document the denominator's definition explicitly in the comment header.
5. **Use window functions precisely, with deterministic ORDER BY.**
   1. **Prefer window functions to self-joins** for:
      - Ranking: `ROW_NUMBER()`, `RANK()`, `DENSE_RANK()`, `NTILE(n)`.
      - Running/rolling aggregates: `SUM(...) OVER (ORDER BY ... ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)`, windowed `AVG(x) OVER (PARTITION BY ... ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)` for 30-day moving average.
      - LAG/LEAD for period-over-period deltas.
      - FIRST_VALUE / LAST_VALUE for snapshot-at-grain logic.
   2. **DETERMINISTIC ROW_NUMBER is mandatory.** Every `ORDER BY` in a ranking function must include tiebreakers so the function is deterministic. Example: `ROW_NUMBER() OVER (PARTITION BY customer_key, date_trunc('month', order_date) ORDER BY order_amount DESC, order_id ASC)`. Without tiebreakers, re-running the query may produce different winners for tied rows, breaking reproducibility.
   3. **Avoid window functions in WHERE.** Filter the ranked rows in a subsequent CTE: produce the rank in one CTE, SELECT WHERE rn=1 in the next. Readability matters.
6. **Handle NULLs explicitly and date dedupe safely.**
   1. **Write every output column's NULL policy explicitly.** Use `COALESCE`, `NVL`, `IFNULL`, `ISNULL` where the downstream consumer needs a 0 or "Unknown" instead of NULL. Document the policy in the column description. Never leave a numeric output column that feeds a SUM aggregate as NULL unless 0 and NULL are intentionally distinct; by default, sums ignore NULLs and you will get incorrect totals.
   2. **NULL sentinel scan.** Before applying `COALESCE`, scan for sentinel values (-1, 0, "", "1900-01-01") and normalize them to actual NULL first, so the coalesce doesn't mask sentinels.
   3. **Date deduplication / event ordering.** When a single business event has multiple source rows (e.g., event emitted twice with slightly different timestamps), dedupe by (a) partition on the natural/business key, (b) order by source ingestion timestamp or event revision number, (c) pick exactly one row per key using deterministic `ROW_NUMBER`. Never dedupe on event timestamp alone without the revision tiebreaker; two simultaneous events are valid.
   4. **Timezone and date-part semantics.** If timestamps are stored as UTC but reporting is in "local time at site," apply the conversion via a dimension (site.timezone_name) and a library function (`AT TIME ZONE`, `CONVERT_TZ`, `from_utc_timestamp`) explicitly in a CTE, then date-trunc on the converted value. Never truncate the UTC timestamp and call it "local day"; DST transitions will shift days for early-morning events.
7. **Optimize for the target dialect and platform (last, only after correctness is proven).**
   1. **Read query plans.** Run `EXPLAIN` (or dialect equivalent) on the final query. Look for:
      - Sequential scans on large tables without partition pruning (add date predicate, ensure partition keys are referenced in WHERE).
      - Nested-loop joins on large inputs (switch to hash/merge join via hints or statistics update; or pre-filter inputs to reduce size).
      - Cross joins (Cartesian products) appearing where not intended.
      - Spilling to disk / memory overflows.
   2. **Predicate pushdown and pruning.** Push date filters and dimension filters as early as possible in the CTE chain (the first CTE touching that table). CTEs enable this but don't guarantee it; rely on EXPLAIN.
   3. **Partition elimination.** Ensure every fact-table reference has a WHERE clause predicate on its partition key (typically `_loaded_at_utc` or the primary date key) restricting the scan to the minimum required range.
   4. **Materialize large intermediates.** If a CTE is referenced >1 times and produces >1M rows, materialize it as a temp table or intermediate model (with stats/indexes) instead of relying on the CTE being inlined. Most optimizers do not memoize CTEs by default (Postgres >12 with MATERIALIZED, BigQuery, and Spark do sometimes; never assume).
   5. **Approximate algorithms for scale.** For distinct counts on billion-row tables where 0.1% error is acceptable, use dialect-provided approximate functions (`APPROX_COUNT_DISTINCT`, `approx_distinct`, `HLL_COUNT.INIT`/`MERGE`) instead of exact `COUNT(DISTINCT)`. Document the approximation in the header comment.
   6. **Semi-join instead of DISTINCT.** When using `WHERE col IN (subquery)` or `EXISTS` to filter a fact by dimension members, prefer the SEMI-JOIN form (or keep `EXISTS`) over `SELECT DISTINCT` + INNER JOIN; it avoids an unnecessary distinct-sort operation.
8. **Handle dialect differences portably (where code is cross-platform).**
   1. Keep a dialect-abstraction layer in mind; for common operations, use the most portable form and add dialect-specific variants via macros:
      - **String concatenation:** Prefer `CONCAT(a, b, c)` to `a || b` (works everywhere vs missing in T-SQL pre-2012 without setting QUOTED_IDENTIFIER).
      - **Null comparison:** Prefer `IS NOT DISTINCT FROM` (T-SQL/SQLite/Postgres) with a fallback macro `IS_EQUAL_NULLSAFE` for Spark/BigQuery/MySQL (`<=>`).
      - **Date truncation:** `DATE_TRUNC('month', ts)` (ANSI/Postgres/BigQuery/Snowflake/Databricks) vs `DATEADD(DAY, 1-DAY(ts), CAST(ts AS DATE))` / `DATETRUNC` (T-SQL).
      - **Regex:** `REGEXP_LIKE(col, pattern)` (Oracle/Postgres recent) vs `col ~ pattern` (Postgres) vs `REGEXP_CONTAINS(col, pattern)` (BigQuery) vs `col RLIKE pattern` (MySQL/SQLite).
      - **Pagination:** Prefer keyset/seek pagination (`WHERE id > @last_id ORDER BY id LIMIT N`) to `OFFSET N`; offset performance degrades catastrophically on large N.
9. **Validate the query end-to-end.**
   1. **Row-count sanity:** At every CTE boundary, add `SELECT COUNT(*) FROM <cte>` sanity checks as you develop (can comment out later). Confirm counts match expectations from profiled data.
   2. **Known-row recomputation:** Pick 5 specific well-understood rows from the fact table (specific known order IDs, shipment IDs, etc.). Hand-calculate the expected output row for each. Run the query filtered to those 5. They must match exactly.
   3. **Control-total recomputation:** Compute the total of the primary KPI measure both directly from the source table and via the full query over the baseline period. They must match at business-equality tolerance.
   4. **NULL-sentinel test:** Intentionally include one row with every input column set to NULL/sentinel. Verify output matches the documented NULL policy.
   5. **Fan-out regression test:** After every join CTE, assert that row count after join = expected (no surprise N×M explosion). Add a singular data test that runs the assertion on every pipeline run.
10. **Review, commit, and archive alongside its validation evidence.**
    1. Lint the final query (sqlfluff with team conventions).
    2. Attach the validation evidence (known-row hand calculations file, control-total screenshot, EXPLAIN plan summary) as comments or linked files.
    3. Submit for PR review using the SQL review rubric in references.

## Decision points

- **Step 2 (CTE split).** If a CTE exceeds ~200 lines, split it. 200 lines is a soft upper bound for a single logical transformation. If a split would force an unnatural materialization, keep it but add a block comment describing the sub-transformations in order.
- **Step 3 (Join trap discovered).** If profiling reveals the join is 1:many and "many" is not intended, the query is in one of two categories: (a) aggregation must happen before the join → reorder CTEs, (b) grain mismatch → escalate to model owner; do not patch with `SELECT DISTINCT` as a band-aid.
- **Step 4.4 (Division by zero expected for many rows).** If denominator can be zero legitimately (e.g., "periods with no production"), choose: (a) NULL output + documented, (b) 0 output + documented, (c) exclude from result set via WHERE denominator > 0. Never silently return NULLs without the documented choice.
- **Step 5 (Ties in ranking).** If tiebreakers are not available (no revision number, no unique id), escalate to the SME: for tied events, which one "wins"? Without a rule, the query is non-deterministic; never ship non-deterministic code to production.
- **Step 7 (Optimization vs readability tradeoff).** If a "faster" query plan requires an opaque 4-level nested subquery or platform-specific hints, first check that the readability cost is worth it. Query that runs in 30 seconds and is readable beats a query that runs in 15 seconds and no one can debug. Document the tradeoff explicitly.

## Validation

- Header comment is present: purpose (one sentence), grain, inputs, outputs, owner.
- Query uses only explicit JOINs; no comma-list FROM, no implicit cross-joins.
- Every CTE has a verb-prefixed descriptive name and does exactly one logical transformation.
- Join profiles (counts, distinct keys, NULL rates) exist for every JOIN in the query; no unintended fan-out.
- Aggregation inputs are verified at the GROUP BY grain; known duplicates are deduped before aggregation, or duplication is intended and documented.
- Every `ROW_NUMBER` / ranking window has a deterministic ORDER BY with tiebreakers.
- Output columns have explicit NULL policies (COALESCE or intentional NULL documented).
- Date deduplication uses natural key + revision tiebreaker; UTC timestamps have explicit timezone conversion to reporting time via a dimension before truncation.
- EXPLAIN plan analyzed; no cross joins, no full table scans without partition pruning, no known anti-patterns.
- 5 known-row hand-calculations match exactly.
- Control total over baseline period matches direct source table total at business-equality tolerance.
- Singular data test exists that catches fan-out regressions on every pipeline run.
- Lint passes 100% with no rule violations.
- PR review passes against the SQL review rubric.

## Expected outputs

- A version-controlled `.sql` file conforming to all procedure rules with the header comment block.
- If part of a model: a `.yml` metadata file with tests, column descriptions, and references to semantic metrics.
- A validation artifact (markdown or PDF) containing: known-row hand calc table, control-total delta, join profile outputs, EXPLAIN plan summary, singular fan-out test query.
- PR link with review completed.

## Common failure modes

1. **Implicit joins (comma FROM).** A missing WHERE join condition produces a cross join and billion-row result. Remedy: step 3.1 explicit JOINs only; a lint rule forbids comma-list FROM.
2. **Silent fan-out.** Fact joined to a 1:N attribute dimension multiplies additive measures by N. Remedy: step 3.2 pre-join profiling; step 9.5 fan-out regression test in suite.
3. **`COUNT(DISTINCT user_id)` after a 1:N join.** If `users` join to `roles` (1 user : N roles), count distinct is still correct, but `SUM(users.some_additive_field)` on that same GROUP BY is not. Analysts often confuse the two. Remedy: aggregate each measure at its native grain first (CTEs), then join aggregated results.
4. **Non-deterministic ROW_NUMBER.** Ranking ties produce different winners on each run. Remedy: step 5.2 tiebreakers mandatory; lint rule checks for ORDER BY in window functions references >1 column when RANK/ROW_NUMBER is used.
5. **Division by zero or integer division.** `100 / 3 = 33` in integer division, not 33.33. Query silently truncates. Remedy: step 4.4 `CAST(dividend AS DECIMAL(18,6)) / NULLIF(divisor, 0)` with explicit documented type.
6. **UTC day truncation treated as local day.** Reports for a site in UTC-4 show "yesterday" for events that happened at 22:00 UTC (18:00 local yesterday). Remedy: step 6.4 explicit timezone conversion via site dimension BEFORE truncating.
7. **Sentinels treated as valid data.** `-1` or `1900-01-01` survives as if it were a real value, skewing MIN() and averages. Remedy: step 6.2 sentinel-to-NULL before any numeric or date computation.
8. **CTE inlined multiple times causing repeated expensive scans.** Remedy: step 7.4 materialize multi-reference CTEs to temp tables or intermediate models.
9. **`SELECT *` in intermediate CTEs.** Schema drift adds an unexpected column and breaks downstream column ordering. Remedy: explicit column lists in every CTE SELECT. Lint rule forbids `SELECT *`.
10. **Optimization without measurement.** "I rewrote it to use window functions which are faster" with no EXPLAIN, no before/after timing, no proof. Remedy: step 7 requires EXPLAIN analysis; step 9 attaches a plan summary. For large query performance work, use the `optimize.md` workflow formally.

## References to load

- `references/sql-header-template.sql` — Block comment header template with Purpose, Grain, Inputs, Outputs, Owner, Last Modified, Dialect, Approximation Disclosures.
- `references/sql-cte-cheatsheet.md` — 20 worked examples of correct CTE decomposition: filter, join, aggregate, window, dedupe, union, with descriptive verb-prefixed names.
- `references/sql-join-safety-queries.sql` — Profiling queries per join: row counts, distinct keys, NULL counts, expected post-join count, fan-out warning flag.
- `references/sql-window-function-patterns.sql` — Library of window function patterns with mandatory tiebreakers: ranking (ROW_NUMBER/RANK/DENSE_RANK), running totals, rolling averages, LAG/LEAD, FIRST_VALUE/LAST_VALUE, CUME_DIST/PERCENT_RANK, median approx via PERCENTILE_CONT/DISC.
- `references/sql-null-and-sentinel-handling.md` — NULL policy decision tree + sentinel detection regexes/types + explicit COALESCE examples with documented rationale per case.
- `references/sql-dialect-compatibility-matrix.md` — Cross-reference of operations across ANSI, T-SQL, PostgreSQL, Spark SQL, BigQuery, Databricks, Snowflake, with portability macros for string/date/regex/nullsafe-compare/pagination.
- `references/sql-performance-patterns-by-platform.md` — Per-platform optimization recipes: BigQuery slot usage and partition pruning, Snowflake clustering and result caching, Synapse distribution keys and CTAS, Databricks ZORDER and AQE, Postgres partial indexes and parallel query.
- `references/sql-explain-plan-reading-guide.md` — How to read EXPLAIN/EXPLAIN ANALYZE output across 6 platforms, with red flags (nested-loop on large set, cross join, missing partition filter, sort spill) highlighted.
- `references/sql-known-row-reconciliation-template.xlsx` — Workbook with 5 known-row slots for hand calculation, formulas to compare against query output CSV, auto pass/fail coloring.
- `references/sql-review-rubric.md` — 20-item PR review rubric with pass/fail, used as a checklist by every reviewer.
- `references/sql-analysis-review-checklist.md` — 30-item pass/fail checklist covering all 9 procedure steps.

## Completion criteria

- Final SQL file exists with a complete header comment (purpose, grain, inputs, outputs, owner).
- Query uses only explicit JOINs and CTE-based decomposition; no subqueries in WHERE/SELECT when a CTE form is equivalent.
- Every JOIN has been profiled (row counts, distinct keys, NULL counts, fan-out check) and no unintended fan-out exists.
- Every aggregation has been grain-checked; multi-grain measures are aggregated in separate CTEs and then joined.
- Every ranking function uses deterministic tiebreakers.
- NULL/sentinel normalization is applied before any computation; explicit documented NULL policy per output column.
- Timezone conversion is applied before date truncation; timezone source (site dim / config) is explicit.
- EXPLAIN plan has been reviewed; no cross joins, no partition-pruning failures, no unnecessary sorts/distincts.
- 5 known-row hand calculations match exactly.
- Baseline control total matches source at business-equality tolerance.
- Singular data test catches fan-out regressions and is wired into the DQ suite.
- Lint passes 100%; PR review passes against rubric.
- SQL is committed, versioned, and linked to its model/exposure/analysis ticket.
