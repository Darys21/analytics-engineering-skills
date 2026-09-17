# Analytics Engineering Reference Guide

## When Used
Analytics engineering is the **discipline that sits between data engineering and data analysis/BI**, turning raw data into reliable, documented, queryable datasets for decision-making. Use this playbook when:
- Building / operating a modern lakehouse or data warehouse (Snowflake, Databricks, BigQuery, Fabric, Redshift, DuckDB)
- Using tools like **dbt (data build tool)**, SQLMesh, dbt Core, dbt Cloud, Coalesce, Dataform, or raw SQL/Python to transform raw data → marts
- Applying software engineering practices (version control, CI/CD, testing, modularity, DRY) to data pipelines
- Publishing datasets used by 3+ downstream consumers (analysts, BI dashboards, ML feature stores, reverse ETL)

## When NOT Used
- **One-off throwaway Jupyter analysis** — a single analyst exploring; don't engineer a reusable mart for a one-off.
- **Low-code / no-code SaaS ETL only** — if Fivetran/Stitch/Airbyte + Looker Model covers everything, formal AE discipline is optional (but still recommended for tests & docs).
- **Pure streaming pipelines only (Kafka / Flink / ksqlDB)** — use streaming engineering patterns; most AE principles still apply (contracts, tests, lineage) but the runtime is different.
- **Application databases / OLTP schema design** — app data models are normalised for write throughput; analytics models are denormalised for read throughput.
- **Data ingestion / extraction only** — ingestion engineers handle connectors, raw zones, CDC; AE starts *after* raw data has landed.

---

## Common Mistakes

1. **Skipping Bronze → building Silver on raw CSVs directly.** You need the raw data preserved verbatim for reproducibility; if your source changes format, silver breaks and you have no way to replay without re-extracting.
2. **No incremental strategies on large fact tables** — every run `truncate + reload` 500M rows → multi-hour pipelines, massive credit burn, SLA misses.
3. **Mart models that read directly from raw sources (no silver/staging layer)** — one upstream rename cascades into 40 broken marts; stage once, reference everywhere.
4. **One giant `all_marts.sql` file doing 5 CTEs and 10 joins** — can't be reused, tested, or maintained; decompose into staging + intermediate + mart layers.
5. **Tests only on the final mart, not intermediate models** — when numbers are wrong, you have no idea where it broke; test every contract boundary.
6. **`{{ ref('') }}` to mart models from *other* marts (cross dependencies)** — creates circular refs, impossible to build incrementally; intermediate models expose shared logic, marts don't reference marts.
7. **No documentation / column descriptions** — analysts cannot trust a dataset without context; YAML `description:` fields are not optional.
8. **Hundreds of lines of Jinja inside a single model SQL** — unreadable; extract into custom macros or Python model.
9. **"Hard refresh every time is simpler" — no idempotency.** Pipeline fails at 95% → you have to start over + consumers see stale data for an extra day.
10. **Ignoring schema drift.** Source adds a column → silently ignored. Source drops a column → 50 mart models break. Add schema-change tests + contracts.
11. **Using Python models when SQL is fine.** Python is slower, more expensive, less portable; only use it for logic you can't express in SQL.
12. **Committing secrets in `profiles.yml` / `connections.toml`.** Use env vars + secret managers.
13. **No data contract between producers and consumers.** When the source team changes a column meaning and doesn't tell you, your dashboard becomes wrong and you only find out 3 weeks later when sales calls BS.

---

## Trade-offs

| Decision | Advantages | Disadvantages |
|----------|-----------|---------------|
| **Medallion (Bronze/Silver/Gold/Mart) vs Staging→Marts 2-layer** | Medallion: clear layer responsibilities, replayability, best practice for lakehouse. 2-layer: simpler, faster to bootstrap for small warehouse. | Medallion: more steps, more storage, slightly more complex DAG. 2-layer: no re-playable cleansed zone; when raw schema changes you fix N models. |
| **dbt Core (self-hosted) vs dbt Cloud vs SQLMesh** | Core: 100% portable, CI-free local run, no license cost. Cloud: scheduler + IDE + SLAs + jobs UI. SQLMesh: unit tests, virtual data environments (preview without write). | Core: need to schedule/orchestrate yourself (Airflow/Dagster). Cloud: $ cost at scale, vendor lock-in. SQLMesh: smaller ecosystem, newer. |
| **SQL-only vs SQL + Python models** | SQL: 10× more engineers can maintain it, runs entirely in warehouse compute, portable. Python: regex/NLP/ML/complex math possible. | Python: runs on cluster compute, not all warehouses support it (Snowflake Snowpark, Databricks PySpark, BigQuery DataFrames). |
| **View vs Table vs Incremental materialization** | View: zero storage cost, always reflects base, instant deploy. Table: fastest reads on repeated queries. Incremental: best of both for >1M-row facts (fast builds, fast reads). | View: slow for repeated complex joins; 50-query dashboard hits 50× view recompute. Table: full rebuild every run, expensive. Incremental: needs on_schema_change logic + dedup handling; more complex model. |
| **dbt exposures for BI lineage vs manual** | Exposures: dashboard/metric → mart lineage visible; docs site shows breakages. | Manual: faster, no config. Exposures: 5–10 min per report YAML entry; must keep in sync. |
| **Generic dbt tests (unique, not_null, accepted_values, relationships) vs custom singular tests** | Generic: 1 YAML line, 1000 tests; zero code. Singular: any arbitrary SQL, catch weird edge cases. | Generic: limited to 4+ macro patterns. Singular: each requires SQL maintenance. |
| **Kimball-style conformed marts vs domain-specific wide tables** | Kimball: reusable across departments, conformed dimensions → one number. Wide tables: per-department fast iteration, no joins needed. | Kimball: upfront modeling cost. Wide tables: metric chaos (5 definitions of revenue) when not tightly governed. |
| **Warehouse-native transformations vs dbt on raw SQL** | Warehouse native (Snowpark Scripts, Databricks Delta Live Tables): tight integration. dbt: cross-warehouse portable + tests/docs/exposures/CI. | Warehouse native: vendor lock-in. dbt: extra layer; some warehouse-native features (streaming, Python UDF) not 1st-class. |

---

## Medallion Architecture — Standard Layers

```
Source Systems (ERP, CRM, IoT, Web analytics, APIs)
        │ Fivetran / Airbyte / CDC / Kafka / custom scripts
        ▼
┌────────────────────────────────────────────────────────┐
│ BRONZE / LANDING (RAW, immutable, append-only)        │
│ - 1:1 mirror of source tables, with ingest metadata   │
│ - `_ingested_at UTC`, `_source_system`, `_file_name`  │
│ - Parquet / Delta / Iceberg; no DDL beyond partitions │
│ - NEVER deleted (retention per data contract)         │
└────────────────────────────────────────────────────────┘
        │ dbt staging models (1:1, typed, deduped)
        ▼
┌────────────────────────────────────────────────────────┐
│ SILVER / CLEANSED / STAGED                            │
│ - Staging models per source: `stg_sap__orders`        │
│ - Typed columns, PKs, natural keys preserved          │
│ - Deduped + soft-delete captured                      │
│ - Null coercion + basic validation (no transforms)    │
│ - Reusable intermediate joins: `int_orders_enriched`  │
└────────────────────────────────────────────────────────┘
        │ Dimension + Fact modeling + business logic
        ▼
┌────────────────────────────────────────────────────────┐
│ GOLD / WAREHOUSE (conformed, 3NF or Data Vault or… )  │
│ OPTIONAL skip: small orgs go Silver→Marts directly.   │
│ Conformed dims + facts once, then join in marts.      │
└────────────────────────────────────────────────────────┘
        │ Business aggregation for a department
        ▼
┌────────────────────────────────────────────────────────┐
│ MARTS / SEMANTIC LAYER  (star schema, per use-case)   │
│ `mart_sales_daily`, `mart_finance_pnl_monthly`        │
│ Consumed by BI dashboards, analysts, reverse ETL,     │
│ ML feature stores                                      │
└────────────────────────────────────────────────────────┘
```

### Layer Boundary Rules
- **Bronze → Silver**: Silver reads *only* Bronze.
- **Silver → Gold/Mart**: Marts read *only* Silver (or Gold). A mart **MUST NOT** read another mart. If two marts share logic, extract it into an intermediate (Silver `int_*`) model.
- **No circular `ref()`** anywhere.

---

## Good Implementation

### Project Layout (dbt / SQLMesh standard)

```
analytics_project/
├── analyses/                  # Ad-hoc analyst SQL, versioned
├── dbt_project.yml            # Model paths, materialization, vars, quoting
├── profiles.yml               # env-var-driven connection profiles; NEVER commit secrets!
├── packages.yml               # dbt_utils, dbt_expectations, codegen, T-SQL/Snowflake dialect
├── macros/
│   ├── custom_schema.sql      # Macro to compute prod/dev schema name
│   ├── generate_surrogate_key.sql
│   ├── grant_select.sql
│   └── tests/                 # Custom generic tests (is_valid_email, etc.)
├── models/
│   ├── staging/
│   │   ├── sources.yml        # Source tables + freshness / tests
│   │   ├── sap/
│   │   │   ├── stg_sap__customers.sql
│   │   │   ├── stg_sap__orders.sql
│   │   │   └── stg_sap.yml    # docs + column tests
│   │   └── salesforce/
│   ├── intermediate/
│   │   ├── int_customers_enriched.sql
│   │   ├── int_order_line_with_reason.sql
│   │   └── intermediate.yml
│   ├── marts/
│   │   ├── core/              # Conformed dimensions and core facts (gold)
│   │   │   ├── dim_customer.sql
│   │   │   ├── dim_product.sql
│   │   │   ├── dim_date.sql
│   │   │   ├── fct_sales_order_line.sql
│   │   │   └── core_schema.yml
│   │   ├── sales/
│   │   │   ├── mart_sales_daily.sql
│   │   │   └── mart_sales_region_monthly.sql
│   │   └── finance/
│   └── utilities/             # Dim date seed, macro helpers
├── seeds/                     # Static lookups: country_codes.csv, gl_account_map.csv
├── snapshots/                 # SCD Type 2 via dbt snapshot (if not handled in staging)
│   └── snap_customers.sql
├── tests/                     # Singular tests: assert_revenue_matches_source.sql
├── docs/                      # Extra markdown docs + overview pages
└── ci/
    └── requirements.txt       # dbt-core, dbt-snowflake pinned versions
```

### Staging Model (Silver)

```sql
-- models/staging/sap/stg_sap__orders.sql
WITH source AS (
    SELECT * FROM {{ source('sap', 'orders') }}
),

renamed AS (
    SELECT
        -- Primary key + natural business keys
        CAST(orderid AS BIGINT)                        AS order_id,
        CAST(kunnr AS BIGINT)                          AS customer_business_key,
        CAST(vbeln AS STRING)                          AS sales_document_number,

        -- Dates (UTC-normalised; source tz converted in source connector)
        CAST(erdat AS DATE)                            AS order_date,
        CAST(erzet AS TIME)                            AS order_time,
        TIMESTAMP_NTZ_FROM_PARTS(CAST(erdat AS DATE), CAST(erzet AS TIME))
                                                       AS order_created_at,

        -- Measures
        CAST(netwr AS DECIMAL(18,2))                   AS net_value_document_currency,
        CAST(waerk AS STRING)                          AS document_currency_code,

        -- Status / categorization
        TRIM(CAST(augru AS STRING))                    AS order_reason_code,
        TRIM(CAST(lfsk AS STRING))                     AS delivery_block_code,
        TRIM(CAST(bukrs AS STRING))                    AS company_code,

        -- Technical audit columns (add, don't remove)
        _file_name                                     AS _source_file_name,
        _line_number                                   AS _source_line_number,
        _ingested_at                                   AS _ingested_at_utc
    FROM source
),

final AS (
    SELECT
        {{ dbt_utils.generate_surrogate_key(['order_id', 'company_code']) }}
                                                       AS order_surrogate_key,
        *,
        CURRENT_TIMESTAMP()                            AS _staged_at_utc
    FROM renamed
)

SELECT * FROM final
```

**Principles:**
- 1:1 with source; no joins, no aggregates. Typing, trimming, renaming, technical metadata only.
- Every staged row has a stable deterministic SK for downstream joins.

### Mart Model (Incremental Fact)

```sql
-- models/marts/core/fct_sales_order_line.sql
{{
    config(
        materialized = 'incremental',
        unique_key   = 'sales_line_surrogate_key',
        on_schema_change = 'sync_all_columns',
        incremental_strategy = 'merge',
        partition_by = {'field': 'order_date', 'data_type': 'date'},
        cluster_by   = ['customer_key', 'product_key'],
        tags         = ['mart', 'fact', 'daily'],
        pre_hook = "{{ delete_insert_overlap(this, 'order_date', -3) }}"
          -- re-process last 3 days of partitions to capture late-arriving facts
    )
}}

WITH order_lines AS (
    SELECT * FROM {{ ref('int_order_line_with_reason') }}
    {% if is_incremental() %}
      WHERE order_date >= (SELECT DATEADD(day, -3, COALESCE(MAX(order_date), '1900-01-01')) FROM {{ this }})
    {% endif %}
),

customers AS (
    SELECT * FROM {{ ref('dim_customer') }}
),

products AS (
    SELECT * FROM {{ ref('dim_product') }}
),

dates AS (
    SELECT * FROM {{ ref('dim_date') }}
),

enriched AS (
    SELECT
        ol.sales_line_surrogate_key,
        COALESCE(c.customer_key, -1)                    AS customer_key,
        COALESCE(p.product_key,  -1)                    AS product_key,
        d.date_key                                      AS order_date_key,
        ol.order_id_degenerate,
        ol.line_number,
        ol.qty_ordered,
        ol.qty_shipped,
        ol.unit_price,
        ol.line_amount_ex_tax,
        ol.line_tax_amount,
        ol.line_cost_amount,
        ol.line_discount_amount,
        ol.is_return_flag,
        ol.order_reason,
        ol.company_code,
        ol._ingested_at_utc,
        ol._staged_at_utc
    FROM order_lines ol
    LEFT JOIN customers c
           ON ol.customer_business_key = c.customer_business_key
          AND ol.order_date BETWEEN c.row_effective_from AND c.row_effective_to  -- SCD2 join
    LEFT JOIN products p
           ON ol.product_business_key  = p.product_business_key
          AND ol.order_date BETWEEN p.row_effective_from AND p.row_effective_to
    LEFT JOIN dates d ON ol.order_date = d.date
)

SELECT * FROM enriched
```

### Documentation & Data Contracts (YAML)

```yaml
# models/marts/core/core_schema.yml
version: 2

models:
  - name: fct_sales_order_line
    description: >
      Transaction-level sales fact. **Grain:** one row per order line per source document
      per company code. Includes booked orders (excl. pre-quotes) from SAP ECC.
    config:
      meta:
        owner: analytics-engineering@societetrager.fr
        sla:   "Daily by 06:30 UTC"
    columns:
      - name: sales_line_surrogate_key
        description: "Hash surrogate PK: `(source_system, order_id_degenerate, line_number)`"
        data_tests:
          - unique
          - not_null

      - name: customer_key
        description: "FK -> dim_customer; -1 if customer unknown at time of ingest."
        data_tests:
          - not_null
          - relationships:
              to: ref('dim_customer')
              field: customer_key

      - name: order_date_key
        description: "FK -> dim_date on order placement date (UTC-normalised)."
        data_tests:
          - not_null
          - relationships:
              to: ref('dim_date')
              field: date_key

      - name: line_amount_ex_tax
        description: "Net line amount in document currency, excluding VAT/Taxes."
        data_type: numeric
        data_tests:
          - not_null
          - dbt_utils.accepted_range:
              min_value: -999999999
              max_value:  999999999
```

### Source Freshness + Contracts

```yaml
# models/staging/sources.yml
version: 2
sources:
  - name: sap
    database: RAW
    schema: SAP_ECC
    loader: Fivetran
    meta:
      owner: data-platform-team
    freshness:
      warn_after:  {count: 12, period: hour}
      error_after: {count: 36, period: hour}
    loaded_at_field: _ingested_at

    tables:
      - name: orders
        identifier: ORDERS_CDC
        columns:
          - name: orderid
            description: "Primary key in source SAP table VBAK."
            data_tests: [not_null]
          - name: netwr
            description: "Net value in document currency."
            data_tests:
              - dbt_expectations.expect_column_values_to_be_of_type:
                  column_type: decimal
```

### Modularity & Reusability
- **Don't Repeat Yourself.** If two staging models share a `currency_exchange_rate` lookup, extract it into a shared `int_*` intermediate, not copy-pasted CASE statements.
- **Expose one business concept per model.** A `mart_sales_daily` model aggregates at day grain only. If an analyst wants weekly, they build on top of it (or it lives in another mart).
- **Use `ref()` everywhere** — never hardcode `database.schema.table` so dev/CI/prod schemas and blue/green deploys work.

### Idempotency
Running the pipeline 1 or 10 times in a row on the same input data:
- Produces the *exact same output* (no extra rows, no duplicate rows, sums match to 1e-6).
- If it fails step 7 of 12, rerun continues from step 8 (or overwrites cleanly).
→ How: `incremental_strategy = 'merge'` with a stable unique key; deterministic SQL (no `CURRENT_DATE()` where `max(date)` from data should be used); no random sort without `ORDER BY` tiebreaker.

---

## Naming Conventions

| Object Type | Pattern | Example |
|-------------|---------|---------|
| Staging model | `stg_<source>__<entity>` | `stg_sap__orders` |
| Intermediate | `int_<business-entity>_<description>` | `int_customer_enriched_with_segment` |
| Dimension | `dim_<entity>` | `dim_customer` |
| Fact | `fct_<business process>_<grain>` | `fct_sales_order_line` |
| Mart | `mart_<department>_<grain>` | `mart_sales_region_monthly` |
| Snapshot | `snap_<entity>` | `snap_sf_account` |
| Singular test | `assert_<model>_<condition>` | `assert_fct_sales_no_duplicate_lines` |
| Macro | `<verb>_<noun>` or `<domain>_<verb>` | `grant_select_on_schemas`, `scd2_valid_ranges` |
| PK column | `<entity>_key` | `customer_key`, `product_key` |
| Business key | `<entity>_business_key` or `bk` | `customer_business_key` |
| Dates in facts | `<event>_date_key` (int smart key YYYYMMDD) or `<event>_date` (DATE) | `order_date_key` |
| Tech columns | prefix `_` to distinguish | `_ingested_at_utc`, `_staged_at_utc`, `_dbt_run_id` |

---

## Dependency Management & Deploy

### dbt Packages (`packages.yml`)
```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.1.0", "<2.0.0"]
  - package: calogica/dbt_expectations
    version: [">=0.10.0"]
  - package: dbt-labs/codegen
    version: [">=0.12.0"]
```

### Tooling Ecosystem by Warehouse
| | Orchestrate | Transform | Test | Catalog/Lineage | Observe |
|--|------------|-----------|------|-----------------|---------|
| **Snowflake** | Dagster, Airflow, dbt Cloud | dbt Core/Cloud, SQLMesh | dbt tests, dbt_expectations | dbt docs, Collibra, Monte Carlo | Monte Carlo, Great Expectations, Elementary |
| **Databricks Lakehouse** | Workflows + dbt, Airflow | Delta Live Tables, dbt-databricks, Spark SQL | dbt, Delta expectations | Unity Catalog lineage, dbt docs, Amundsen/OpenLineage | Datadog + DLT event logs |
| **Fabric / OneLake** | Data Factory pipelines + Fabric Data Pipelines | Dataflow Gen2 + dbt-Fabric, T-SQL SPs | dbt tests, Pipelines assertions | Microsoft Purview + Fabric lineage | Fabric monitoring, App Insights |
| **BigQuery** | Cloud Composer + dbt | dbt-bigquery, Dataform | dbt, dbt-expectations, Dataform assertions | Data Catalog + dbt docs | Elementary, re_data, BigQuery audit logs |

---

## How to Test

1. **Source tests** (contracts on input): `not_null` on PK, `accepted_values` on status codes, `expect_column_values_to_be_of_type`.
2. **Model schema tests**:
   - Every PK: `unique` + `not_null`
   - Every FK: `not_null` (or documented allowed NULL → -1) + `relationships: to ref('dim')`
   - Measures: `accepted_range: min/max`
   - Cardinality: `dbt_utils.unique_combination_of_columns` for composite grains
3. **Singular (business-logic) tests**:
   ```sql
   -- tests/assert_fct_sales_revenue_reconciles.sql
   WITH mart_total AS (
       SELECT SUM(line_amount_ex_tax) AS v FROM {{ ref('fct_sales_order_line') }}
       WHERE order_date >= DATEADD(month, -3, CURRENT_DATE())
   ),
   source_total AS (
       SELECT SUM(netwr) AS v FROM {{ source('sap', 'orders') }}
       WHERE erdat    >= DATEADD(month, -3, CURRENT_DATE())
         AND EXISTS (SELECT 1 FROM {{ source('sap','order_items') }} oi WHERE oi.orderid = orderid)
   )
   SELECT * FROM mart_total, source_total
    WHERE ABS(COALESCE(mart_total.v,0) - COALESCE(source_total.v,0)) > 1.00
   -- if any rows returned, test fails: mart and source diverge by >1€
   ```
4. **Freshness tests**: `dbt source freshness` — fail pipeline if source hasn't landed in SLA window.
5. **Schema drift contracts** (dbt 1.6+ `contract.enforced=true`): if new upstream column is added and not in model YAML → fail build (instead of silently dropping or adding).
6. **CI-only smoke tests**: PR build runs `dbt build --select state:modified+ --exclude tag:full_only` against DEV schema with test data.
7. **Regression tests**: canonical output of 10 core marts saved as seeds; run daily `dbt test` with custom equivalence macro (floats within tolerance).
8. **Tools:** dbt tests + dbt_expectations, Great Expectations, Monte Carlo, Elementary-data, Soda, PipeRider.

---

## Performance Behavior

| Pattern | Credit / Time Cost |
|---------|-------------------|
| Full rebuild 500M-row fact (no incremental) | ❌ 10–20× incremental; 100× warehouse credits vs incremental merge last 3 days |
| Incremental merge + cluster/partition prune | ✅ Minutes; only scan + write changed partitions |
| View-based mart referenced 20× by 20 reports | ❌ 20× recompute per BI dashboard load; materialise as table/incremental |
| Cross joins / unintentional Cartesian in intermediate | ❌ O(n·m) rows; shows up as "query spilled to disk" in profiles |
| dbt `--full-refresh` on entire project | ❌ 2–10× duration; only run on schema-breaking changes |
| Materialized intermediate models reused by 5+ marts | ✅ Compute once, reuse 5× |
| Jinja `for` loop generating 20 CTEs from list | ✅ Smaller SQL file; no runtime cost (dbt renders once at compile time) |
| SCD2 `BETWEEN` join without `equi-predicate` | ⚠️ Nested-loop-join cost; add equi-partition on year + hash join |
| Cluster / sort keys misaligned to common queries (order by country on a date-filtered fact) | ❌ 5–20× slower on date-range queries; prune doesn't work |

### Optimization Order of Operations
1. Make models incremental (biggest win).
2. Partition + cluster / sort keys aligned to top WHERE predicates.
3. Break giant 1000-line model into intermediate materialized steps → optimizer sees smaller queries.
4. Avoid anti-patterns: unnecessary DISTINCT, `SELECT *`, scalar UDFs on large columns.
5. Warehouse-specific: Snowflake query acceleration, warehouse sizing match to workload; Databricks Photon + Z-order.

---

## What to Inspect First (Wrong Numbers / Late Pipeline)

1. **Source freshness** — `dbt source freshness`: did source data stop landing 14 hours ago? → Pipeline shows yesterday's data; not a bug in your model.
2. **Model tests failing?** If `relationships` test fails on customer_key, then numbers are wrong because 2% of rows went to `-1` unknown key.
3. **Incremental filter is too narrow / too wide?** Did last 3 days become last 0 days (bug in DATEADD) → missing late facts; or last 365 days → rebuild entire fact every run.
4. **SCD2 join** — Are you joining fact to dim `ON customer_business_key` *without* the `BETWEEN effective_from/to` clause? Today's segment applied to historical sales.
5. **Cross-schema ref** — Does a dev model accidentally `ref()` a PROD-only table they hardcoded instead of using {{ source() }}? → Numbers look great in dev, missing in CI.
6. **Schema drift** — Source added / removed column; `on_schema_change = 'ignore'` silently dropped it → mart has 0s everywhere new col should be.
7. **Late-arriving facts + window dedup** — Incremental run selected `max(order_date)` but a late-arriving correction with earlier `order_date` arrived after that date range was processed; fix `pre_hook` reprocess window to ≥ max expected lateness.
8. **dbt run-order issue / missing dependencies** — Model A depends on B but no `ref()` → B wasn't rebuilt in today's run; use `dbt ls --select +A --output name` to see dependency chain.
9. **Currency conversion applied twice** — once in staging (to USD), once in mart (to EUR) with outdated exchange rates → amounts inflated by 1.08×.
10. **Timezone bugs** — Source system in Africa/Libreville (WAT UTC+1); pipeline converts to UTC but dashboard displays as-is → daily cutoff appears at 11pm local, not midnight.

---
