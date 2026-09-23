# Contributing to Analytics Engineer Agent Skills

Thank you for considering a contribution. Every workflow, reference, template,
validator, and evaluation case makes the agent better at doing trustworthy
analytics engineering.

This document gives the architecture overview, contribution recipes, naming
conventions, and review expectations. The detailed walkthrough with examples
lives in `docs/contribution-guide.md`.

---

## 0. Local setup — before you contribute

Install the repository's pinned Python dependencies so validators behave the
same on your machine as in CI. The dependency footprint is intentionally tiny
(one optional dep, `PyYAML`, plus stdlib for everything else).

```bash
# Windows (use py launcher)
py -m venv .venv
.venv\Scripts\activate
py -m pip install --upgrade pip
py -m pip install -r requirements.txt

# Unix / macOS
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

Verify by running:

```bash
# Windows
py scripts/validate_project.py --strict
# Unix
python3 scripts/validate_project.py --strict
```

It should exit 0 on a clean clone with `PyYAML available: yes` in the header.
If you see `PyYAML available: no (using fallbacks)`, re-run the
`pip install -r requirements.txt` step above.

---

## 1. Repository Architecture

This repository has exactly seven top-level directories. Each has a single
responsibility, and new content almost always goes into exactly one of them.

```
analytics-engineering-skills/
├── SKILL.md                # Agent entry point: manifest, routing, operating model
├── workflows/              # Composable, routing-driven procedural recipes
├── references/             # Substantive domain knowledge (loaded on demand)
├── templates/              # Reusable output artifacts (CONTEXT, ADR, DoD, …)
├── scripts/                # Deterministic Python validators / helpers
├── evals/                  # Custom internal behavioral evaluation cases
└── docs/                   # Architecture, workflows catalog, contribution guide
```

Responsibility split — enforced by the progressive-disclosure model:

| Dir | What goes in | When agent reads it |
|---|---|---|
| `workflows/` | Step-by-step procedural *recipe* for a concrete task. Always: Purpose, When to use, Inputs, Prerequisites, Steps, Decisions, Validation, Deliverables, References. | Only after `SKILL.md` has routed the user intent to this workflow. |
| `references/` | *Domain knowledge*: SQL style, DAX semantics, IQR outliers, Power BI, modeling, observability, etc. | Only when a workflow explicitly lists the reference in its "References to load" section. Never pre-loaded. |
| `templates/` | Reusable output *artifacts* that the agent fills in. Format only — no realistic domain content. | When a workflow step tells the agent to produce the artifact. |
| `scripts/` | *Deterministic* Python validators and helpers. Stdlib-only by default; degrade gracefully if `pandas`/`pyarrow` missing. | When a workflow validation step calls the script, or before commit / in CI. |
| `evals/` | Custom internal behavioral *evaluation cases*. Assert expected workflow routing and behaviors (including "expected_not" anti-patterns). | Evaluation harnesses. Schema is validated in CI via `.github/workflows/evals.yml`. |
| `docs/` | *Human-facing* documentation: architecture, catalog of workflows, detailed contribution walkthrough, design principles. | When a human contributor reads the repo. Not loaded by the agent at runtime. |

If the material you want to add does not fit cleanly into one of the above,
ask first — this repository deliberately keeps layers separate.

---

## 2. How to Add Each Component

### 2.1 Add a Workflow

Workflows are composable procedural recipes under `workflows/`.

1. Pick a **kebab-case** filename: `workflows/<task-name>.md`, e.g.
   `workflows/onboard-source-system.md`.
2. Copy the structural sections from an existing workflow (e.g.
   `workflows/business-analysis.md`). Every workflow must include:
   - **Purpose** — one sentence, what this workflow is for.
   - **When to use** — concrete signals in user input that trigger it.
   - **Inputs** — what information is required before starting.
   - **Prerequisites** — what must already be true.
   - **Steps** — ordered numbered list the agent follows.
   - **Decisions** — explicit judgement calls the agent must make.
   - **Validation** — completion criteria.
   - **Deliverables** — concrete files / artifacts produced.
   - **References to load** — one or more relative paths to `references/*.md`.
3. Register the new workflow in the `SKILL.md` **Routing** table so intent
   maps to it.
4. Add a short entry in `docs/workflows.md`.
5. Add at least one evaluation case in `evals/evals.json` that asserts the
   workflow is selected for a representative prompt.
6. Run the validator before committing:
   ```bash
   py scripts/validate_project.py --strict
   ```

### 2.2 Add a Reference

References are substantive domain knowledge under `references/`.

1. Pick a **kebab-case** filename: `references/<topic>.md`, e.g.
   `references/slowly-changing-dimensions.md`.
2. Keep it self-contained. No hidden assumptions about project-specific
   context. No company domain data.
3. **Do not** duplicate knowledge already in another reference; extend or
   link instead.
4. Point one or more existing workflows at the new file by adding the path
   to the workflow's **References to load** list.
5. Run `py scripts/validate_project.py --strict` to confirm cross-links resolve.

### 2.3 Add a Template

Templates are reusable output artifact formats under `templates/`.

1. Pick a **kebab-case** filename and keep extensions matching the artifact
   kind: `templates/ADR.md`, `templates/data-contract.yml`, etc.
2. Content is a *format*, not a real example. Use structural placeholders
   (e.g. `[Project Name]`). Do not embed realistic-looking business data or
   company-specific assumptions.
3. Call out which workflows produce this artifact (link from the workflow's
   Deliverables section).
4. Keep the file generic: remove any company- or domain-specific content
   before merging.

### 2.4 Add a Validator Script

Validators are deterministic Python scripts under `scripts/`.

1. Pick a **snake_case** filename prefixed with `validate_` or descriptive
   action: `scripts/validate_<topic>.py`, `scripts/quality_check.py`.
2. Conventions every script must satisfy:
   - **Stdlib first.** Optional deps (`pandas`, `pyarrow`) must degrade
     gracefully with a clear INFO message when missing — never a hard error.
   - Full `argparse` CLI with `--help`. Subparsers only when strictly required.
   - Structured `--json` output mode (machine-parseable).
   - Exit codes: `0` = success, `1` = validation failure, `2` = usage / IO
     error. Do **not** invent new exit codes.
   - Module docstring with: purpose, inputs/flags, **explicit limitations**,
     and which checks are heuristic vs. deterministic.
   - Never present a heuristic (regex) warning as proof the code is wrong.
     Use `ERROR / WARN / INFO` consistently; reserve `ERROR` for conditions
     the script can reliably establish.
3. Update the **Validators (scripts/)** table in `README.md` so the new
   script appears in the catalog.
4. Add at least one evaluation case in `evals/evals.json` covering a rule
   the new validator enforces (or document why one is impractical in the PR
   description).
5. Confirm: `py scripts/<new-script>.py --help` exits 0 and prints usage.

### 2.5 Add an Evaluation Case

Evaluation cases live in `evals/evals.json` inside the top-level `cases[]`
array. This repository uses a **custom internal behavioral schema** (see
`docs/how-to-use.md` §13 for the schema definition).

1. Append a new object to `cases[]`. Required fields:
   - `id` — unique stable ID, format `eval-NNN`.
   - `title` — short human description.
   - `difficulty` — `"low"` | `"medium"` | `"high"`.
   - `type` — `"positive"` (expect correct routing / behavior) or
     `"negative_near_miss"` (expect the agent to *resist* an anti-pattern).
   - `input` — the exact prompt text.
   - `expected_workflow_routing` — `list[str]` of workflow basenames, e.g.
     `["grill","business-analysis"]`.
   - `expected_behaviors` — `list[str]` of natural-language assertions.
   - `expected_not` — `list[str]` of natural-language anti-pattern assertions.
   - Optionally `references_loaded` — `list[str]` of reference/workflow paths.
2. Test the file parses and passes schema validation before committing:
   ```bash
   # Syntax check
   python -m json.tool evals/evals.json > /dev/null
   # Schema check (inline; matches evals.yml CI)
   python - <<'PY'
   import json, sys
   required = {"id","title","difficulty","type","input","expected_workflow_routing","expected_behaviors","expected_not"}
   with open("evals/evals.json","r",encoding="utf-8") as f:
       data = json.load(f)
   for i, case in enumerate(data["cases"]):
       missing = required - set(case.keys())
       bad = [(k, type(case[k]).__name__) for k in ("expected_workflow_routing","expected_behaviors","expected_not") if k in case and not isinstance(case[k], list)]
       if missing or bad:
           print(f"case #{i} id={case.get('id')}: missing={sorted(missing)} bad_types={bad}")
           sys.exit(1)
   print(f"OK: {len(data['cases'])} cases validated")
   PY
   ```

---

## 3. Naming Conventions

- **English throughout** — filenames, markdown content, code comments, commit
  messages.
- **Filenames in docs, workflows, references, templates:** `kebab-case.md`
  (e.g. `data-discovery.md`, `analysis-report.md`).
- **Python scripts:** `snake_case.py` (e.g. `validate_dax.py`,
  `quality_check.py`).
- **DAX / TMDL / Power BI object names** inside files: `PascalCase` for
  tables, measures, and columns. Example: `[Total Sales Amount]`, table name
  `FactSales`. This convention applies to object identifiers *inside* a file,
  not to the filename itself (which stays kebab-case).
- **SQL identifiers:** `snake_case` unless the source system explicitly
  forces otherwise.
- **Evaluation IDs:** `eval-NNN` zero-padded and monotonically increasing.
- **Branches:** descriptive kebab-case, prefixed with change type, e.g.
  `add-workflow-onboard-source`, `fix-dax-divide-rule`,
  `new-eval-sql-cte-recommendation`.
- **Commit messages:** use conventional commits style (see §5).

---

## 4. Review Checklist

A reviewer will verify the following before approving. Tick these locally
before opening a PR:

- [ ] **Repo validator passes:** `py scripts/validate_project.py --strict`
      exits 0.
- [ ] **Naming conventions** match §3 above; no PascalCase in markdown
      filenames.
- [ ] **New Python scripts** have a module docstring with limitations
      explicitly stated; `py scripts/<script>.py --help` exits 0.
- [ ] **New validator rules** have a corresponding evaluation case in
      `evals/evals.json`, or the PR description clearly explains why one
      is not practical.
- [ ] **Markdown files** render cleanly; internal links are relative and
      resolve (covered by `validate_project.py`).
- [ ] **New workflows** include all mandatory structural sections: Purpose,
      When to use, Inputs, Prerequisites, Steps, Decisions, Validation,
      Deliverables, References to load.
- [ ] **No obsolete filenames.** If you refer to a file from an older repo
      version (e.g. `onboard_source_system.md`, `star_schema_design.md`)
      verify it still exists; remove or update dead references.
- [ ] **No project-specific contamination** in generic templates or
      references. Realistic-looking company- or domain-specific values do not
      belong in reusable generic artifacts.
- [ ] **Technical accuracy.** Claims involving DAX semantics, SQL NULL
      behavior, statistical significance, and performance thresholds are
      appropriately qualified (hard rule vs. heuristic / preferred pattern
      / context-dependent).

---

## 5. Commit Expectations — Conventional Commits

Use the [Conventional Commits](https://www.conventionalcommits.org/) format
for all commit messages. This makes the `CHANGELOG.md` easy to maintain and
automates release notes.

Format:

```
<type>(<scope>): <subject>

<body — optional, wrap at 72 chars>
```

Valid `type` values in this repo:

- `feat` — new workflow, new reference, new validator rule, new eval case.
- `fix` — bug fix in a validator, broken links, routing correction, schema
  fix in evals.
- `docs` — README, CONTRIBUTING, how-to-use, architecture, design docs.
- `refactor` — restructure code/workflow text without changing behavior.
- `perf` — validator performance improvements only (not analytical perf
  guidance; that's `docs` or `feat`).
- `test` — eval cases only when not already part of a `feat`.
- `ci` — GitHub Actions workflow changes.
- `chore` — build/tooling boilerplate, `.gitignore`, license headers.

Scopes are optional but recommended; use the directory name when applicable,
e.g. `feat(workflows):`, `fix(validators):`, `docs(readme):`, `ci(validate):`.

Bad: `update stuff`, `more docs`, `fixed dax thing`.
Good: `feat(workflows): add data-contract reconciliation workflow`
Good: `fix(validators): make DIVIDE rule distinguish hardcoded 0 vs. column`
Good: `docs(how-to-use): add installation troubleshooting section`

Squash-merging is the default on PRs, so you can use WIP / checkpoint
commits locally — just ensure the *squash commit* message follows the
format above before merging.

---

## 6. Pull Request Process & Description Template

### 6.1 Process

1. **Open an issue first** for anything bigger than a typo, a single new
   reference, or an additional single-file validator rule. State the
   problem you are solving and the expected outcome.
2. **Fork and branch** from `main` (see §3 for branch naming).
3. **Run the repo validator** before committing:
   ```bash
   py scripts/validate_project.py --strict
   ```
   Fix all ERRORs. If WARN-level messages stem from files your PR did not
   touch, note that explicitly in the PR description.
4. **Write or update evaluation cases** when your change affects behavior
   the agent consumes. See §2.5 for the eval schema.
5. **Open the PR** against `Darys21/analytics-engineering-skills:main`.
6. **Address review comments.** At least one approval required before
   merge. Maintainers squash-merge by default.

### 6.2 PR Description Template (bullet points)

Fill this structure into the PR description so a reviewer can validate
quickly:

```markdown
## Summary
<!-- One sentence. -->

## What changed
- <!-- Bullet 1: e.g. Added workflow `reconciliation.md` covering ERP/CRM source semantic equality. -->
- <!-- Bullet 2: e.g. Added reference `references/reconciliation-matrix.md`. -->
- <!-- Bullet 3: e.g. Added eval cases eval-016..eval-017. -->

## How I validated
- <!-- e.g. py scripts/validate_project.py --strict → exit 0. -->
- <!-- e.g. py scripts/validate_sql.py test/fixtures/*.sql → no errors. -->
- <!-- e.g. Eval JSON schema check (inline python) → 17 cases validated. -->

## Limitations / follow-ups
- <!-- e.g. Oracle SQL dialect rules not covered (future PR). -->
- <!-- e.g. Heuristic only; no AST parser (documented in validator docstring). -->

## Screenshots / terminal output
<!-- Paste or attach — especially valuable for validator changes. -->
```

Keep descriptions tight and honest. If a validator rule is heuristic, say
so. If a test is impractical, explain why.

---

## 7. Code of Conduct

Be kind, be precise, assume good intent. When in doubt, ask clarifying
questions in the issue/PR rather than guessing.
