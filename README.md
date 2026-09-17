# Analytics Engineer Agent Skills

Composable, opinionated building blocks for an **Analytics Engineering agent** that
operates on data warehouses, semantic models, and BI artifacts. The repository
provides reusable **workflows**, **reference** material, **templates**,
**validators** (scripts/), and an **evaluation** harness so that an LLM agent
can produce trustworthy, reviewable results.

> Designed for the SETRAG / Eramet analytics platform context and generalizable
> to any modern warehouse stack (SQL, DAX / Power BI, TMDL, CSV / Parquet data
> pipelines).

## 🚀 How to use this skill

Read the end-to-end practical guide at [docs/how-to-use.md](docs/how-to-use.md) for installation, activation, typical prompts, routing, validation, contributing, and troubleshooting.

## Project Context

An Analytics Engineer spends most of their time moving *data* into *information*
that humans can act on. In practice, this work is a composition of small,
deterministic tasks:

- Writing and validating SQL models.
- Designing semantic models (Power BI / Analysis Services / TMDL).
- Writing DAX measures that are correct, performant, and readable.
- Profiling source and output data to catch quality regressions.
- Documenting and reviewing changes in a structured way.

This repository encodes those tasks as **agent skills**: pieces of work that an
LLM agent can execute deterministically, with guard rails (validators) and
scaffolding (templates/workflows) so that the result is close to what a senior
analyst would ship.

## Repository Structure

```
analytics-engineer-agent-skills/
├── SKILL.md                # Top-level skill manifest (agents read this first)
├── README.md               # This file
├── LICENSE                 # Apache License 2.0
├── CONTRIBUTING.md         # How to contribute
├── CHANGELOG.md            # Version history
├── workflows/              # Composable agent workflows (per-task recipes)
├── references/             # Knowledge base articles, guides, style references
├── templates/              # File/project templates (SQL models, TMDL, evals, etc.)
├── scripts/                # Deterministic validators (Python, no LLM required)
│   ├── validate_project.py
│   ├── validate_sql.py
│   ├── validate_dax.py
│   ├── validate_tmdl.py
│   └── quality_check.py
├── evals/                  # Evaluation cases + expected outputs (per skill)
└── docs/                   # Architecture, workflows reference, contribution guide
    ├── architecture.md
    ├── workflows.md
    ├── contribution-guide.md
    └── design-principles.md
```

## Installation & Activation

### Prerequisites

- **Python 3.9+** (3.11 recommended) on Windows, Linux, or macOS.
- Optional, but recommended:
  - `pandas` and `pyarrow` for `quality_check.py` Parquet + richer stats.
  - No LLM API keys are required to run the scripts in `scripts/` — they are
    fully deterministic.

### Standard Install

```bash
# 1. Clone the repository.
git clone https://github.com/Darys21/analytics-engineering-skills.git
cd analytics-engineer-agent-skills

# 2. (Optional) create a virtual environment.
# Windows (py launcher):
py -m venv .venv
.venv\Scripts\activate
# Unix:
# python3 -m venv .venv
# source .venv/bin/activate

# 3. Install optional data-quality dependencies.
pip install pandas pyarrow
```

### Verify Activation

```bash
# 1. Validate the repo itself (Windows: py launcher; Unix: python3).
py scripts/validate_project.py --repo . --verbose

# 2. Validate a sample SQL file (use your own .sql file).
py scripts/validate_sql.py path/to/model.sql

# 3. Profile a CSV.
py scripts/quality_check.py data/raw/sales.csv --json
```

All scripts exit **0 on success**, **non-zero on errors**, and support `--help`.

## Quickstart

Pick the smallest unit of work that matches your task.

### 1. Validate a SQL model before review

```bash
py scripts/validate_sql.py models/sales/sales_fact.sql --strict
```

### 2. Audit DAX measures extracted from a Power BI `.bim` export

```bash
py scripts/validate_dax.py extracts/model.bim --format json --strict
```

### 3. Check a TMDL semantic model (Analysis Services / Fabric)

```bash
py scripts/validate_tmdl.py TmdlModel/ --strict
```

### 4. Profile CSV extract from a source system

```bash
py scripts/quality_check.py data/raw/erp_sales_20260901.csv \
    --range qty:0:100000 \
    --range amount:0:10000000 \
    --primary-key sale_id \
    --datetime-gap-hours 25
```

### 5. Run the entire repo-level validation before committing

```bash
py scripts/validate_project.py --repo . --strict
```

The workflow files in `workflows/` describe how an agent composes these steps
for larger tasks (for example: *onboard a new source system* or *design a
new star schema*). See `docs/workflows.md` for the catalog.

## Validators (scripts/)

| Script | Purpose | Exit 0 means |
|---|---|---|
| `validate_project.py` | Repo structure + internal markdown link checker. | All required files/dirs present; no broken links. |
| `validate_sql.py` | SQL static analysis: anti-patterns, naming, comma style, NULL/agg safety. | No SQL errors detected; warnings with `--strict` also fail. |
| `validate_dax.py` | DAX static analysis: common anti-patterns (nested IF in CALCULATE, ALLSELECTED misuse, missing DIVIDE, etc.). | No DAX errors detected. |
| `validate_tmdl.py` | TMDL structural checks: required fields, relationship integrity, display folders, numeric formats. | No structural errors in the TMDL model. |
| `quality_check.py` | CSV/Parquet data quality: completeness, nulls, uniqueness, IQR outliers, datetime gaps, range checks, PK validation. | No quality errors; warnings with `--strict` / `--fail-on-warnings` also fail. |

Run any script with `--help` for the full list of options and flags.

## Contributing

Contributions are welcome — especially new workflows, reference material,
evaluation cases, and additional validator rules. See:

- `CONTRIBUTING.md` — summary of the process.
- `docs/contribution-guide.md` — detailed walkthrough with examples and the
  review checklist.

## License

This repository is released under the **Apache License 2.0**. See the `LICENSE` file
for the full text.

Official repository: <https://github.com/Darys21/analytics-engineering-skills.git>
