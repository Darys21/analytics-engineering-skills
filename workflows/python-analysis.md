# Workflow: PYTHON ANALYSIS — Production-Grade Data Code

## Purpose

Write Python data analysis code that is project-structured, environment-isolated, dependency-pinned, type-hinted, function/module/composed (classes only when justified), pandas- and numpy-idiomatic, input-validated, logged, exception-safe, unit/integration-tested, performant via vectorization, memory-efficient, reproducible, configuration-driven, secrets-safe, CLI-friendly, and suitable for ETL/ELT pipeline embedding or interactive analysis. This workflow elevates "notebook throwaway code" to code the team trusts in production pipelines.

## When to use

- When producing Python code that will (a) run more than once, (b) be reviewed by another engineer, (c) feed a production dashboard or model, or (d) be used as a step in a scheduled pipeline.
- When converting a Jupyter notebook analysis into a production-ready script, module, or package.
- When writing custom data quality checks, anomaly detectors, reconciliations, ML feature engineering, or data transformations that cannot be expressed cleanly in SQL.
- When auditing or refactoring existing Python data code.

## Inputs

- Analytical specification or KPI to compute (from BUSINESS-SPEC or DATA-MODEL).
- DATA-DISCOVERY profiles of input data sources.
- Target environment: serverless function, container, orchestrated DAG, notebook server, CI runner.
- Team's chosen Python toolchain version (3.10+ recommended), package manager (pip-tools, Poetry, PDM, uv), and testing framework (pytest standard).
- Any existing project template or internal PyPI mirror.

## Preconditions

- Python 3.10+ is installed locally and in the target execution environment.
- Secrets management is available (env vars, .env file + gitignore, AWS/GCP/Azure secret manager, HashiCorp Vault).
- CI runner has network access to install dependencies and run the test suite.

## Procedure

1. **Scaffold the project structure according to purpose.**
   1. **Single-purpose CLI / ETL script (≤500 lines):**
      ```
      /project-root
        pyproject.toml            # build-system, deps, scripts
        requirements.lock         # pinned transitive deps
        README.md
        .env.example
        .gitignore
        /src
          __init__.py
          config.py               # pydantic-settings or dataclass config
          logging_setup.py        # structlog / stdlib JSON logger config
          main.py                 # entrypoint: CLI argparse/click/typer
          extract.py              # data fetching
          transform.py            # transformations
          load.py                 # output writing
          validation.py           # input/output schema checks
          exceptions.py           # custom exception hierarchy
        /tests
          conftest.py             # fixtures, test data factories
          test_config.py
          test_extract.py
          test_transform.py
          test_validation.py
          /fixtures                # small parquet/CSV test input sets
        /analyses                  # one-off Jupyter notebooks, gitignored outputs
      ```
   2. **Interactive analysis project (notebooks first, with supporting modules):** Same as above plus `/notebooks` under version control (use `jupytext` for .py representation in git to avoid binary diffs). No notebook output cells in committed files.
   3. **Shared internal library:** Build a proper package with `src/<package_name>/`, semantic versioning, CHANGELOG, internal PyPI publishing, docs built with mkdocs/sphinx.
   4. Use `pyproject.toml` exclusively (no `setup.py`, no `setup.cfg`, no `requirements.txt` floating around).
2. **Isolate environments and pin all dependencies.**
   1. Use a per-project virtual environment. Never install packages globally.
   2. Pin direct dependencies with version ranges in `pyproject.toml` (`pandas = ">=2.1,<3"`).
   3. Produce and commit a fully-pinned transitive lock file (`requirements.lock` via `pip-compile` / `uv pip compile` / `poetry.lock` / `pdm.lock`). Production installs use ONLY the lock file, never floating ranges.
   4. Distinguish group dependencies: `main`, `dev` (pytest, black, ruff, mypy, pre-commit), `test`, `docs`. CI installs `main + test + dev`; production installs only `main`.
   5. If using Docker, produce a multi-stage build: builder stage compiles/installs locked deps to a venv; runtime stage copies only the venv + source code. Runtime image has no compilers, no pip, no dev dependencies.
3. **Write type hints everywhere public-facing.**
   1. Apply type hints to: all function signatures (params and return), module-level constants, class attributes, public variables.
   2. Use the typing standard library + pandas/numpy stubs: `pandas.DataFrame`, `pd.Series[float]`, `np.ndarray[np.float64, Any]`, `Mapping[str, Any]`, `Sequence[Record]`.
   3. Use `pydantic` v2 for configuration and for schema validation of inputs and outputs. Define `InputRecord`, `TransformedRecord`, `OutputRecord` models.
   4. Run `mypy` or `pyright` in strict mode in CI. Ignore only via inline `# type: ignore[code]` with a justification comment.
4. **Compose logic as small, pure functions in modules; use classes only when justified.**
   1. **Default to pure functions.** Each function: (a) takes explicit inputs, (b) has no side effects inside, (c) returns a single output type or tuple, (d) <100 lines. Name verbs: `extract_invoices_from_sftp()`, `clean_invoice_lines(raw_lines: pd.DataFrame) -> pd.DataFrame`, `reconcile_totals(...) -> ReconciliationReport`.
   2. **Group functions into modules by responsibility** (extract, transform, load, validation, io). Avoid god modules.
   3. **Use classes ONLY when:**
      - You have encapsulated state + invariant that must hold across method calls (e.g., `DatabaseConnectionPool`, `RateLimiter`, `FeatureStore`), OR
      - You need polymorphism via inheritance/ABC (`BaseExtractor` with 3 subclasses for different source types).
      - Prefer dataclasses / NamedTuples / pydantic models for data-only bags of fields; do not write empty classes with getters/setters.
   4. One package/class/function does one thing. If a function is named `process_and_save_and_notify`, split it.
5. **Write pandas and numpy code that is vectorized, memory-efficient, and validated.**
   1. **Vectorize. Do not iterate.** Prefer:
      - `df.assign(new_col = df["a"] * df["b"])` over `for i, row in df.iterrows()`.
      - `df.groupby("key")["metric"].transform("sum")` over per-group apply with custom Python code.
      - `numpy.where(cond, a, b)` and `pandas.Series.mask/where` over per-row if/else.
      - `pd.merge` / `pd.merge_asof` over nested loops.
   2. **Only reach for `.apply` as an escape hatch**, and only when you can prove the group size is bounded. If `.apply` contains more than 5 lines of Python, move the logic to numpy/numba or C-extension-backed code.
   3. **Memory and dtypes:**
      - Downcast floats: `float64` → `float32` when precision allows (pandas `to_numeric(downcast="float")`).
      - Downcast ints: nullable `Int64` → `Int32`/`Int16` if min/max allows.
      - Use categorical dtype for low-cardinality strings (`nunique / nrows < 0.05`).
      - Use `pyarrow` string dtype or `pd.StringDtype("pyarrow")` instead of `object` for large string columns.
      - Dates: `datetime64[ns, UTC]` explicitly; timezone-naive timestamps are forbidden in production (annotate as a validation error).
      - Profile memory before/after with `df.memory_usage(deep=True).sum()`.
   4. **Chunked processing for data larger than RAM:** Use `pandas.read_csv(..., chunksize=...)`, `pyarrow.dataset` / `dask.dataframe` / `polars` / `PySpark` depending on scale. Never `pd.read_csv()` a 20GB file on a 16GB laptop — it will OOM.
   5. **Validation at boundaries:** At entry points (extract) and exit points (load), run pydantic / `pandera` schema checks:
      - Column presence, dtypes, uniqueness on keys.
      - Null percentage per column within configured thresholds.
      - Range checks on numeric columns, regex on strings, date bounds.
      - Fail fast with a clear `ValidationError` containing the violating rows' sample (≤20 rows) and counts; never silently proceed with bad input.
6. **Log structured data; use a custom exception hierarchy; never swallow exceptions.**
   1. **Logging setup once** in `logging_setup.py`. Use JSON-structured logs in production (structlog or stdlib `logging` with JSON formatter) with fields: `timestamp`, `level`, `logger`, `event`, `run_id`, `commit_sha`, `duration_ms`, `rows_processed`, `error` (if any).
   2. **Log at appropriate levels:**
      - DEBUG: dev-only diagnostics (intermediate row counts during transform), disabled by default.
      - INFO: one line per major stage start/end: "extracted 412,301 rows from source X in 14.2s", "loaded 3,905 rows to table Y".
      - WARNING: handled edge cases: "12 rows skipped due to out-of-range date (< 0.01% of input)", "backfill mode enabled; rewriting partition 2024-03".
      - ERROR: failures that cause the run to exit non-zero, always include traceback + context (run_id, offending batch_id, etc.).
   3. **Custom exceptions:** Define a clean hierarchy:
      ```python
      class AnalyticsError(Exception): pass
      class ExtractError(AnalyticsError): pass
      class ValidationError(AnalyticsError): pass
      class TransformError(AnalyticsError): pass
      class LoadError(AnalyticsError): pass
      ```
      Catch low-level errors (e.g., `ConnectionError`, `pa.ArrowInvalid`) only to wrap + enrich with context, then re-raise.
   4. **Never use bare `except:`.** Catch the narrowest exception class possible. Never `except Exception: pass`. Log and re-raise or recover explicitly.
7. **Write tests at the right layers with explicit fixtures.**
   1. **`/tests/conftest.py` with fixtures:**
      - Small, deterministic, hand-curated input fixtures stored as `/tests/fixtures/*.parquet` (≤100 rows) — one happy path, one fixture with known edge cases (NULLs, outliers, duplicate keys, extreme dates).
      - Mocked external services: `mock_sftp_client`, `mock_db_connection` using `unittest.mock` / `responses` / `pytest-httpserver`.
   2. **Unit tests (80% of coverage):**
      - One test class per module, one test function per function branch.
      - Test pure transform functions against known input→expected output using the edge-case fixture. Include: expected row count, exact expected values on 5 sample rows, dtypes match.
      - Use `pytest.approx` for floats; never `assert actual == expected` on floating point.
      - Parametrize: `@pytest.mark.parametrize("fx_name,expected", [("happy", 1234.5), ("edge", 0.0)])`.
   3. **Validation tests:** For the schema validation module, test both valid inputs and all invalid branches (missing col, wrong dtype, duplicate key, date out of range) — every rule must have a failing case that raises `ValidationError` with the correct message substring.
   4. **Integration tests (15%):** Run extract + transform + load end-to-end against a test database/sandbox account (never production). Confirm output rows + KPI totals against known baseline.
   5. **Smoke tests (5%):** A single test that invokes the CLI/entrypoint with `--help` and with the sample fixture; ensures dependency wiring, imports, and config work.
   6. **Coverage gate in CI:** Fail the build if coverage <75% for libraries, <85% for pipeline code. Cover all exception branches.
8. **Performance via vectorization, profiling before optimization.**
   1. Do not optimize based on intuition. Profile first:
      - Line-level: `line_profiler` / `py-spy` on the slow transform.
      - Pandas-specific: check `.vectorized` operations vs `.apply`; use `pandas.util.testing.assert_produces_warning` for `PerformanceWarning` (object-dtype string ops, chained indexing).
   2. Prefer `numpy` vectorization → `pandas` built-in operations → `numba` JIT → `polars` rewrite → native Cython/Rust extension, in that order. Measure each step before moving to the next.
   3. For long-running pipelines, add progress logging every N rows or every partition, with ETA: `processed 1,200,000/4,800,000 rows (25%) — ETA 14m 22s`.
9. **Ensure reproducibility, configuration-driven code, and secrets safety.**
   1. **Reproducibility hygiene:**
      - Fix random seeds everywhere stochastic operations occur (numpy, pandas sample, sklearn, torch). Expose seed via config, never hardcode 42 deep in a function.
      - Use sort orders before any ordering-sensitive operations (top-N, first-value, etc.). Deterministic output on identical input is mandatory.
      - Pin Python version in CI + Docker image. Use a matrix to test on the lowest and highest supported versions.
   2. **Configuration:**
      - No magic strings/numbers in source code. Every constant (input path, SLA window, outlier threshold, SFTP host, chunk size, seed) lives in a config object.
      - Config loads via `pydantic-settings` from a YAML/JSON file, env vars, or CLI args in that precedence order (CLI overrides env, env overrides file). Each has a documented default and type.
   3. **Secrets safety:**
      - Credentials via env vars or secret manager ONLY. No `.env` committed; `.env.example` committed with placeholders.
      - Add `detect-secrets` / `gitleaks` as a pre-commit hook and CI gate. Fail PRs on any high-entropy string that looks like an AWS key / DB password / token.
      - Logging must filter secrets. Never log a raw config dump; log only non-sensitive field names and their lengths/hashes.
10. **Expose a clean CLI interface (when applicable); support ETL/ELT patterns.**
    1. Use `typer` or `click` for the entry point. Mandatory subcommands:
       - `run --start-date <YYYY-MM-DD> --end-date <YYYY-MM-DD> [--backfill]` — primary execution.
       - `validate` — run schema validations on latest input only; no write.
       - `reconcile --period <YYYY-MM>` — run reconciliation against golden source; output report.
       - `--help` for every subcommand.
    2. **Exit codes:** 0 on success, 1 on validation error, 2 on extract/transform/load failure, 3 on config/secrets error. Document each.
    3. **ETL patterns:** For long-running batch loads, checkpoint every N rows/partition: write a `.checkpoint` marker file or database row; on re-run after failure, resume from last successful checkpoint rather than re-processing everything. Make checkpoints idempotent.
11. **Run lint, type check, test, and smoke locally before PR.**
    1. Use `pre-commit` hooks: ruff (lint + isort + format), black, mypy, end-of-file-fixer, trailing-whitespace, detect-secrets.
    2. `pytest -xvs` locally before push.
    3. Attach profiling output + test-run summary to the PR description if performance-critical.

## Decision points

- **Step 1 (Notebook vs module).** If the deliverable is a one-off exploration that will never run again, a notebook is acceptable if it is paired with a short README, deterministic seeds, and committed via `jupytext` as a .py representation. If it will run a second time, extract logic to modules per step 1.1.
- **Step 3 (Strict type-check cost/benefit).** For a 200-line internal tool, mypy strict may be overkill. Set a gradient: strict for shared libs and production pipelines, basic type hints only for throwaway scripts. Enforce via CI configuration per repo.
- **Step 5.4 (pandas vs polars vs PySpark).** Default to pandas for <2GB in-memory. Move to polars when pandas OOMs or profiling shows 40%+ of time in the pandas engine. Move to PySpark/Databricks when single-machine processing is insufficient. Never start a pipeline in PySpark "for future scale" if the data is currently 500MB.
- **Step 7.6 (Coverage bar).** 75–85% is a healthy target. 100% coverage is vanity. If a module has complex exception paths for rare upstream failures, test them but don't penalize coverage for branches that can only be hit by mocking the OS.
- **Step 10 (Checkpointing granularity).** If a batch run takes >20 minutes end-to-end, checkpoint after every input partition or 10-minute wall time, whichever is coarser. Checkpoints add overhead; don't checkpoint every row.

## Validation

- Project conforms to the chosen structure per step 1 (src layout, tests layout, pyproject.toml).
- All transitive dependencies are pinned in a committed lock file; no floating installs in production.
- Type hints are present on all public functions and pass mypy/pyright at the configured strictness level.
- Logic is modularized as pure functions in modules; classes are only used where they encapsulate state invariants or polymorphism with ABCs.
- Pandas/numpy code is vectorized; no `iterrows()`, no `.apply` with >5 lines of Python, no nested loops without a justification + profiling evidence.
- Memory dtypes are explicitly chosen; categorical for low-card strings, downcast numerics, UTC-aware datetimes only.
- Boundary validation (pydantic/pandera) runs at extract and load; schema violation raises ValidationError with sample offending rows.
- Structured JSON logs at 4 levels; custom exception hierarchy; no bare `except`; no swallowed exceptions.
- Test suite covers unit + validation + integration + smoke; runs in CI with a coverage gate and passes 100%.
- Random seeds are exposed via config; all ordering-sensitive operations have deterministic sorts.
- No secrets in code; pre-commit secret-scan passes; `.env.example` exists.
- CLI has `run/validate/reconcile` subcommands with documented exit codes; checkpointing is present for runs >20min.
- Locally: pre-commit hooks pass, full test suite passes, smoke run on fixture succeeds.

## Expected outputs

- A version-controlled repository/folder matching the step 1 structure for the project.
- `pyproject.toml` + pinned lockfile.
- Source modules: `config.py`, `logging_setup.py`, `main.py` (or CLI entry), `extract.py`, `transform.py`, `load.py`, `validation.py`, `exceptions.py`. Each <500 lines; each function <100 lines.
- `/tests` with conftest, fixtures, and unit/validation/integration/smoke tests. Coverage report.
- `README.md`: purpose, install from lockfile, how to run each CLI subcommand, config schema explanation, exit codes, contact.
- `.env.example`, `.gitignore`, pre-commit config, CI workflow file.
- A CHANGELOG.md for libraries or reusable packages.
- PR link with review completed and CI green.

## Common failure modes

1. **Notebook-as-production.** 1,500-cell notebook committed with outputs, stateful execution order, manual file paths hardcoded to a developer's laptop. Remedy: step 1 enforces src layout; step 10 CLI; step 9 config externalization. Any notebook that runs twice is converted.
2. **Global mutable state.** `pd.set_option` called at module import; a module-level cache dict that is mutated. Breaks test isolation and reproducibility. Remedy: pure functions default; options set in a controlled entrypoint function only.
3. **`.apply(massive_python_function)` on 10M rows.** A transformation that should take 2 seconds takes 20 minutes. Remedy: step 5.1 vectorization rules; step 8 profiling before rewrite to numba/polars.
4. **Chained indexing pandas warnings → silent bugs.** `df["c"][i] = value` sometimes works, sometimes raises, depends on copy-on-write mode. Remedy: always use `.loc[row_indexer, col_indexer] = value`; enforce in lint/ruff rule or pandas future warning treated as error in tests.
5. **Timezone-naive timestamps mixing with UTC.** DST transitions and server-local timezone drift cause off-by-one day errors. Remedy: step 5.3 datetime64[ns, UTC] enforced via pandera schema at input validation.
6. **Secrets in logs.** `logger.info(f"connected with pwd={config.db_password}")` slips through. Remedy: step 6.1 structured logger filters; step 9.3 secret-scan; never log config dumps.
7. **Non-deterministic output.** Two runs with identical input produce slightly different Parquet files because of dict ordering, DataFrame row order, random seeds. Remedy: step 9.1 explicit seeds; step 9.1 sort before every ordering-sensitive output.
8. **Tests use network-dependent fixtures.** Test suite fails randomly because it hits a real SFTP. Remedy: step 7.1 network services mocked; tests run offline.
9. **Coverage gate gamed.** Tests assert `True` and hit lines without checking values. Remedy: step 7.2 test review rubric requires 5 known-row exact matches per transform; PR reviewer enforces.
10. **Checkpoints not idempotent.** A resumed run duplicates output rows. Remedy: checkpoint key is (partition_date, batch_id) and load step does UPSERT/MERGE on that key, not blind INSERT.

## References to load

- `references/python-analytics-project-template.zip` — Ready-to-use project scaffold with src/tests layout, pyproject.toml (pandas/numpy/pydantic v2/typer/structlog/ruff/pytest/mypy), pre-commit config, CI workflow, sample Dockerfile, example fixture + test.
- `references/pandas-vectorization-cheatsheet.ipynb` — 40 worked before/after examples: iterrows → assign, apply → groupby transform, nested if/else → np.where, per-row dict access → merge.
- `references/pandas-memory-optimization-recipe.py` — Function `optimize_df_dtypes(df, max_cardinality_ratio=0.05, category_min_unique=10)`: downcasts ints/floats, converts strings, enforces UTC dates; returns before/after memory report.
- `references/pandera-schema-examples.py` — 10 schemas: invoice, shipment, employee, sensor_reading, etc. with type/null/uniqueness/range/regex/date checks + custom error aggregation.
- `references/structlog-json-logging-config.py` — Production logging setup: JSON format, redaction filters for secret fields, trace ID injection, run_id/commit_sha binding, file + stdout handlers, level from env.
- `references/custom-exception-hierarchy-template.py` — Base AnalyticsError + Extract/Validation/Transform/Load subclasses, with error code registry and PagerDuty-friendly error categories.
- `references/pytest-analytics-fixtures-conftest.py` — Reusable conftest: parquet fixture loader, temp directory with cleanup, mock sftp, mock duckdb/snowflake/bigquery clients, deterministic seed fixture.
- `references/cli-template-typer.py` — Typer CLI skeleton with run/validate/reconcile subcommands, date parsing, dry-run mode, config file + env + CLI precedence, exit codes.
- `references/etl-checkpoint-and-resume.py` — Abstract checkpoint store interface (local file / Postgres / S3), UPSERT idempotent load example, resume-from-last-checkpoint logic.
- `references/python-performance-profiling-cookbook.md` — Recipes: line_profiler, py-spy, pandas tqdm progress, numpy einsum vs loops, numba JIT decorator patterns, when to move to polars.
- `references/python-reproducibility-checklist.md` — 15-item checklist for deterministic output: seeds, sorts, pinned deps, Docker SHA base images, input content hashing, output checksums.
- `references/python-analysis-review-checklist.md` — 35-item PR review rubric covering every step; used by every reviewer.

## Completion criteria

- Repository structure matches step 1; `pyproject.toml` is the single build-config source of truth.
- Transitive dependencies are pinned in a committed lock file; dev/main/test groups are distinct.
- Mypy/pyright at the configured strictness passes.
- Pandas code is vectorized (no iterrows, apply ≤5 lines only when justified); dtypes optimized; UTC-aware datetime only.
- Pydantic/pandera validation runs at input and output boundaries with explicit failure messages + sample violators.
- Structured JSON logging at 4 levels; custom exception hierarchy; 0 bare `except:`, 0 swallowed exceptions.
- Test suite has unit/validation/integration/smoke layers; CI passes; coverage at or above project bar.
- Random seeds are configurable; ordering-sensitive code sorts; identical input produces byte-identical output (tested via hash).
- No committed secrets; pre-commit secret-scan passes; `.env.example` documented.
- CLI has run/validate/reconcile subcommands, dry-run, documented exit codes; checkpointing present for runs >20 min.
- README covers install, configure, run, test; CHANGELOG for libraries.
- CI workflow file committed; last CI run green.
- PR reviewed against rubric and merged.
