# Python Reference Guide (Analytics Engineering)

## When Used
Python is the **swiss-army runtime** for analytics when SQL alone is insufficient:
- **Custom transformations** — regex parsing, fuzzy matching, NLP tokenization, image metadata extraction
- **ML / statistics** — scikit-learn, statsmodels, Prophet, XGBoost, PyTorch training and inference
- **Complex ETL orchestration** — Dagster, Airflow operators, custom connectors for exotic sources
- **Data validation & contracts** — Great Expectations, Pandera, custom schema assertions
- **DataFrames at scale** — Polars (single-node) or PySpark/Glow (cluster) when warehouse SQL is limited
- **CLI tools & scaffolding** — project generators, backfills, one-off migrations
- **Visualization & notebooks** — exploratory analysis in Jupyter, Matplotlib, Plotly, Altair
- **APIs serving analytics** — FastAPI endpoints for dashboard embedding, model scoring

## When NOT Used
- **Structured columnar transformations that SQL does well** (JOIN/GROUP BY/WINDOW on warehouse data) — paying serialization cost for no gain
- **Ultra-low-latency OLTP queries** (<10ms) — use compiled languages or specialized databases
- **Memory-constrained environments with >100× data over RAM** — use warehouse-SQL/Spark, not Pandas
- **GUI/desktop applications** — use C#, Electron, Swift; Python is suboptimal for UI latency
- **Mobile or embedded** — Python interpreters add 50MB+ overhead
- **Billing-critical financial transactions** — strict ACID semantics better expressed in stored SQL procedures

---

## Common Mistakes

1. **Mutable default arguments** — `def f(x=[]): x.append(1)` → state leaks across calls. Use `None` + init.
2. **`pandas` row-by-row `apply` / `iterrows`** — 100×–1000× slower than vectorized methods; CPU bound in Python bytecode
3. **`SELECT *` + `read_sql` without column pruning** — wastes memory and transfer; pass explicit column list or pushdown predicate
4. **Ignoring `SettingWithCopyWarning`** — chained indexing `df[df.x > 0]['y'] = 1` may or may not mutate; use `.loc[row, col] = val`
5. **`np.matrix` instead of `np.ndarray`** — deprecated, confusing operator semantics; always use `ndarray` with `@` for matmul
6. **Hardcoding paths** — `C:\Users\me\data.csv` breaks for teammates; use `pathlib.Path(__file__).parent / "data.csv"`
7. **Broad `except:` catches** — swallows `KeyboardInterrupt`, `SystemExit`; catch specific exceptions, never bare `except`
8. **Committing secrets in `.py` or `.env`** — `API_KEY = "sk-..."`; use `python-dotenv` + key vault + `.gitignore`
9. **Not pinning transitive dependencies** — `requirements.txt` with no versions → different behaviour on every machine; use `pip-tools`, `poetry.lock`, or `uv.lock`
10. **Using notebooks as deployment artifacts** — `.ipynb` cannot be version-diffed, CI-tested, or imported; convert pipeline logic to `.py` modules
11. **`inplace=True`** — makes functions non-composable, hides behaviour, and can fail silently on views; prefer assignment `df = df.foo()`
12. **Silent `NaN` propagation** — `df.mean()` on sparse numeric columns can silently skip entire cohorts; check `.isna().sum()` first

---

## Trade-offs

| Decision | Advantages | Disadvantages |
|----------|-----------|---------------|
| **Pandas vs Polars** | Pandas: ubiquitous, 15y ecosystem, books/docs | Polars: 5–50× faster, less RAM, streaming, lazy API. Pandas: slower, high-watermark RAM, eager-only |
| **Pandas vs PySpark** | Pandas: zero-setup, local iteration, rich APIs | Spark: scales to TB+ on clusters, SQL + Python UDF interchange. Pandas: single-machine only |
| **`venv` vs Poetry vs PDM vs Rye/uv** | `venv`: stdlib, no install. Poetry: lockfile + publish + groups out of box. | `venv`: no lock, manual pip-compile. Poetry: slower resolver. uv/rye: fastest but newest ecosystem |
| **Type hints on vs off** | Catch bugs pre-runtime, better IDE autocomplete, self-documenting | 5–20% more code; runtime enforcement needs mypy/pyright |
| **Notebook (.ipynb) vs Script (.py)** | Iterative exploration, inline charts, markdown narrative | Hard to diff, non-linear execution, not importable/CI-able |
| **`requests` vs HTTPX vs urllib** | `requests`: idiomatic, universally known. HTTPX: async, HTTP/2. | `requests`: sync-only. urllib: stdlib, verbose APIs. |
| **SQLAlchemy ORM vs raw SQL** | ORM: typed composable queries, DB-portable, migrations via Alembic | Raw SQL: faster to author for complex analytics, optimizer-transparent. ORM: learning curve, overhead |
| **pytest vs unittest** | pytest: plain `assert`, fixtures, parametrize, rich plugins | unittest: stdlib, no install. pytest needs `pip install pytest` |
| **Logging vs print()** | Structured levels, timestamps, sinks (file/JSON/cloud), filterable | print: fastest, but zero context, never disableable in prod |
| **FastAPI vs Flask/Django** | FastAPI: async-first, typed, auto-OpenAPI, pydantic validation | Flask: minimal, biggest plugin ecosystem. Django: batteries-included ORM/admin. FastAPI: newer, smaller ecosystem |

---

## Good Implementation

### Project Structure (Standard Layout)

```
analytics_project/
├── README.md
├── pyproject.toml          # deps, build config, tooling (ruff, mypy, pytest)
├── uv.lock / poetry.lock   # EXACT pinned transitive deps
├── .env.example            # required env vars, secrets redacted
├── .gitignore              # __pycache__, .env, *.parquet, .pytest_cache
├── src/
│   └── mypackage/
│       ├── __init__.py     # public API re-exports
│       ├── cli.py          # click/typer entrypoint
│       ├── config.py       # pydantic Settings / env vars
│       ├── logging_.py     # logging dictConfig
│       ├── io/
│       │   ├── sources.py  # warehouse/S3/API readers
│       │   └── sinks.py    # writers
│       ├── transforms/
│       │   ├── cleaning.py
│       │   ├── features.py
│       │   └── validate.py
│       └── models/
│           └── scoring.py
├── tests/
│   ├── conftest.py
│   ├── fixtures/           # tiny CSV/Parquet test fixtures
│   ├── test_cleaning.py
│   └── test_validate.py
├── notebooks/              # exploratory ONLY; never import src from here via sys.path hack
│   └── 2024-01-eda.ipynb   #   → install project as editable (pip install -e .)
└── docs/
```

### Environment & Dependencies

```toml
# pyproject.toml
[project]
name = "mypackage"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "polars>=0.20.0,<1",
    "pydantic>=2.5",
    "pydantic-settings>=2",
    "click>=8",
    "python-dotenv>=1",
    "structlog>=24",
    "sqlalchemy>=2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-cov>=5",
    "hypothesis>=6",
    "ruff>=0.2",
    "pyright>=1.1",
    "pre-commit>=3",
]
ml = ["scikit-learn>=1.4", "xgboost>=2"]
viz = ["matplotlib>=3.8", "plotly>=5.18"]

[project.scripts]
mypackage = "mypackage.cli:main"

[tool.ruff]
target-version = "py311"
line-length = 100
[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "SIM", "RUF"]

[tool.pytest.ini_options]
addopts = "-ra --strict-markers --cov=src/mypackage --cov-fail-under=80"
```

### Secrets & Config (Never Commit Secrets)

```python
# mypackage/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    warehouse_conn_str: str            # required; blows up if missing
    api_base_url: str = "https://api.internal/v1"
    api_key: str | None = None         # optional for dev
    log_level: str = "INFO"
    feature_store_bucket: str = "s3://analytics-feature-store"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### Type Hints & Composable Functions

```python
# mypackage/transforms/cleaning.py
from __future__ import annotations
from datetime import date
import polars as pl
from typing import Iterable

REQUIRED_COLUMNS: tuple[str, ...] = (
    "order_id", "customer_id", "order_date", "status", "amount",
)

VALID_STATUSES: frozenset[str] = frozenset({
    "pending", "completed", "cancelled", "refunded",
})

def validate_schema(df: pl.DataFrame) -> pl.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return df

def clean_orders(
    df: pl.DataFrame,
    start_date: date | None = None,
    end_date: date | None = None,
) -> pl.DataFrame:
    """Dedup, filter, and type-check raw orders. Deterministic: same in → same out."""
    return (
        df.pipe(validate_schema)
          .with_columns(
              order_date=pl.col("order_date").cast(pl.Date, strict=False),
              amount=pl.col("amount").cast(pl.Float64, strict=False).round(2),
          )
          .filter(
              pl.col("order_date").is_not_null(),
              pl.col("amount").is_not_null() & (pl.col("amount") >= 0),
              pl.col("status").is_in(VALID_STATUSES),
          )
          .pipe(lambda d: d.filter(pl.col("order_date") >= start_date) if start_date else d)
          .pipe(lambda d: d.filter(pl.col("order_date") <= end_date)   if end_date   else d)
          .unique(subset=["order_id"], keep="last")    # dedup by key
    )

def revenue_by_segment(orders: pl.DataFrame, customers: pl.DataFrame) -> pl.DataFrame:
    """Enriched revenue aggregation. Uses lazy-style chaining for composability."""
    return (
        orders
        .join(customers, on="customer_id", how="inner")
        .group_by("segment", "country")
        .agg(
            order_count=pl.len(),
            revenue=pl.sum("amount"),
            avg_order_value=pl.mean("amount"),
        )
        .with_columns(
            revenue_share_pct=(pl.col("revenue") / pl.sum("revenue") * 100).round(2)
        )
        .sort("revenue", descending=True)
    )
```

### Logging (Structured JSON in Prod)

```python
# mypackage/logging_.py
import logging
import structlog
from .config import get_settings

def setup_logging() -> None:
    settings = get_settings()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.ExceptionPrettyPrinter() if settings.log_level == "DEBUG"
                else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        cache_logger_on_first_use=True,
    )

# Usage anywhere:
# log = structlog.get_logger(); log.info("pipeline_started", table="orders", rows=len(df))
```

### Exceptions (Rich, Categorised)

```python
class AnalyticsError(Exception):
    """Base for all package errors."""

class DataQualityError(AnalyticsError):
    """Raised when data fails validation contracts."""
    def __init__(self, table: str, details: Iterable[str]):
        self.table = table
        self.details = list(details)
        super().__init__(f"{table} failed quality checks: {', '.join(self.details[:5])}")

class PipelineOrderError(AnalyticsError):
    """Raised when a step is invoked before its dependency."""
```

### CLI (Typer/Click)

```python
# mypackage/cli.py
from __future__ import annotations
import typer
from datetime import date
from pathlib import Path
from .logging_ import setup_logging
from .config import get_settings
from .transforms.cleaning import clean_orders, revenue_by_segment
from .io.sources import read_orders, read_customers
from .io.sinks import write_parquet

app = typer.Typer(add_completion=False, help="Analytics pipeline CLI")

@app.command()
def run_daily(
    start: date = typer.Option(..., help="Inclusive start date (YYYY-MM-DD)"),
    end:   date = typer.Option(..., help="Inclusive end date (YYYY-MM-DD)"),
    output_dir: Path = typer.Option(Path("./out"), dir_okay=True),
) -> None:
    """Daily revenue-by-segment pipeline."""
    setup_logging()
    log = __import__("structlog").get_logger()
    s = get_settings()
    log.info("run_daily.start", start=start, end=end)

    orders    = clean_orders(read_orders(s.warehouse_conn_str, start, end), start, end)
    customers = read_customers(s.warehouse_conn_str)
    result    = revenue_by_segment(orders, customers)
    out_path  = output_dir / f"revenue_segment_{start}_{end}.parquet"
    write_parquet(result, out_path)

    log.info("run_daily.done", rows=len(result), output=str(out_path))

def main() -> None:
    app()
```

---

## Pandas / NumPy Performance & Memory

### ✅ Vectorize, Don't Iterate

| Slow Pattern | Fast Replacement | Speedup |
|--------------|-----------------|---------|
| `for i, row in df.iterrows()` | `np.where(cond, a, b)`, `df.assign(...)` | 100–1000× |
| `df.apply(fn, axis=1)` | Columnar ops, `numba.njit`, `polars` | 10–100× |
| `df.groupby().apply(fn)` | `transform()` / built-in aggregations / `polars` | 10–50× |
| Repeated string `+` | `''.join(list)` / f-strings (single pass) | 10–100× |
| `pd.concat([a,b,c…], axis=0)` in a loop | Append to list, one final concat | O(n²)→O(n) |

### Memory Tips
- **Categorical dtypes** for low-cardinality strings (<5% unique): `df['country'] = df['country'].astype('category')`
- **Smaller numerics**: downcast ints `pd.to_numeric(df['id'], downcast='integer')`; float64→float32 if precision allows
- **Chunked reads**: `pd.read_csv(path, chunksize=100_000)` or `pl.scan_parquet().sink_parquet()` (Polars streaming)
- **Drop columns early**: project before you read (`usecols=`); never keep unused cols in memory
- **Polars lazy API**: `pl.scan_parquet(...)` builds a plan, pushes down filters/projections, reads only needed pages

### Reproducibility

```python
import os
import random
import numpy as np
import polars as pl

def set_seed(seed: int = 42) -> None:
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    # pandas/pl/dt inherit from numpy for legacy; add explicit for libs that have own RNG
    try:
        import torch; torch.manual_seed(seed)  # noqa: E701
    except ImportError:
        pass
```

---

## How to Test

### Unit with pytest + fixtures

```python
# tests/test_cleaning.py
from __future__ import annotations
from datetime import date
import polars as pl
import pytest
from mypackage.transforms.cleaning import clean_orders, validate_schema, DataQualityError

@pytest.fixture
def raw_orders() -> pl.DataFrame:
    return pl.DataFrame({
        "order_id":    [1,     2,     3,   3,   4,   5],
        "customer_id": [101,   102,   103, 103, 104, 105],
        "order_date":  ["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-02",
                        "bad-date", "2024-01-03"],
        "status":      ["completed", "completed", "cancelled", "cancelled",
                        "completed", "made-up-status"],
        "amount":      [100.0, 200.5, -50, 50, 75.0, 25.0],
    })

def test_clean_orders_dedup_filters_and_types(raw_orders: pl.DataFrame):
    out = clean_orders(raw_orders, start_date=date(2024,1,1), end_date=date(2024,1,31))
    # order_id=3 deduped (last wins), order_id=4 bad date, order_id=5 invalid status, amount<0 dropped
    assert out.height == 2
    assert set(out["order_id"].to_list()) == {1, 2}
    assert out["order_date"].dtype == pl.Date

def test_validate_schema_raises(raw_orders: pl.DataFrame):
    with pytest.raises(ValueError, match="Missing required"):
        validate_schema(raw_orders.drop("amount"))
```

### Property-based (Hypothesis) for Robustness

```python
from hypothesis import given
import hypothesis.strategies as st

@given(
    ids=st.lists(st.integers(1, 1000), min_size=1, max_size=500),
    amounts=st.lists(st.floats(allow_nan=False, allow_infinity=False,
                               min_value=-1_000_000, max_value=1_000_000), min_size=1, max_size=500),
)
def test_clean_orders_never_returns_negative_amount(ids, amounts):
    n = min(len(ids), len(amounts))
    df = pl.DataFrame({
        "order_id":    ids[:n],
        "customer_id": ids[:n],
        "order_date":  ["2024-01-15"] * n,
        "status":      ["completed"] * n,
        "amount":      amounts[:n],
    })
    out = clean_orders(df)
    assert (out["amount"] >= 0).all()
```

### Integration Tests
- Spin up a local Postgres container (`testcontainers-python`)
- Run the CLI against a small fixture warehouse
- Assert output Parquet schema + row count + key aggregations match golden file

---

## Performance Behavior

| Operation | Complexity | Memory | Notes |
|-----------|-----------|--------|-------|
| Polars `join` (hash) | O(n + m) | O(min(n,m)) build | Defaults to inner; stream with `sink_parquet` for >RAM |
| Pandas `merge` (hash) | O(n + m) | O(n + m) copies | Can spike 3–5× data size for wide merges |
| Group-by agg (vectorised) | O(n) cols × O(n) rows | Output only | Always prefer built-in aggs |
| Python `for` loop over rows | O(n), k× constant | Low | k ≈ 100-1000× vectorized |
| `np.linalg` ops | BLAS-dependant | Matrix size | MKL/OpenBLAS use CPU threads; set `OPENBLAS_NUM_THREADS` |
| `pd.read_csv` | O(n) time, ~2× RAM peak | | Use `engine='pyarrow'` or Polars for 2–5× speed |
| PyArrow / Parquet read | O(n) projected cols only | Column batch buffers | Predicate pushdown + column projection → 10× less I/O |
| Network DB I/O | Round-trip + bandwidth | Buffer size | One large query >> many small queries (chunk when huge) |

**Mantra**: *Optimize I/O first, then algorithm, then Python-level micro-optimization.* A `read_parquet(columns=[...], filters=[...])` change typically out-rewards any code-level refactor.

---

## What to Inspect First (When Code is Slow/Wrong)

1. **`py-spy top -p <pid>` or `snakeviz` profile** — Where is wall-time actually spent? (Usually I/O, not compute)
2. **DataFrame `.memory_usage(deep=True).sum()` / Polars `.estimated_size()`** — Is an intermediate 10× the input? Look for joins without select() prune or cross products.
3. **`.isna().sum()` / `unique()` / `value_counts()`** — Did an upstream change introduce unexpected NULLs, invalid categories, or 80% one outlier group?
4. **Randomness without seed** — Did a shuffle/ML training split change results between runs? Check for unseeded RNG calls.
5. **Silent `SettingWithCopyWarning` or Polars `with_columns` not reassigned** — Did a transformation not persist? Always assign `df = df.op(...)`.
6. **Schema drift** — `dtypes` between staging and today: is a column suddenly string where it was int? Compare `dict(source.dtypes)` to contract.
7. **Dependency drift** — `pip freeze | compare` vs lockfile; did a transitive upgrade change default behaviour (e.g., Pandas `groupby(sort=True/False)`)?
8. **Environment-specific config** — Production uses a different warehouse user that lacks access to a view → empty DF → zero metrics.
9. **Non-deterministic dedup** — `.drop_duplicates()` without `subset=` / `keep=` returns arbitrary rows between runs; always specify both.
10. **Division by zero / NaN-infecting arithmetic** — `df['ratio'] = df.a / df.b` silently becomes NaN; use `df.a.divide(df.b, fill_value=0)` (Pandas) or `pl.when(pl.col.b != 0).then(…).otherwise(0)` (Polars).

---
