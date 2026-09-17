# Data Modeling Reference Guide (Analytics)

## When Used
Data modeling is the **foundation of every analytics system**. Apply it when:
- Designing (or refactoring) a warehouse, lakehouse, data mart, or semantic model
- Onboarding a new business domain (sales, inventory, HR, logistics) into analytics
- Defining the shape of tables to be used by analysts, BI tools, or ML feature stores
- Choosing between denormalization for speed vs normalization for flexibility
- Determining what needs to be historically tracked (SCD) vs overwritten
- Re-structuring data after a source-system change

## When NOT Used
- **Raw / bronze landing zone design** — raw should mirror source exactly; don't model, just land with metadata + ingest timestamp
- **Transient intermediate step in a pipeline** — temporary staging tables don't need formal modeling discipline
- **OLTP application schema design** — normalization (3NF) is correct for write performance; analytics reads need a different approach
- **Low-volume departmental spreadsheets** — Excel table structure is fine; formal DW modeling is overkill for <10k rows
- **Pure data-science feature engineering** — wide denormalised feature matrices, one-hot encodings, etc., are consumed by models not humans; follow ML conventions not Kimball

---

## Common Mistakes

1. **Fact table without a declared grain** — "What does one row of this fact represent?" If the answer is vague (e.g., "sales stuff"), joins will explode duplicates. *Write the grain statement down.*
2. **Mixing grains in one fact table** — an "Order + Order Line + Shipment" fact is unusable; split into separate fact tables at their own grains (use `dim_order` degenerate dimension or a bridge if you must correlate).
3. **Null foreign keys in a fact row** — `customer_key = NULL` for unknown breaks BI tool joins → use the **Unknown/NA dimension row** (e.g., `customer_key = -1`, name="Unknown Customer").
4. **Using natural keys as primary dimension keys** — source system keys change (mergers, data fixes, re-imports); always use **surrogate keys** (integers or hash) in dimensions.
5. **SCD Type 1 when history was needed** — marketing needs "what segment was this customer in *at time of sale*?" but you overwrote the segment every refresh → irrecoverable information loss.
6. **SCD Type 2 when simple Type 1 is fine** — every tiny address typo fix spawns a new row → dimension doubles in size, analysts get wrong counts; track SCD *only on columns that matter*.
7. **Bi-directional / many-to-many relationships by accident** — Power BI auto-detect creates a bidirectional filter → silent double-counting in visuals; declare cardinality explicitly and mostly single-direction.
8. **Date dimension with datetime-to-minute grain** — your 100M-row date dim blows up Vertipaq; one row per day (365 × 100 years ≈ 36k rows) is correct; intra-day time goes in a separate `dim_time` or as fact columns.
9. **No role-playing date dimensions** — fact has `order_date`, `ship_date`, `invoice_date`, but only one `dim_date` active relationship → measures with `USERELATIONSHIP()` all over the place (acceptable) or worse, 3 physical copies of dim_date (not acceptable).
10. **"One big table" anti-pattern (OBT)** — a single 200-column denormalised table for an entire department: no joins, but impossible to maintain, every refresh is massive, every report scans all 200 cols; only viable for small single-purpose exports.
11. **Ignoring semi-additive facts** — `SUM(Inventory[QtyOnHand])` across January + February double-counts inventory that existed both months; snapshot facts demand Last/Max aggregations across time, *not* SUM.
12. **Facts with too many low-cardinality flags stored as columns** — 30 "is_xxx" columns compress OK in columnar, but a `dim_sale_type` dimension (16 rows) + foreign key compresses better and is query-friendlier.

---

## Trade-offs

| Decision | Advantages | Disadvantages |
|----------|-----------|---------------|
| **Star Schema (Kimball)** | Simple, fast reads, fewer joins, universally understood by BI tools and analysts. Agile: add a dimension without breaking existing reports. | Denormalized → storage cost; ETL must propagate type-2 changes; some redundancy. History-tracking design choices are per-dimension. |
| **Snowflake Schema** | Normalised dimensions → less storage, easier 3NF integration with master data. | 3+ joins per query → slower on some engines; analysts struggle with path choices; DAX/BI auto-exists breaks across snowflake levels. |
| **Data Vault 2.0** | Audit-able history of *everything*, scalable ingestion parallelism, source-system agnostic Hubs/Satellites/Links; great for enterprise + regulated industries. | Steep learning curve; 3× more tables; requires a downstream Business Vault + marts layer (Kimball-style) *before* analysts can query. Adds 6–18 months build-out vs Kimball-only. |
| **Inmon 3NF EDW + Data Marts** | Single integrated source for all corporate facts; strong data governance for shared master data. | Huge up-front modeling cost. Slow delivery of first mart ("boil the ocean"). Rebuilding the EDW if a source changes is painful. |
| **One Big Table (OBT)** | Fastest possible single-table reads on columnar warehouses. No joins → BI tools rarely struggle. | Inflexible. ETL = rewrite OBT on every dimension change. No reusability across departments. Column count grows unbounded (some warehouses struggle >500 cols). |
| **Surrogate Keys (int vs hash)** | Integer SKs: 4 bytes, tiny, fast joins. Hash SKs: no central ID generator; can be computed from natural key in parallel ETLs; merge across systems without collision. | Int SKs: need to be generated sequentially (bottleneck) or in ranges. Hash: 16/32 bytes per join key → larger memory footprint in BI semantic models. |
| **Type 1 vs Type 2 on attribute X** | Type 1: 1 row per entity, small dims, no date-range logic needed in queries. Type 2: full history, "as-was" reporting. | Type 1: can't answer "what segment was they in at sale?". Type 2: inflates dim size, requires BETWEEN join or `effective_end_date` handling in measures. |
| **Snapshot vs Transaction fact** | Transaction fact: smallest footprint, answers any "when did X happen?" question with any date math. Snapshot fact (daily/weekly): pre-aggregated to one row per entity per period → super-fast "state of business on day X" questions. | Transaction fact: computing "inventory on day 365" is expensive (cumulative sum). Snapshot fact: explosive growth (365 days × 1M items = 365M rows/yr) and you cannot ask about intra-period events. |
| **Conformed dimensions vs silo per mart** | Conformed: "Customer" means the same in Sales mart as in Service mart → cross-mart joins work, single ETL, single definition of "active customer". | Silo: fastest per-mart delivery, no need to align teams. Long-term, produces metric chaos (5 definitions of "active customer" in 4 marts). |

---

## Core Concepts

### Fact Tables

A fact table row corresponds to a **business event or measurement**.

| Type | Grain | Example | Common Facts |
|------|-------|---------|--------------|
| **Transaction Fact** | One row per event, at the lowest operational detail | `fct_sales_line` | qty, unit_price, line_amount, cost_amount, is_return, discount_amount |
| **Periodic Snapshot Fact** | One row per entity × per period (day/week/month) regardless of activity | `fct_inventory_daily_snapshot` | qty_on_hand, qty_reserved, qty_in_transit |
| **Accumulating Snapshot Fact** | One row per workflow entity; updated as milestones are reached | `fct_order_fulfillment` | order_date_key, ship_date_key, deliver_date_key, invoice_date_key; days_to_ship, days_to_deliver |
| **Factless Fact Table** | Only keys (no measures); captures event occurrence | `fct_student_attendance` | date_key, course_key, student_key, present_flag (the flag is tiny, but you may have none) |

**Naming:** `fct_<business domain>_<grain>` — e.g., `fct_sales_order_line`, `fct_finance_gl_journal_line`.

**Fact table primary key:** Composite of all FKs + degenerate dim where applicable, OR a single meaningless hash/surrogate `fact_key` for incremental update idempotency. *Do not depend on a composite PK in downstream BI — use a single fact_key column to facilitate upsert.*

### Dimension Tables

Dimensions answer the **"who, what, where, when, why, how"** of a fact. They are wide, descriptive, typically slowly changing, and joined to facts via a single-column key.

**Naming:** `dim_<entity>` — e.g., `dim_customer`, `dim_product`, `dim_date`, `dim_employee`.

**Required columns on every dimension:**
- `<entity>_key INT/BIGINT`: surrogate key (never NULL; -1 for unknown)
- `<entity>_id / business_key`: natural key from source
- `row_effective_from DATETIME2`, `row_effective_to DATETIME2`, `is_current BOOLEAN` (for SCD Type 2)
- `created_at DATETIME2`, `updated_at DATETIME2`
- Descriptive attributes: `customer_segment`, `product_category`, `country_name`, `is_active`

#### Surrogate vs Natural Keys
```
✅ Preferred: Surrogate integer key → dim_customer.customer_key = 42
  Why? Source merges / UUID changes → update business_key in ONE dim row; all historical facts remain joined.
❌ Avoid: Natural key as dimension PK → if source changes ID for same customer, you can't re-map historical facts.
```

### Date Dimension (Always Separate)

One row per calendar day, 50–100 descriptive columns. Always materialize it; never rely on `DATE_TRUNC`/`DATENAME` at query time for fiscal/holiday logic.

```sql
CREATE TABLE mart.dim_date (
    date_key                INT         PRIMARY KEY,   -- 20240115 (smart key: YYYYMMDD)
    date                    DATE        NOT NULL UNIQUE,
    day_of_week             TINYINT,
    day_name                VARCHAR(10),
    day_of_month            TINYINT,
    day_of_year             SMALLINT,
    week_key                INT,                      -- 202403
    iso_week_of_year        TINYINT,
    month_key               INT,                      -- 202401
    month_name_short        CHAR(3),
    month_name              VARCHAR(15),
    quarter_key             INT,
    quarter_name            CHAR(2),                  -- "Q1"
    year                    SMALLINT,
    fiscal_year             SMALLINT,
    fiscal_quarter          TINYINT,
    fiscal_period           VARCHAR(7),               -- "FY2025-P01"
    is_weekend              BOOLEAN,
    is_holiday_country_xx   BOOLEAN,
    is_working_day          BOOLEAN,
    relative_days_from_today INT                      -- -1 yesterday, +1 tomorrow; refreshed daily
);
-- Index / cluster on (year, month_key) for BI partition pruning.
```

**Role-playing dates:** In the semantic model, create inactive relationships from the fact's different date columns to *the same* `dim_date`. Use `USERELATIONSHIP(fct[ship_date_key], dim_date[date_key])` in ship-date measures.

### SCD Types (Slowly Changing Dimensions)

| Type | Behavior | Example Use | Implementation |
|------|----------|-------------|----------------|
| **SCD 0** — Never change | Static reference data that can't change | `dim_country` (ISO country code) | Initial load only. |
| **SCD 1** — Overwrite | Current state only; no history | Customer `phone_number`, `email` (for contact, not for historical segmentation) | `MERGE` update in place. |
| **SCD 2** — Add new row with date range | Need "as-was" reporting | Customer `segment`, `territory`, `tier`; Product `category`, `list_price` | `UPDATE old row_effective_to = now(), is_current=false; INSERT new row with from=now, to=9999-12-31, is_current=true; same business_key.` |
| **SCD 3** — Add "previous value" column | Only last + prior history needed | Account `manager_previous` | `ALTER TABLE ADD col_previous; UPDATE on change`. (Use sparingly.) |
| **SCD 4** — History-only mini-dimension + Type 1 current | Huge attribute churn / rapid changes tracked separately | Customer `risk_score` recalculated hourly → `dim_customer_risk_history` with (customer_key, as_of_date, score) + `dim_customer.current_risk_score` type 1 | Separate history table; join with fact's date if needed. |
| **SCD 6** — Hybrid Type 1 + 2 + 3 | Historical row for changes + additional type-1 "current value" column + previous column | Product category history preserved *and* current category always at hand | Type 2 rows + `category_current` type-1 column updated on every row |

**Decision shortcut:** For each attribute, ask the stakeholder: *"Do you ever need to report as-if this attribute was its old value at time of transaction?"* If yes → Type 2; no → Type 1. 95% of analytics use cases are Type 1 or Type 2.

### Grain Statement

Before writing DDL, write it down:
> "One row in `fct_sales_order_line` represents **one line on one order** in the source ERP system. A line is uniquely identified by (source_system, order_id, line_number). We include orders of status 'booked' and above; quotes and deleted orders are excluded."

If you can't write this sentence, you haven't defined the model yet.

---

## Good Implementation (Star Schema Example)

### Tables + Relationships

```
dim_date (PK: date_key)
dim_customer (PK: customer_key)
dim_product  (PK: product_key)
dim_store    (PK: store_key)
dim_promotion(PK: promotion_key)
dim_order    (PK: order_id_degenerate)   -- degenerate; no attributes beyond key

fct_sales_order_line (
    sales_line_key          BIGINT PK,     -- meaningless SK; for upsert idempotency
    order_date_key          INT NOT NULL REFERENCES dim_date,
    ship_date_key           INT NOT NULL REFERENCES dim_date,  -- role-playing dim
    customer_key            BIGINT NOT NULL REFERENCES dim_customer,
    product_key             BIGINT NOT NULL REFERENCES dim_product,
    store_key               BIGINT NOT NULL REFERENCES dim_store,
    promotion_key           BIGINT NOT NULL REFERENCES dim_promotion,
    order_id_degenerate     VARCHAR(40) NOT NULL,
    line_number             INT NOT NULL,
    qty_ordered             DECIMAL(18,4),
    qty_shipped             DECIMAL(18,4),
    unit_price              DECIMAL(18,4),
    line_amount_ex_tax      DECIMAL(18,2),
    line_tax_amount         DECIMAL(18,2),
    line_discount_amount    DECIMAL(18,2),
    line_cost_amount        DECIMAL(18,2),
    is_return_flag          BOOLEAN,
    source_system           VARCHAR(20),
    ingestion_batch_id      INT,
    created_at              DATETIME2 DEFAULT SYSUTCDATETIME()
)

-- UNIQUE constraint mirrors the grain statement:
ALTER TABLE fct_sales_order_line
  ADD CONSTRAINT uk_sales_line_nat
  UNIQUE (source_system, order_id_degenerate, line_number);
```

### Bridge Table for Multi-Valued Dimensions

When one fact row maps to many dimension rows (e.g., one sale attributable to multiple sales reps):

```
-- Bridge: one fact row → N sales rep keys, weighted
fct_sales_line_rep_bridge (
    sales_line_key  BIGINT REFERENCES fct_sales_order_line(sales_line_key),
    rep_key         BIGINT REFERENCES dim_employee(employee_key),
    allocation_pct  DECIMAL(5,4) NOT NULL,   -- must sum to 1 per sales_line_key
    PRIMARY KEY (sales_line_key, rep_key)
)
```
→ In DAX, use `SUMX(bridge, bridge[allocation_pct] * RELATED(fct[line_amount]))`. *Do not double-count by joining directly to dim_employee from fact without allocation.*

### Accumulating Snapshot for Workflows

```sql
CREATE TABLE mart.fct_order_fulfillment (
    order_id_degenerate     VARCHAR(40) PRIMARY KEY,
    customer_key            BIGINT NOT NULL,
    order_date_key          INT NOT NULL,
    book_date_key           INT,            -- NULLable milestones
    pick_date_key           INT,
    ship_date_key           INT,
    deliver_date_key       INT,
    invoice_date_key        INT,
    return_date_key         INT,
    total_order_amount      DECIMAL(18,2),
    days_order_to_ship      AS (DATEDIFF(day, order_date_key, ship_date_key)),  -- persisted calc
    days_ship_to_deliver    AS (DATEDIFF(day, ship_date_key, deliver_date_key)),
    fulfill_status          VARCHAR(20) NOT NULL,  -- "Booked", "InTransit", "Delivered", "Returned"
    last_updated_at         DATETIME2
);
```
→ Updated every pipeline run as milestones happen. Great for average-cycle-time KPIs.

### Degenerate Dimensions (DD)

High-cardinality dimension columns that have no other attributes (just a number/ID), so they live in the fact table (no dimension table). Example: `order_id_degenerate`, `ticket_number`, `invoice_number`. Use for drill-through, `DISTINCTCOUNT`, but *don't* create a 100M-row `dim_order` just to hold the key.

### Junk Dimensions

When a fact has 20+ low-cardinality flags (`is_gift`, `shipping_method`, `payment_type`, `channel`, `promo_channel`, `is_international`…), consolidate all combinations into a junk dimension:

```
dim_order_flags (
    order_flags_key   INT PK,
    is_gift           BOOLEAN,
    shipping_method   VARCHAR(20),
    payment_type      VARCHAR(20),
    sales_channel     VARCHAR(20),
    is_international  BOOLEAN
    -- one row per combination actually seen in data
)
```
→ Replaces 5 FKs + 15 columns in the fact with 1 FK column. Shrinks fact size on disk.

---

## Cardinality, Filter Direction, and Semi-Additivity

### Relationship Cardinality (Semantic Model / TMDL)
- **Fact → Dimension (95% of cases):** `Many-to-One (*:1)`, single direction (fact filters through dim, dim never filters fact unless explicit).
- **Dimension → Dimension:** Rare. Use only for snowflake when truly required. Generally denormalize into single dimension instead.
- **Many-to-Many:** *Not* a replacement for modeling. Use only when you have a bridge table with allocation, and you know what you're doing.
- **1:1:** Used for slowly changing mini-dim split. E.g., `dim_customer_core` (1 row per customer) → `dim_customer_risk_current` (1 row per customer). Single-direction FK from the core fact model.

### Semi-Additive Facts

A measure that is additive across **some but not all dimensions**:
- Inventory snapshot: `SUM(qty_on_hand)` across products → OK. `SUM(qty_on_hand)` across dates → wrong (double counts same item across months).
- Account balance: `SUM(balance)` across accounts → OK. `SUM(balance)` across months → wrong.

**Correct aggregation strategy:**
- Dimensions you CAN sum across: `SUM()`
- Date/Time dimension you CAN'T sum across: Use `LASTNONBLANKVALUE('Date'[Date], [Raw Balance])` per account, then sum the per-account latest values.

### Conformed vs Non-Conformed Measures

A measure is **conformed** if its formula and the dimensions it uses have *identical meaning* in every mart it appears in. `[Revenue]` in Sales mart should equal `[Revenue]` in Customer mart when sliced by conformed dimensions.

When to allow non-conformed measures (very sparingly):
- Department-specific shorthand: e.g., Finance reports "Adjusted Revenue" with some reclassification. Name it explicitly: `[Adjusted Revenue Finance]`, not `[Revenue]`. Don't silently redefine.

---

## Kimball vs Inmon vs Data Vault: Which to Pick?

| Methodology | Best For | Rough Build Timeline | Queryable By Analysts |
|-------------|----------|---------------------|----------------------|
| **Kimball (Star Marts)** | 95% of mid-size companies; agile delivery; first mart in weeks; BI-team-led. | First mart 2–6 weeks. Enterprise coverage 6–24 months depending on domains. | ✅ Yes, directly on the marts. |
| **Data Vault 2.0** | Large regulated enterprises (pharma, banking, insurance); multi-source; strong audit; need to replay every business key change ever. Downstream Business Vault + Kimball marts still required. | First usable mart 6–18 months. Full EDW-scale 18–36 months. | ❌ Raw/Hub-Link-Sat is for engineers only. Business Vault + Marts layer required. |
| **Inmon (3NF EDW + Dependent Marts)** | Giant corporates with strong central governance. Enterprise-wide single integrated version of data. | First mart 6–18 months. Full EDW-scale multi-year. | ⚠️ Analysts query data-marts (Kimball) sitting on top of 3NF EDW. Never query 3NF directly. |

**Pragmatic guidance for most teams (SeTRAG-size):**
1. Raw/bronze: parquet files, mirror source, no modeling.
2. Silver: lightly cleansed, typed, deduplicated; 3NF-ish integration if multiple sources share entities.
3. Gold/Marts: **Kimball star schemas**. One star per business process. Delivered via dbt/SQLMesh.
4. Semantic layer (Fabric/Power BI dataset): Star schema imported; add DAX measures, calc groups, RLS.

---

## How to Test a Data Model

1. **Grain test** — `SELECT natural_key_cols, COUNT(*) FROM fact GROUP BY natural_key_cols HAVING COUNT(*) > 1` → should return 0 rows.
2. **Referential integrity** — Anti-join: rows in fact where dimension row is missing (must only hit the -1 unknown row, count should match documented %).
3. **Unknown row present** — Every dimension has `key=-1` with `name='Unknown'`.
4. **No NULL FKs** — `SELECT COUNT(*) FROM fact WHERE any_fk IS NULL` → 0; use -1.
5. **Date range integrity (SCD 2)** — Per business key: no gaps, no overlaps, exactly 1 `is_current=true` row.
6. **Semi-additive total sanity** — Day-end inventory sum should equal `SUM(qty_on_hand) WHERE date=last_day`. Compute both and diff.
7. **Source↔mart reconciliation** — For a given transaction date: sum(source.amount) within 0.01 of sum(mart.amount). Fail pipeline on drift > threshold.
8. **Cardinality test in BI semantic model** — Tabular Editor "Analyze Model" → relationship cardinality check; no auto-detected "many-to-many" unless intentional.
9. **Cross-filter path test** — Issue 10 canonical queries (sales by region YTD, inventory by product class end of last month) and compare vs source-of-truth reports.
10. **Longitudinal test** — Rebuild 6 months of marts from backup; assert 2024-03 totals identical between fresh rebuild and 6-month-old persisted mart (determinism).

---

## Performance Behavior (Modeling Choices → Query Speed)

| Modeling Decision | Query Cost Impact |
|-------------------|-------------------|
| Star (2–4 joins per query) | ✅ Optimizer picks perfect hash joins every time; 99th-percentile fast. |
| Snowflake (6–10 joins) | ⚠️ Optimizer has exponential join-order space; can pick wrong plan; 2–5× slower on complex reports. |
| 150-column wide OBT | ✅ Fastest reads (zero joins). ❌ But refresh 2–10× slower; scan cost per query is higher (more columns). Columnar warehouses mitigate. |
| Fact partitioned + clustered by `(date_key, store_key)` | ✅ 10× faster date-range queries; zone-map pruning works. |
| Smart date key (YYYYMMDD INT) vs actual DATE column | ⚠️ Same join speed; smart key makes BETWEEN ranges a bit more explicit in ETL. |
| High-cardinality degenerate dimension in fact | ✅ `DISTINCTCOUNT(order_id)` is fast; no join needed. |
| SCD 2 with millions of rows (over-used) | ❌ Dim scan cost increases; BI FE needs to compute "effective date" joins → slower. Prefer Type 1 where you can. |
| Junk dimension for 20 flags | ✅ Smaller fact row → more rows per page; fewer column reads. |
| Bridge table (M2M) without allocation pct | ❌ Fact row counted N times per bridge entry; silent double-count. |

---

## What to Inspect First (Wrong Numbers in Reports)

1. **Grain violation?** — Print a report that returns a duplicate; trace back to natural key; often grain statement was wrong.
2. **SCD type mismatch.** — Did business *need* Type 2 on `segment` but it was implemented as Type 1? → Current segment being applied to historical sales.
3. **Semi-additive fact summed across dates.** — Inventory/balance doubled. Fix measure, not model (unless model's grain is wrong).
4. **Role-playing date using wrong relationship.** — "Ship revenue" measure accidentally uses `order_date_key` active relationship → numbers off by average ship lag.
5. **M2M bridge missing allocation %.** — Sales attributed to 2 reps → 200% total.
6. **Bi-directional filter enabled.** — A slicer on dim is filtering fact; fact then filters unrelated dim via bidirectional → huge numbers wrong in other visuals on same page.
7. **Date table not contiguous.** — Fiscal calendar missing a leap-year day; time intelligence functions silently drop a week.
8. **Snowflake path ambiguity.** — Product → SubCategory → Category relationship path chosen vs direct shortcut dimension → totals differ.
9. **Degenerate dimension treated as real dim.** — You created `dim_order` with 100M rows joined on order_id → massive join cost + Vertipaq memory. Drop the dim, keep the key in fact.
10. **Unknown row (-1) not set.** — 2% of fact rows have NULL customer_key and those are silently excluded in BI joins (because NULL != NULL); totals 2% lower than expected. Add the -1 row + map facts to it.

---
