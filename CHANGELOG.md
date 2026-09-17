# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
starting from `v1.0.0`. Pre-`1.0.0` releases use the convention
`MINOR` for feature additions and `PATCH` for fixes.

## [Unreleased]

(nothing yet)

---

## [v0.1.0] — 2026-09-17

> Initial project scaffold. This release establishes the repository structure,
> the five core deterministic validators, the documentation backbone, and the
> contribution workflow. Future releases will populate `workflows/`,
> `references/`, `templates/`, and `evals/` with concrete content, and will
> extend the validators based on real-world usage.

### Added

- **Core repository structure**: `workflows/`, `references/`, `templates/`,
  `scripts/`, `evals/`, `docs/` directories plus root metadata files
  (`SKILL.md`, `README.md`, `LICENSE`, `CONTRIBUTING.md`, `CHANGELOG.md`).
- **`validate_project.py`** (`scripts/`):
  - Required-directory and required-file existence checks.
  - Internal markdown link resolution (grep-based, skips remote links).
  - Deduplicated issue list with severity (ERROR / WARN / OK).
  - Summary table output, `--strict` mode, configurable `--skip-*` flags.
  - Non-zero exit on errors (or warnings when strict is enabled).
- **`validate_sql.py`** (`scripts/`):
  - `SELECT *`, CTE recommendation, comma-style consistency, and aggregate
    NULL-handling checks.
  - `DISTINCT COUNT` vs `COUNT(DISTINCT)` detection.
  - Implicit JOIN, Cartesian product, and JOIN-without-ON anti-patterns.
  - `DELETE` / `UPDATE` without `WHERE`, `INSERT` without column list.
  - snake_case naming enforcement for table/column identifiers.
  - Rule-level `--disable`, `--json`, and `--strict` support.
- **`validate_dax.py`** (`scripts/`):
  - Measure definition extraction from `.dax`, `.bim`, `.pbip`, `.json`,
    and `.txt` files.
  - Anti-pattern detection: nested IF inside CALCULATE, ALLSELECTED misuse,
    `FILTER(ALL(...))`, `SUMX`-where-`SUM`-suffices, `CALCULATE(COUNTROWS)`
    vs `COUNTROWS(FILTER(...))`, `IF(VALUES(...))` vs `SELECTEDVALUE`,
    missing `DIVIDE` vs `/`, `EARLIER` usage, nested `CALCULATE`.
  - Measure-name convention enforcement (PascalCase).
  - `--disable`, `--strict`, `--json`, `--format`.
- **`validate_tmdl.py`** (`scripts/`):
  - Rough TMDL section parser for tables, columns, measures, relationships,
    hierarchies, etc.
  - Required-attribute checks (column: `sourceColumn` or `expression`,
    `dataType`; measure: `expression`).
  - Numeric column/measure `formatString` warnings.
  - Relationship integrity: from/to table + column references resolve when
    cross-file index is available.
  - Display-folder consistency and duplicate-name detection.
  - PascalCase naming enforcement.
- **`quality_check.py`** (`scripts/`):
  - CSV (stdlib) + optional Parquet (pandas) input support.
  - Column completeness, null counts, uniqueness per column, PK candidate
    detection, full-row duplicate count.
  - Numeric outlier detection via IQR method (configurable multiplier).
  - Datetime gap detection (configurable hour threshold) with auto-detection
    of likely datetime columns in CSV fallback mode.
  - Numeric stats: min, 25/50/75%, max, mean, std.
  - Per-column numeric range checks (`--range col:min:max`, repeatable).
  - `--primary-key` uniqueness validation.
  - `--json`, `--strict` / `--fail-on-warnings`, `--sample N`.
- **Documentation backbone**:
  - `README.md` with overview, quickstart, install/activation steps, and
    validator summary table.
  - `LICENSE` (MIT).
  - `CONTRIBUTING.md` with contribution types, style guide, and PR process.
  - `docs/architecture.md` — per-directory responsibilities, composability
    model, progressive disclosure, extension points.
  - `docs/workflows.md` — workflow catalog table (purpose / when to use /
    composition pointers).
  - `docs/contribution-guide.md` — step-by-step walkthroughs for adding a
    workflow, reference, template, validator, or eval case; naming
    conventions; the review checklist.
  - `docs/design-principles.md` — the 25 design principles that govern the
    project, including determinism, composability, progressive disclosure,
    validator honesty ("no fake validators"), evaluation-first, and
    documentation hygiene.

### Known limitations (not bugs; documented in each module docstring)

- All validators are regex/heuristic where a true parser would be ideal.
  False positives are possible and should be reported with a reproducer.
- `validate_dax.py` JSON extractor uses heuristics to find DAX expressions
  inside `.bim` / `.pbip` blobs; complex or hand-edited JSON may miss some.
- `validate_tmdl.py` indentation parser is a best-effort subset of the TMDL
  spec; it is not a replacement for Microsoft's official TMDL parser when
  100% semantic correctness is required.
- `quality_check.py` loads full files into memory; use `--sample N` for
  large CSV/Parquet inputs.

[Unreleased]: https://github.com/<org>/<repo>/compare/v0.1.0...HEAD
[v0.1.0]: https://github.com/<org>/<repo>/releases/tag/v0.1.0
