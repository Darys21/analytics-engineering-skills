# SQL Reference Guide

## When Used
SQL is the **primary language** for:
- Extracting, transforming, and loading (ETL/ELT) data from relational databases and data warehouses
- Analytical querying across fact and dimension tables in star/snowflake schemas
- Defining views, materialized views, stored procedures, and table schemas
- Ad-hoc business intelligence investigations and exploratory data analysis
- Data validation, reconciliation, and quality checks
- Incremental batch and streaming pipeline transformations (dbt, Spark SQL, Flink SQL)
- Warehouse-native transformations in Snowflake, BigQuery, Redshift, Databricks, DuckDB

## When NOT Used
- **Row-by-row procedural logic** (use Python, stored procedure languages, or Spark UDFs instead)
- **Complex numerical/scientific computing** (use Python with NumPy/SciPy or R)
- **Graph traversal and path queries** (use Cypher/Neo4j or Gremlin)
- **Full-text search with ranking** (use Elasticsearch, Solr, or specialized search indexes)
- **Low-latency, sub-millisecond key-value lookups** (use Redis, DynamoDB, or KV stores)
- **Unstructured data processing** (images, audio, raw text NLP) — SQL is for structured/semi-structured
- **Workflow orchestration** (use Airflow, Dagster, Prefect, Fivetran)

---

## Common Mistakes

1. **`SELECT *` in production code** — causes schema-breakage, over-fetching, and ambiguous column joins. **Maintainability recommendation.**
2. **Implicit `CROSS JOIN` via comma syntax** (`FROM a, b WHERE a.id = b.id`) — accidental Cartesian products when predicates are missing. **Hard correctness rule (risk).**
3. **`NULL` = `NULL` comparisons** — SQL uses three-valued logic; `NULL = NULL` evaluates to UNKNOWN, not TRUE. Use `IS NULL` or `IS NOT DISTINCT FROM`. **Hard correctness rule.**
4. **Filtering on `LEFT JOIN`ed columns in `WHERE`** — silently converts to `INNER JOIN` by filtering out NULL-extended rows. Move predicates to `ON` or explicitly handle NULLs. **Hard correctness rule.**
5. **Unbounded window frames** — default `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` differs from `ROWS` in semantics and performance; always specify explicitly for correctness and predictability. **Hard correctness rule (semantics) + performance heuristic.**
6. **`COUNT(column)` when meaning `COUNT(*)`** — `COUNT(col)` excludes NULLs; `COUNT(*)` counts all rows including full-NULL rows. Choose intentionally based on whether NULLs should count. **Hard correctness rule.**
7. **`DISTINCT` used to "fix" duplicate rows** — symptom of bad joins or model issues; deduplicate explicitly with `ROW_NUMBER()` and understand the source of duplication. **Hard correctness rule (diagnostic).**
8. **Date literals without timezone awareness** — `'2024-01-01'` behaves differently across timezones, session settings, and dialects. Use explicit timezone-typed literals or anchor to UTC. **Hard correctness rule (risk).**
9. **Correlated subqueries on large tables** — row-by-row execution; rewrite as `JOIN` or window function when the optimizer does not decorrelate automatically. **Performance heuristic.**
10. **Deeply nested subqueries without CTEs** — unreadable and hard to debug; refactor to CTEs. **Maintainability recommendation.**

---

## Trade-offs

| Decision | Advantages | Disadvantages |
|----------|-----------|---------------|
| **CTEs vs Subqueries** | Readable, linear, reusable aliases, debuggable step-by-step | Some older optimizers (MySQL < 8.0.14, old Postgres) don't pushdown predicates into CTEs |
| **CTEs vs Temp Tables** | Single-statement, no side effects, inline execution plan | Materialized CTEs (Postgres `MATERIALIZED`, Oracle) repeat work if referenced multiple times; temp tables can be indexed |
| **Window Functions vs Self-Joins** | Single scan, O(n) vs O(n²), no duplicate inflation | Cannot always push aggregates before window; memory for sort/hash window |
| **`IN` vs `EXISTS` vs `JOIN`** | `EXISTS` short-circuits on first match; `JOIN` allows column access | `IN (subquery)` with NULLs returns empty (surprising); `NOT IN` with NULLs returns nothing |
| **`UNION` vs `UNION ALL`** | `UNION` deduplicates output | `UNION` requires expensive sort-hash distinct; use `UNION ALL` unless dedup is required |
| **Star Schema Query vs Normalized 3NF** | Fewer joins, business-readable, optimizer-friendly | Denormalized storage cost; ETL complexity for SCDs |
| **Materialized Views vs Derived Tables** | Pre-computed, indexable, low-latency reads | Staleness; refresh cost; storage overhead |

---

## Good Implementation

### Readable CTE Structure (Linear DAG)

```sql
WITH base_orders AS (
    SELECT
        order_id,
        customer_id,
        order_date,
        status,
        total_amount
    FROM raw.orders
    WHERE order_date >= DATE_TRUNC('year', CURRENT_DATE) - INTERVAL '2 years'
),

valid_customers AS (
    SELECT customer_id, country, segment
    FROM raw.customers
    WHERE is_active = TRUE
),

order_enriched AS (
    SELECT
        o.order_id,
        o.customer_id,
        c.country,
        c.segment,
        o.order_date,
        o.total_amount
    FROM base_orders o
    INNER JOIN valid_customers c USING (customer_id)
),

daily_agg AS (
    SELECT
        DATE_TRUNC('day', order_date) AS order_day,
        country,
        segment,
        COUNT(*)                           AS order_count,
        SUM(total_amount)                  AS revenue,
        AVG(total_amount)                  AS avg_order_value
    FROM order_enriched
    GROUP BY 1, 2, 3
)

SELECT *
FROM daily_agg
ORDER BY order_day DESC, country, segment;
```

**Principles:** Each CTE has one responsibility; linear dependency (no diamond joins unless necessary); CTEs named for what they *produce*, not how.

---

### Correct Joins & NULL Semantics

```sql
-- LEFT JOIN: keep all customers, even those with zero orders
-- Predicate on orders MUST be in ON, not WHERE
SELECT
    c.customer_id,
    c.name,
    COUNT(o.order_id) AS order_count  -- COUNT(o.id) excludes NULLs → correct zero
FROM dim_customers c
LEFT JOIN fct_orders o
    ON c.customer_id = o.customer_id
    AND o.order_date >= '2024-01-01'   -- time filter here, NOT in WHERE
GROUP BY c.customer_id, c.name;

-- NULL-safe equality (dialect-aware)
-- Postgres / DuckDB / BigQuery:
SELECT * FROM t1 JOIN t2 ON t1.col IS NOT DISTINCT FROM t2.col;
-- Snowflake:
SELECT * FROM t1 JOIN t2 ON EQUAL_NULL(t1.col, t2.col);
-- T-SQL:
SELECT * FROM t1 JOIN t2 ON (t1.col = t2.col OR (t1.col IS NULL AND t2.col IS NULL));
```

---

### Conditional Aggregation (Avoid PIVOT)

```sql
SELECT
    DATE_TRUNC('month', order_date) AS month,
    COUNT(*)                                                      AS total_orders,
    COUNT(CASE WHEN status = 'completed' THEN 1 END)             AS completed_orders,
    COUNT(CASE WHEN status = 'cancelled' THEN 1 END)             AS cancelled_orders,
    SUM(CASE WHEN country = 'US' THEN total_amount ELSE 0 END)   AS us_revenue,
    SUM(CASE WHEN country = 'FR' THEN total_amount ELSE 0 END)   AS fr_revenue,
    -- safe division avoiding /0
    DIV0(SUM(CASE WHEN status = 'returned' THEN total_amount END),
         SUM(total_amount))                                      AS return_rate
FROM fct_orders
GROUP BY 1
ORDER BY 1 DESC;
```

**Why:** `PIVOT` is syntactic sugar, dialect-specific, and rigid. Conditional aggregation is portable, composable, and optimizer-friendly.

---

### Window Functions & Deduplication

```sql
-- Dedup: keep latest version per natural key
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY business_key
            ORDER BY updated_at DESC, ingestion_ts DESC
        ) AS rn
    FROM src_orders
)
SELECT * EXCLUDE (rn)
FROM ranked
WHERE rn = 1;

-- Running total, moving average, YoY
SELECT
    date,
    country,
    revenue,
    SUM(revenue)        OVER (PARTITION BY country ORDER BY date ROWS UNBOUNDED PRECEDING)       AS running_rev,
    AVG(revenue)        OVER (PARTITION BY country ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS avg_30d,
    LAG(revenue, 365)   OVER (PARTITION BY country ORDER BY date)                                AS rev_same_day_last_year,
    revenue / NULLIF(LAG(revenue, 365) OVER (PARTITION BY country ORDER BY date), 0) - 1         AS yoy_growth
FROM daily_country_revenue
ORDER BY country, date;
```

---

### Date Logic (Timezone-Aware)

```sql
-- Always anchor to UTC/warehouse TZ; convert at report layer
SELECT
    CONVERT_TIMEZONE('UTC', 'Europe/Paris', event_time_utc)  AS event_time_paris,  -- Snowflake
    DATE_TRUNC('day', event_time_paris)                     AS event_day_paris,
    LAST_DAY(event_time_paris, 'month')                     AS month_end,
    DATEADD('day', -DATE_PART('dow', event_day_paris)::INTEGER, event_day_paris) AS week_start_monday,
    CURRENT_DATE                                            AS report_date;

-- Date dimension join for fiscal calendars (never hardcode)
SELECT
    d.fiscal_week,
    d.fiscal_year,
    SUM(f.revenue) AS revenue
FROM fct_sales f
JOIN dim_date d ON f.sale_date = d.date
GROUP BY 1, 2;
```

---

### Incremental / SCD Logic

```sql
-- Merge (Upsert) pattern for SCD Type 1
MERGE INTO dim_customers tgt
USING stg_customers src
   ON tgt.customer_bk = src.customer_bk
WHEN MATCHED AND (
    tgt.name <> src.name OR tgt.email <> src.email OR tgt.country <> src.country
) THEN UPDATE SET
    name        = src.name,
    email       = src.email,
    country     = src.country,
    updated_at  = CURRENT_TIMESTAMP()
WHEN NOT MATCHED THEN INSERT (customer_bk, name, email, country, created_at, updated_at)
    VALUES (src.customer_bk, src.name, src.email, src.country, CURRENT_TIMESTAMP(), CURRENT_TIMESTAMP());
```

---

## Dialect-Specific Differences

| Feature | T-SQL (SQL Server) | Postgres | Snowflake | DuckDB | Spark SQL |
|---------|-------------------|----------|-----------|--------|-----------|
| **LIMIT** | `TOP n` or `OFFSET…FETCH NEXT n ROWS ONLY` | `LIMIT n` | `LIMIT n` | `LIMIT n` | `LIMIT n` |
| **String concat** | `+` (NULL propagates) or `CONCAT()` | `\|\|` or `CONCAT()` | `\|\|` or `CONCAT()` | `\|\|` or `CONCAT()` | `\|\|` or `CONCAT()` |
| **Date arith** | `DATEADD(day, n, col)` | `col + INTERVAL 'n days'` | `DATEADD('day', n, col)` | `col + INTERVAL n DAY` | `date_add(col, n)` |
| **Boolean literals** | `1`/`0` (BIT) or `'true'` | `TRUE` / `FALSE` | `TRUE` / `FALSE` | `TRUE` / `FALSE` | `true` / `false` |
| **Quoted identifiers** | `"id"` (QUOTED_IDENTIFIER ON) or `[id]` | `"id"` | `"id"` | `"id"` | `` `id` `` or `"id"` |
| **Index creation** | Clustered/nonclustered, columnstore | B-tree, hash, GIN, BRIN, GiST | Automatic (micro-partitions + clustering keys) | Automatic + ART indexes | Delta Lake data skipping / Z-order |
| **Top-N per group** | `CROSS APPLY (SELECT TOP 1 …)` or window | Window, `LATERAL JOIN` | Window, `LATERAL` | Window, `LATERAL` | Window, `LATERAL` |
| **Explain plan** | `SET SHOWPLAN_XML ON` / Actual Execution Plan | `EXPLAIN (ANALYZE, BUFFERS)` | `EXPLAIN USING {TEXT\|JSON\|TABULAR}` | `EXPLAIN ANALYZE` | `EXPLAIN (FORMATTED, COST)` |
| **Array / Semi-structured** | `OPENJSON`, `JSON_VALUE` (2016+) | `JSONB`, `->>`, array ops | `VARIANT`, `PARSE_JSON`, `LATERAL FLATTEN` | `JSON`, struct/list | `STRUCT`, `ARRAY`, `EXPLODE` |
| **Materialized CTE** | Not supported (inline) | `WITH ... AS MATERIALIZED (...)` | `WITH ... AS (...)` (cost-based) | Cost-based | Cost-based |

---

## Dialect Specific Notes

The following sections detail behavior differences across five common SQL dialects. For portable code, wrap dialect-specific operations in macros (e.g., dbt macros) and test both branches.

### T-SQL (SQL Server, Azure SQL DB, Azure Synapse Dedicated)

1. **String concatenation & NULL propagation:**
   - `a + b` operator: propagates NULL (if either operand is NULL, result is NULL).
   - `CONCAT(a, b, c)` function: treats NULLs as empty strings (no NULL propagation); returns a string concatenation of all arguments.
   - `||` operator: NOT supported by default; requires `SET QUOTED_IDENTIFIER OFF` + `SET ANSI_PADDING ON` and even then behaves inconsistently. **Preferred pattern:** Use `CONCAT()` for portable non-NULL-propagating concatenation, or `+` with explicit `ISNULL/COALESCE` guards.

2. **Date functions:**
   - `DATEADD(day, 7, order_date)` — date part is a keyword, not a string; returns the same type as input.
   - `DATEDIFF(day, start_date, end_date)` — signed integer difference in the specified date part boundary crossings.
   - `DATE_TRUNC` is NOT available prior to SQL Server 2022. Use `DATEADD(DAY, 1 - DAY(ts), CAST(ts AS DATE))` style workarounds for month-truncation on older versions; `DATETRUNC(month, ts)` on SQL Server 2022+.
   - `GETDATE()` / `SYSDATETIME()` return server-local time; use `GETUTCDATE()` / `SYSUTCDATETIME()` for UTC.

3. **QUALIFY row_number filtering:**
   - NOT supported. Wrap window functions in a CTE or subquery and filter on the ranking column in an outer WHERE: `WITH r AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) AS rn FROM src) SELECT * FROM r WHERE rn = 1`.

4. **PIVOT syntax:**
   - Supports explicit `PIVOT` operator with an aggregate and explicit value list: `SELECT ... FROM src PIVOT (SUM(amount) FOR status IN ([completed], [cancelled], [refunded])) AS p`.
   - Column aliases in the IN-list must be quoted with square brackets.
   - Conditional aggregation (`SUM(CASE WHEN status='completed' THEN amount END)`) is the portable alternative and recommended for maintainability.

5. **SELECT * EXCEPT / REPLACE:**
   - NOT supported in T-SQL. Explicitly list columns.

6. **Incremental MERGE syntax:**
   - `MERGE target USING source ON ... WHEN MATCHED AND (hash_differs) THEN UPDATE SET ... WHEN NOT MATCHED THEN INSERT ... WHEN NOT MATCHED BY SOURCE THEN DELETE ...` (supports SCD1 full upsert + soft/hard delete).
   - Caution: `MERGE` in T-SQL has known race conditions under high concurrency; use `HOLDLOCK` / `SERIALIZABLE` hints or wrap in a transaction for incremental idempotency. For large tables, stage + `UPDATE` + `INSERT` batches often outperform a single MERGE.

### PostgreSQL (including Aurora Postgres, AlloyDB, Redshift with compatibility layer)

1. **String concatenation & NULL propagation:**
   - `a || b` operator: propagates NULL (NULL input → NULL result) per SQL standard.
   - `CONCAT(a, b, c)` function: treats NULLs as empty strings (no NULL propagation).
   - `FORMAT()` or `concat_ws(' ', a, b, c)` for separator-joined, NULL-skipping concatenation.

2. **Date functions:**
   - `order_date + INTERVAL '7 days'` — ANSI-style interval arithmetic.
   - `DATE_TRUNC('month', order_date)` — date part is a string literal; returns timestamptz/date truncated to the specified part.
   - `AGE(end_date, start_date)` — returns an interval type (years-months-days); use `EXTRACT(EPOCH FROM AGE(...))` for seconds if needed.
   - `NOW()` returns `timestamptz` at UTC+session TZ; `NOW() AT TIME ZONE 'UTC'` for explicit UTC.

3. **QUALIFY row_number filtering:**
   - NOT supported in core Postgres before PostgreSQL 16. As of PG16, `QUALIFY` is supported. For older versions use CTE/subquery pattern: `WITH r AS (SELECT *, ROW_NUMBER() OVER (...) AS rn) SELECT * FROM r WHERE rn = 1`.

4. **PIVOT syntax:**
   - No built-in `PIVOT` operator. Use conditional aggregation `SUM(CASE WHEN ... END) FILTER (WHERE status = 'completed')`. The `FILTER` clause (Postgres 9.4+) is more efficient than CASE with NULL-else.
   - `tablefunc` extension provides `CROSSTAB` for true pivot output; requires explicit type declaration.

5. **SELECT * EXCEPT / REPLACE:**
   - NOT supported natively. Explicitly list columns.

6. **Incremental MERGE syntax:**
   - `MERGE INTO target USING source ON ... WHEN MATCHED AND ... THEN UPDATE SET ... WHEN NOT MATCHED THEN INSERT ...` (Postgres 15+).
   - Pre-Postgres 15: use classic `INSERT ... ON CONFLICT (key) DO UPDATE SET ...` (UPSERT) for SCD1. For delete handling, pair with a separate DELETE using a left-anti-join pattern.

### Snowflake

1. **String concatenation & NULL propagation:**
   - `a || b` operator: propagates NULL per default. Set `CONCAT_NULL_YIELDS_NULL = FALSE` at session/account level to treat NULLs as empty strings (non-default).
   - `CONCAT(a, b, c)` function: treats NULLs as empty strings (no NULL propagation); identical to Postgres/SQL Server `CONCAT`.
   - `CONCAT_WS(sep, a, b, c)` skips NULLs and joins with a separator.

2. **Date functions:**
   - `DATEADD('day', 7, order_date)` — date part is a string literal.
   - `DATEDIFF('day', start_date, end_date)` — counts whole boundary crossings.
   - `DATE_TRUNC('month', order_date)` — standard truncation; returns the first day of the period.
   - `CURRENT_TIMESTAMP()` returns the wall-clock time; use `CONVERT_TIMEZONE('UTC', ts)` for conversions.

3. **QUALIFY row_number filtering:**
   - FULLY SUPPORTED. Preferred concise pattern: `SELECT * FROM src QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) = 1`.
   - Executes after WHERE / GROUP BY / HAVING but before ORDER BY. Commonly used instead of CTE wrapping for dedup and top-N per group.

4. **PIVOT syntax:**
   - Supports explicit `PIVOT` with aggregate and value list: `SELECT * FROM src PIVOT (SUM(amount) FOR status IN ('completed', 'cancelled', 'refunded'))`.
   - Also supports `UNPIVOT` for the reverse direction.
   - Conditional aggregation remains portable; `PIVOT` is convenient for ad-hoc with fixed value lists.

5. **SELECT * EXCEPT / REPLACE:**
   - FULLY SUPPORTED.
   - `SELECT * EXCLUDE (rn, hash_col, _loaded_at) FROM ranked` — removes listed columns from the star expansion.
   - `SELECT * REPLACE (UPPER(name) AS name, COALESCE(email, '') AS email) FROM src` — replaces the expressions of specific columns in the star output.
   - These are Snowflake-specific; do not use in portable code paths.

6. **Incremental MERGE syntax:**
   - `MERGE INTO target USING source ON match_key WHEN MATCHED AND source._hash != target._hash THEN UPDATE SET ... WHEN NOT MATCHED THEN INSERT ... WHEN NOT MATCHED BY SOURCE THEN DELETE` — fully-featured and optimized for micro-partition pruning on the join key.
   - Best practice: cluster both tables by the merge join key to ensure efficient pruning. Use `MATCH BY SOURCE` variants for complex SCD2 logic with explicit row effective dates.

### DuckDB

1. **String concatenation & NULL propagation:**
   - `a || b` operator: propagates NULL per ANSI standard.
   - `CONCAT(a, b, c)` function: treats NULLs as empty strings (no NULL propagation).
   - `CONCAT_WS` also supported.

2. **Date functions:**
   - `order_date + INTERVAL 7 DAY` or `DATEADD('day', 7, order_date)` — both forms accepted.
   - `DATE_TRUNC('month', order_date)` — standard truncation.
   - `CURRENT_TIMESTAMP`, `NOW()` supported.

3. **QUALIFY row_number filtering:**
   - FULLY SUPPORTED. `SELECT * FROM src QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) = 1`.

4. **PIVOT syntax:**
   - Supports both `PIVOT` operator and conditional aggregation.
   - `PIVOT src ON status IN ('completed','cancelled') USING SUM(amount)` — compact syntax with inferred grouping columns.

5. **SELECT * EXCEPT / REPLACE:**
   - FULLY SUPPORTED.
   - `SELECT * EXCLUDE (rn, _tmp) FROM ...` (keyword EXCLUDE, not EXCEPT) — removes columns.
   - `SELECT * REPLACE (UPPER(name) AS name) FROM ...` — replaces specific column expressions.
   - Note: keyword is `EXCLUDE` not `EXCEPT` (differs from Snowflake).

6. **Incremental MERGE syntax:**
   - `MERGE INTO target USING source ON match_key WHEN MATCHED THEN UPDATE SET ... WHEN NOT MATCHED THEN INSERT ... WHEN NOT MATCHED BY SOURCE THEN DELETE` — full ANSI-style MERGE with delete branch.
   - For large local workloads, DuckDB often achieves better throughput with separate `INSERT ... WHERE key NOT IN (SELECT key FROM target)` + `UPDATE` batches due to vectorized execution.

### Spark SQL (Databricks, Delta Lake, Synapse Serverless Spark pools)

1. **String concatenation & NULL propagation:**
   - `a || b` operator: behavior depends on `spark.sql.legacy.concatNullsInBinaryComparison` config; modern Spark (3.0+) propagates NULL by default.
   - `CONCAT(a, b, c)` function: propagates NULL (different from most other dialects where CONCAT skips NULLs). For NULL-safe concatenation use `CONCAT_WS('', a, b, c)` which skips NULLs and joins with empty string.
   - Key difference: Spark `CONCAT` NULL-propagates; all other dialects above treat NULLs as empty strings in `CONCAT()`.

2. **Date functions:**
   - `DATE_ADD(order_date, 7)` — second arg is integer days.
   - `ADD_MONTHS(order_date, 3)` for months.
   - `DATE_TRUNC('month', order_date)` or `TRUNC(order_date, 'MM')` — both work.
   - `DATEDIFF(end_date, start_date)` — returns days between dates (note reversed arg order vs Snowflake/SQL Server).
   - `CURRENT_TIMESTAMP()` for session TZ; `FROM_UTC_TIMESTAMP` / `TO_UTC_TIMESTAMP` for conversions.

3. **QUALIFY row_number filtering:**
   - FULLY SUPPORTED as of Spark 3.2 / Databricks Runtime 10.4 LTS+.
   - `SELECT * FROM src QUALIFY ROW_NUMBER() OVER (PARTITION BY id ORDER BY updated_at DESC) = 1`.
   - For older Spark use CTE/subquery pattern.

4. **PIVOT syntax:**
   - Supports explicit `PIVOT` on DataFrames and SQL: `SELECT * FROM src PIVOT (SUM(amount) FOR status IN ('completed', 'cancelled'))`.
   - `UNPIVOT` / `STACK()` for the reverse.
   - Conditional aggregation is portable across all Spark versions.

5. **SELECT * EXCEPT / REPLACE:**
   - NOT supported directly. Databricks SQL supports star with column drops via `SELECT * EXCEPT(col1, col2)` on some recent runtimes; verify version. Portable fallback: explicitly list columns.

6. **Incremental MERGE syntax:**
   - Delta Lake MERGE: `MERGE INTO target USING source ON key WHEN MATCHED AND _hash_changed THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT * WHEN NOT MATCHED BY SOURCE THEN DELETE`.
   - Supports SCD2 with `WHEN MATCHED AND current_flag = 1 THEN UPDATE SET current_flag = 0` + separate `WHEN NOT MATCHED THEN INSERT` pattern, or use Delta Lake `SCD TYPE 2` operation in Delta Live Tables.
   - Optimize by partitioning and Z-ordering both tables on the merge key; Delta Lake auto-skips unaffected files via data skipping.

---

## How to Test SQL

1. **Unit-test logic with known inputs** — Build test fixtures (CTEs with VALUES) and assert expected outputs.
   ```sql
   WITH test_input(order_id, status, amount) AS (VALUES
       (1, 'completed', 100),
       (2, 'completed', 200),
       (3, 'cancelled',  50),
       (4, NULL,          10)
   ),
   actual AS (
       SELECT
           COUNT(*)                                            AS n,
           COUNT(CASE WHEN status='completed' THEN 1 END)      AS completed_n,
           SUM(amount)                                         AS total
       FROM test_input
   )
   SELECT CASE WHEN n = 4 AND completed_n = 2 AND total = 360
               THEN 'PASS' ELSE 'FAIL' END AS unit_test FROM actual;
   ```
2. **Row-count reconciliation** — `SELECT COUNT(*) FROM source` vs target; incremental row counts should match delta.
3. **Primary key uniqueness** — `SELECT key, COUNT(*) FROM t GROUP BY key HAVING COUNT(*) > 1`.
4. **Referential integrity** — Anti-join: `SELECT f.fk FROM fct f LEFT JOIN dim d USING(fk) WHERE d.pk IS NULL`.
5. **Distribution checks** — Min/max, percentiles, unexpected NULL rates, top-N outliers.
6. **Regression tests** — Save canonical result sets as snapshots; compare on schema change.
7. **Tools:** dbt tests (singular + generic), Great Expectations, SQLFluff (linting), tSQLt (T-SQL unit tests).

---

## Performance Behavior

| Pattern | Cost Profile | Notes |
|---------|-------------|-------|
| **Full table scan** | O(n) | Avoid on large tables without predicate pushdown |
| **Nested-loop join** | O(n · log m) or O(n · m) | Good for small outer table + indexed inner |
| **Hash join** | O(n + m) | Default for large equi-joins; memory proportional to build side |
| **Sort-merge join** | O(n log n + m log m) | Good for sorted inputs, very large data, low memory |
| **Window with sort** | O(n log n) per PARTITION/ORDER BY | Minimize sort keys; cluster/partition data |
| **DISTINCT** | O(n log n) or O(n) hash | Prefer `GROUP BY` or EXISTS; never use to "fix" a bad join |
| **SELECT \*** | I/O + network waste | Explicit column lists enable columnar pruning |
| **CTE referenced N times** | 1 scan (inline) or N scans (materialized) | Know your optimizer; temp tables if N > 2 |
| **String LIKE '%x%'** leading wildcard | No index use (scan) | Use trigram/Full-Text indexes for contains search |
| **Functions on WHERE columns** | Prevents index usage, block-range pruning | `WHERE DATE(ts)=?` → index on DATE(ts) or rewrite range |

---

## What to Inspect First (When a Query is Slow/Wrong)

1. **`EXPLAIN ANALYZE` / actual execution plan** — Is the row estimate off by >10×? Is there a nested loop on million-row tables? Full scans on filters?
2. **Predicate selectivity** — Which `WHERE` clauses actually prune data? Are SARGable predicates used? Are partition/clustering keys leading filters?
3. **Join order & types** — Are small tables on the build side of hash joins? Are outer joins preventing predicate pushdown?
4. **Duplicate explosion** — Does a 1:many join followed by an aggregate produce inflated sums? Add `COUNT(*)` sanity checks.
5. **NULL handling** — Did a `WHERE col = NULL` silently drop rows? Did `NOT IN (subquery)` with NULLs return zero rows?
6. **Data skew** — Does one partition/key have 10× more rows? (Look for "spill" in warehouse profiles.)
7. **Statistics freshness** — Are table statistics outdated, misleading the optimizer? (Run `ANALYZE`, `COMPUTE STATISTICS`, warehouse auto-stats.)
8. **Columnar projection** — Is the project list narrow? Avoid `SELECT *` on columnar stores.
9. **Sort / window spill** — Do `ORDER BY` / window functions spill to disk? Increase memory or reduce sort key count.
10. **Sargable predicates** — Is there `UPPER(col) = ?` or `YEAR(date_col) = 2024` instead of `date_col BETWEEN '2024-01-01' AND '2024-12-31'`?

---

## Analytical Patterns & Anti-Patterns

### ✅ Patterns (Prefer)
- **Medallion CTE pipelines** with explicit naming
- **Explicit equi-joins** with `USING()` or clear ON predicates
- **Calendar table joins** for fiscal/holiday logic
- **Anti-joins / left-semi joins** for set membership
- **`QUALIFY ROW_NUMBER() = 1`** for dedup (where supported)
- **GROUP BY ALL** (Snowflake/DuckDB) to avoid mismatched column lists

### ❌ Anti-Patterns (Avoid)
- **Correlated subqueries in SELECT clause** running per-row
- **Deeply nested `CASE`** — refactor into lookup dimension or multiple CTE steps
- **`OR` in join predicates** — forces nested loop; `UNION ALL` of two joins is often faster
- **Trailing `ORDER BY` in subqueries/CTEs** without `LIMIT` — ignored by optimizer, wasted work
- **Non-sargable date filters**: `YEAR(ts) = 2024 AND MONTH(ts) = 1`
- **Over-normalized joins** (more than 6–8 tables) in BI-facing queries — use denormalized marts

---

## Indexes & Query Plans

**Performance heuristics — always check execution plan, then consider.**

- **OLTP systems** (Postgres, SQL Server): Check actual execution plan first. If the plan shows repeated table lookups on a high-selectivity access pattern, consider a B-tree on high-selectivity JOIN/WHERE columns. Consider covering indexes that include projected columns to avoid bookmark lookups when the plan shows lookups are the bottleneck.
- **OLAP warehouses** (Snowflake, BigQuery): Traditional indexes are typically not supported or beneficial. Check the query profile for partition/clustering pruning misses. Consider **clustering / sort keys / partitioning** (e.g., Snowflake `CLUSTER BY (date, country)`) for zone-map pruning when the profile shows full-table scans on filters that could prune.
- **DuckDB**: ART (Adaptive Radix Tree) indexes help point lookups on FK/PK columns; auto-created for PK. Check the plan before adding secondary indexes.
- **Spark / Delta Lake**: If the query profile shows poor data skipping, consider Z-order by commonly filtered columns and partition by low-cardinality date columns.
- **Reading a plan**: Work from the *innermost* (leaves) node *outward*. Estimate vs actual row mismatches of >10× indicate stale statistics. A Nested Loop with a Sequential Scan inside it on a large table is a common sign of a missing join predicate or missing index — verify against the actual plan before acting.
- **FK column indexes**: On OLTP systems, check the plan for join performance. If FK joins are the bottleneck (nested-loop scans without index), consider indexing FK columns. **Performance heuristic, not a hard rule.**

**Hard correctness rule (NULLs in outer join key semantics):** When a column participates in an OUTER JOIN, the engine's treatment of NULL join keys is consistent (NULLs do not match NULLs in standard SQL), but the result can be surprising. For OUTER JOINs, verify that: (1) NULL-extended rows from the preserved side are not accidentally filtered in WHERE, and (2) join keys that include NULLs are handled explicitly (IS NOT DISTINCT FROM or NULL-safe equality operator) if NULL-matching is intended.

---
