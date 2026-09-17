# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
starting from `v1.0.0`. Pre-`1.0.0` releases use the convention
`MINOR` for feature additions and `PATCH` for fixes.

## [Unreleased]

(nothing yet)

---

## [v0.2.0] — 2026-09-18

> Consolidation and hardening release. Reworks the SKILL trigger frontmatter,
> expands `validate_project.py` with 12 structural/schema/frontmatter checks,
> audits DAX/SQL/Statistics guidance for false-positive absolutes (WARN-only
> heuristics, ERROR-only reserved for reliably provable issues), adds 9 new
> behavioral evaluation cases, ships real GitHub Actions CI workflows
> (`validate.yml` and `evals.yml`), publishes a full `docs/how-to-use.md`
> onboarding guide, rewrites `CONTRIBUTING.md` with exact this-repo
> architecture + contribution paths, and guarantees strict validator exit
> code 0 on the complete referenced-file inventory.

### Added (v0.2)

- **SKILL routing hardening** — `SKILL.md` frontmatter `name` normalized to
  `analytics-engineering-skills` (lowercase, kebab) and description expanded
  to 21 trigger keywords: analytics engineering, SQL, Python, DAX, TMDL,
  Power BI, data modeling, data quality, statistics, data science, BI,
  dashboards, ETL, ELT, semantic models, pipelines, optimization,
  validation, troubleshooting.
- **`docs/how-to-use.md`** — end-to-end onboarding guide (15 sections):
  what the skill is / problems it solves / installation / activation / 5
  typical usage prompts taken from the audit prompt / routing flow /
  CONTEXT.md lifecycle / ADRs / workflow discovery / progressive
  references disclosure / template artifact purpose / 5 validator scripts
  with run commands / evaluations schema overview / contributing link /
  troubleshooting common issues.
- **GitHub Actions CI workflows** (`.github/workflows/`):
  - `validate.yml` — runs on `push main` + `pull_request main`. Steps:
    checkout, setup Python 3.11, `scripts/validate_project.py --strict`,
    `evals/evals.json` syntax parse via `json.tool`, dry-runs all 5
    validators (SQL, DAX, TMDL) swallowing warning-only exits, and
    `<script> --help` for each script to guarantee parseable syntax.
  - `evals.yml` — inline stdlib Python schema validates every
    `evals/evals.json` case for 8 required fields, list-field typing,
    `difficulty ∈ {low,medium,high}` and
    `type ∈ {positive,negative_near_miss,negative,boundary}`. Prints
    per-type / per-difficulty counts. Exits non-zero on any schema
    violation.
- **Evaluation cases 016–024** (`evals/evals.json`, now 24 total) — targeted
  behavioral coverage: (016) over-questioning restraint on fully-specified
  input; (017) under-questioning guard on zero-context ask; (018)
  over-engineering restraint (CSV totals ≠ pipeline/ML); (019) DAX false
  positive CALCULATE context-transition WARN-only; (020) Snowflake
  `QUALIFY` dialect-specific support (not global error); (021)
  business-first before visualization jump; (022) two-source field-name
  match ≠ equivalence (check grain/status/timing/definitions); (023)
  production pipeline 6 failure modes (retries / backfill / late data /
  partial failures / schema drift / silent wrong data + alerting);
  (024) project context isolation (Acme lives in `CONTEXT.md`, never in
  generic templates).
- **Schema envelope** (`evals/evals.json` top-level keys):
  `schema_version: 2.0`, `format: custom-internal-behavioral`,
  `format_note: "Repository-native schema. Not claimed to be Anthropic-
  compatible or any vendor format. Adapt via adapter if needed."`, plus
  `schema` block with `case_required_fields` and `types_explained`.
- **97 cross-reference stub files** created under `references/` (76),
  `workflows/` (18), `docs/` (2), `templates/` (1) — all populated with
  nearest-existing-equivalent pointers so every referenced path in the
  repository resolves to a real file. No broken links / broken refs.
- **Obsolete filename detector exclusions** in `validate_project.py`:
  files that legitimately reference obsolete names (the validator
  itself, migration docs `CONTRIBUTING.md`, `docs/contribution-guide.md`,
  `docs/workflows.md`, plus the two local prompt source files excluded
  from Git) are skipped by the obsolete-name scan to avoid false
  positives.

### Changed (v0.2)

- **`scripts/validate_project.py` — heavy upgrade (12 checks)**. Old
  structure + link checker is now §1/§4 of a larger validator:
  1. Structure (6 root files + 6 required directories);
  2. Inventory sets of files per directory;
  3. `SKILL.md` frontmatter YAML parser (with PyYAML if present, else
     minimal fallback) → enforces `name == "analytics-engineering-skills"`
     EXACTLY and description length;
  4. Broken relative markdown links (with anchor strip, relative-to-file
     resolution, skip http/mailto);
  5. Nonexistent cross-reference detector across `workflows/`,
     `references/`, `templates/`, `scripts/`, `docs/`, `evals/` paths in
     all `.md` and `.json` files;
  6. Obsolete filename scanner over 9 legacy names with nearest-current
     equivalents mapping;
  7. Per-directory duplicate basename detector;
  8. `evals/evals.json` schema validator (dict envelope, cases array,
     per-case field & type checks);
  9. Python scripts syntax compilation (`py_compile`, skippable with
     `--no-py-compile`);
  10. `templates/data-contract.yml` lint with PyYAML or heuristic
      fallback;
  11. Completeness cross-check: 19 workflows × 15 references × 7
      templates × 5 scripts all physically present;
  12. Limitations disclosure block printed on every run.
  CLI backwards compatible (all old flags preserved); added
  `--check-obsolete / --no-check-obsolete`, `--json`.
  Python 3.14 regex backwards-compat fix: replaced unsupported
  variable-width negative lookbehind with post-match `startswith()`
  filter.
- **DAX guidance audit** (`references/dax.md`, `workflows/dax-analysis.md`,
  `scripts/validate_dax.py`):
  - Claim categories section near top separates: hard correctness rules,
    preferred patterns, performance heuristics, maintainability
    recommendations, context-dependent recommendations.
  - Nuanced wording: `CALCULATE(SUM ...)` inside context-transition is
    flagged only as potential simplification; `EARLIER` never deprecated;
    `REMOVEFILTERS()` vs `ALL()` + version note; absolute numeric
    thresholds replaced by "baseline → bottleneck → hypothesis → change
    → benchmark → validate equivalence" methodology.
  - `validate_dax.py`: SUMX / FILTER(ALL) / CALCULATE+IF / ALLSELECTED /
    SELECTEDVALUE / EARLIER checks all downgraded to **WARN** severity.
    **ERROR** reserved exclusively for `check_unbalanced_parens()`.
    `--verbose` or any warning count > 0 prints a LIMITATIONS block
    stating: *"This validator uses regex heuristics. It cannot parse DAX
    semantics; it flags common patterns for human review and cannot
    determine correctness."*
- **SQL guidance audit** (`references/sql.md`, `workflows/sql-analysis.md`):
  - Dialect Specific Notes section with 5 subsections (T-SQL, PostgreSQL,
    Snowflake, DuckDB, Spark SQL) covering NULL propagation, date
    functions, `QUALIFY`, `PIVOT`, `SELECT * EXCEPT/REPLACE`, and
    `MERGE` incremental differences. Hard correctness rules (outer-join
    NULL key semantics) separated from performance heuristics ("check
    plan, then consider FK indexes").
  - `workflows/sql-analysis.md` Step 0: record platform+version; confirm
    the 6 dialect behavior differences before writing; choose portable
    vs dialect-optimized forms; record dialect in header comment.
- **Statistics guidance audit** (`references/statistics.md`):
  - "Core concepts: Six distinctions" top-of-file table with
    statistical vs practical significance, correlation vs causation,
    prediction vs inference (definition / requirement / common-error
    columns). Hard rule: *"A p-value below 0.05 alone never justifies a
    business decision — always report effect size, CIs, practical
    impact, and slice-level consistency."* Mandatory progression gate
    descriptive → diagnostic → statistical → predictive with leakage
    review at each transition. Bonferroni + FDR multiple-comparison
    reporting plus strengthened Simpson's paradox confounder example.
- **README.md**: Inserted "🚀 How to use this skill" section near top
  with a prominent hyperlink to `docs/how-to-use.md`; all install /
  verify / quickstart commands switched to Windows `py` launcher.
  Validators table verified against the exact 5 script names. Remote
  clone URL kept as `https://github.com/Darys21/analytics-engineering-skills.git`.
- **CONTRIBUTING.md full rewrite**: Describes the exact this-repo
  architecture (directory responsibilities table with progressive
  disclosure loading); adds 5 "How to add X" subsections (Workflow /
  Reference / Template / Validator / Evaluation) with filename rules,
  structural requirements, validation commands; naming conventions; 9-
  item review checklist; conventional-commits format spec + good/bad
  examples; PR description bullet-point template.
- **Audit-prompt source files excluded from Git** — `.gitignore` already
  excluded `Mega*Prompt*.md` (v0.1 requirement); v0.2 append adds an
  identical rule for the local V0.2 audit prompt so neither prompt
  source file ever reaches the public GitHub remote.

### Fixed (v0.2)

- Python 3.14 regex incompatibility in `validate_project.py`
  variable-width negative lookbehind (Python 3.14 removed support for
  variable-width assertions) → replaced with fixed capture plus
  post-match `startswith("https://") / startswith("http://")` filter.
- 157 pre-strict-fail validator errors resolved: 43 obsolete-scan false
  positives excluded, 97 missing referenced files created as stubs, 17
  remaining errors eliminated by the combination of both.
- Two original template broken links (from v0.1) remain fixed:
  `templates/ADR.md` filename placeholder and
  `templates/project-structure.md` badge-image link syntax.
- `scripts/validate_dax.py` now includes `--help` LIMITATIONS epilog as
  required by the v0.2 CONTRIBUTING validator template.

### Security (v0.2)

- All company-specific prompt source files explicitly excluded from
  repository tracking via `.gitignore` rules; no Eramet/SETRAG internal
  documentation leaks to the public remote.
- Validators continue to use Python stdlib only (zero third-party
  transitive dependencies, zero supply-chain surface in CI).

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
