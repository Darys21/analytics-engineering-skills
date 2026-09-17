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

1. **`SELECT *` in production code** — causes schema-breakage, over-fetching, and ambiguous column joins
2. **Implicit `CROSS JOIN` via comma syntax** (`FROM a, b WHERE a.id = b.id`) — accidental Cartesian products when predicates are missing
3. **`NULL` = `NULL` comparisons** — SQL uses three-valued logic; use `IS NULL` or `IS NOT DISTINCT FROM`
4. **Filtering on `LEFT JOIN`ed columns in `WHERE`** — silently converts to `INNER JOIN`; move conditions to `ON`
5. **Unbounded window frames** — default `RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` differs from `ROWS`; always specify for performance and correctness
6. **`COUNT(column)` when meaning `COUNT(*)`** — `COUNT(col)` excludes NULLs; `COUNT(*)` counts rows
7. **`DISTINCT` used to "fix" duplicate rows** — symptom of bad joins or model issues; deduplicate explicitly with `ROW_NUMBER()`
8. **Date literals without timezone awareness** — `'2024-01-01'` behaves differently across timezones and session settings
9. **Correlated subqueries on large tables** — row-by-row execution; rewrite as `JOIN` or window function
10. **Deeply nested subqueries without CTEs** — unreadable and hard to debug; refactor to CTEs

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

- **OLTP indexes** (Postgres, SQL Server): B-tree on high-selectivity JOIN/WHERE columns; covering indexes include projected columns → avoid bookmark lookups.
- **OLAP warehouses** (Snowflake, BigQuery): Do *not* create traditional indexes. Use **clustering / sort keys / partitioning** (e.g., Snowflake `CLUSTER BY (date, country)`) for zone-map pruning.
- **DuckDB**: ART (Adaptive Radix Tree) indexes for point lookups on FK/PK; auto-created for PK.
- **Spark / Delta Lake**: Z-order by commonly filtered columns; partition by low-cardinality date columns.
- **Reading a plan**: Work from the *innermost* (leaves) node *outward*. Seek > Index Seek > Scan. A Nested Loop with a Scan inside it on a large table is almost always a bug.

---
