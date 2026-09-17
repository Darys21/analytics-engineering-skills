# How to Use This Skill

Practical end-to-end guide for anyone using the `analytics-engineering-skills` repository with an LLM agent.

---

## 1 What the skill is

`analytics-engineering-skills` is a modular, composable TRAE-style skill that gives an LLM agent a structured, opinionated playbook for analytics engineering, business intelligence, and data analysis work. It encapsulates the full lifecycle from an ambiguous business question through to validated, documented delivery.

The skill does **not** hardcode company-specific logic or stack-specific features. It encodes the **methodology** a senior analytics engineer would follow, and provides deterministic validators so the agent can verify its own output before handing work off.

At a high level the repository wraps:

- **SKILL.md** — agent entry point, routing rules, operating principles.
- **workflows/** — step-by-step procedural recipes for concrete tasks.
- **references/** — domain knowledge (SQL, DAX, modeling, statistics, …) loaded on demand.
- **templates/** — reusable output artifacts (CONTEXT, ADR, DoD, analysis report, …).
- **scripts/** — deterministic Python validators (stdlib only by default).
- **evals/** — custom internal evaluation cases that assert expected agent behavior.

---

## 2 What problems it helps solve

The skill was built to eliminate the most common failure modes of analytics work. Trigger it whenever any of the following is requested:

- **Revenue drop analysis** — "Revenue fell 12% week-over-week, why?" Root-cause diagnostic with segmented breakdowns, driver analysis, and explicit distinction between correlation vs. causation.
- **DAX optimization** — "This Power BI measure is slow, make it faster." Baseline correctness → measure bottleneck → rewrite → validate numerical equivalence against baseline.
- **Star schema design** — "Model our orders, shipments, and invoices for BI." Conformed dimensions, correct grain per fact, role-playing dates, semi-additive handling, calculation groups.
- **Daily reconciliation pipeline** — "Reconcile ERP vs. CRM revenue and alert on mismatches." Semantic equality rules, grain checks, reconciliation matrix, idempotent daily run, row-count anomaly alerts.
- **Analytics project review** — "We inherited a dbt + Snowflake + Power BI project with no docs." Structured review across business, data, logic, engineering, performance, security, UX, and ops dimensions.
- **Dashboard UX fix** — "Users say this Power BI report is confusing." Apply Context → KPI → Diagnosis → Detail → Action hierarchy; remove chart junk; add accessible visualizations; verify each visual answers a concrete question.
- **Pipeline ops failure debug** — "Pipeline failed at 06:17 with generic 'job failed'." Observe → reproduce → isolate → hypothesize → test → fix → regression test → document.
- **Source data discovery** — "What data do we have about customers?" Inventory sources, grain, freshness, quality issues, documentation, and lineage; produce a data catalogue snippet.
- **Semantic / TMDL model authoring** — "Model our sales mart in TMDL for Fabric / Analysis Services." Correct structural fields, relationship integrity, display folders, numeric format strings, base measures.
- **SQL query / model validation** — "Review and clean this SQL before production." Anti-pattern detection, NULL and aggregation safety, naming, comma style, deterministic output.

If the problem is ambiguous at the business layer, the skill intentionally routes through the `grill` workflow *before* writing any SQL / DAX / Python.

---

## 3 Installation

Install by cloning into a folder referenced by your agent skill loader. Verify by running `py scripts/validate_project.py --strict`.

Concrete steps:

```bash
# 1. Clone the repository (Windows example, use py launcher)
git clone https://github.com/Darys21/analytics-engineering-skills.git
cd analytics-engineering-skills

# 2. Verify the repo is internally consistent (stdlib only, no deps required)
py scripts/validate_project.py --strict
```

The `SKILL.md` manifest sits at the repository root. Point your TRAE-style agent loader at this folder — the loader reads the YAML frontmatter and registers the skill under `name: analytics-engineering-skills`. Optional Python dependencies (`pandas`, `pyarrow`) are only needed for the richer Parquet / stats modes of `quality_check.py`; the core validators run entirely on Python 3.9+ stdlib.

---

## 4 Activation / triggering

The skill is **description-triggered** via the keywords in its YAML frontmatter. An agent loader inspects the frontmatter `description` field and activates the skill when a user prompt matches any of these signals:

> analytics engineering, data analysis, business analysis, SQL, Python, DAX, TMDL, Power BI, data modeling, data quality, BI, dashboards, statistics, data science, pipelines, ETL, ELT, semantic models, query optimization, data validation, analytical troubleshooting

You do **not** need to explicitly say "use analytics-engineering-skills". Mentioning any of the signals above is sufficient for an agent that supports description-based skill matching.

---

## 5 Typical usage

The skill is designed for natural-language prompts. The following are representative inputs that should route correctly:

```text
Why did revenue decrease?
```

```text
Optimize this DAX measure.
```

```text
Design an analytical data model.
```

```text
Build a daily source reconciliation pipeline.
```

```text
Review this analytics project.
```

Each prompt above is internally routed to a different composition of workflows (see §6). For ambiguous prompts such as "Create a dashboard" the skill first asks high-value clarification questions about persona, decision, KPIs, grain, dimensions, and timeframe before any code is produced.

---

## 6 How routing works

Every request follows this logical chain. Text diagram only:

```
User request
   → skill (activated via trigger keywords in SKILL.md frontmatter)
        → workflow (one or more composable recipes from workflows/)
             → references (only those listed at the top of each workflow, loaded on demand from references/)
                  → execution (agent follows workflow steps; uses templates/ for artifacts and scripts/ for deterministic checks)
                       → validation (workflow completion criteria + Definition of Done + validator scripts)
                            → delivery (structured output via delivery workflow, decisions recorded)
```

Key properties:

- **Routing is intent-based.** The `SKILL.md` routing table maps "what the user says" to "which workflow(s) compose the job".
- **Progressive disclosure.** The agent does **not** pre-load the entire repository. It loads `SKILL.md` first, then only the required workflow file, then only the references *that workflow explicitly points to*.
- **Composability.** Workflows call other workflows. A dashboard request chains `grill → business-analysis → data-modeling → dax/tmdl-analysis → visualization → dashboard-ux → review → delivery`.

---

## 7 CONTEXT.md

`CONTEXT.md` is a **project-specific** file created at the start of a new analytics project by copying `templates/CONTEXT.md` and filling it in. It is **not** a global skill file.

- **When created.** At project kickoff or on the first substantial piece of work for a new codebase / warehouse.
- **What belongs.** Business context, objectives, stakeholders, domain terminology, KPI definitions, data sources, grain, quality issues, architecture, tech stack, constraints, security/privacy rules, conventions, assumptions, known limitations, architecture decisions, operational considerations. Project-specific information only.
- **What does NOT belong.** General analytics knowledge (that belongs in `references/`), company-wide boilerplate not specific to the project, stack tutorials, SQL examples that are not project conventions, or anything a different analytics project would not share.
- **How the skill uses it.** Every workflow starts with "Inspect project context: look for `CONTEXT.md` at the project root and ADRs under `docs/adr/` before reasoning. Never invent project context." If a fact is in `CONTEXT.md`, the agent uses it as ground truth. If it is not, the agent either asks or makes it an explicit assumption.

---

## 8 ADRs

Architecture Decision Records capture *irreversible or material* design decisions.

- **When to record.** Anytime the agent makes a choice that: changes grain, picks a technology, selects a modeling pattern (e.g. SCD Type 2 over SCD Type 1), introduces a new pipeline dependency, affects security posture, or commits to a semantic model design that downstream artifacts will depend on.
- **Why to record.** Decisions are revisited. ADRs prevent the "why on earth did we do this?" conversation six months later; they also let a new agent inherit a project without re-arguing everything.
- **Format.** Use `templates/ADR.md` (the standard ADR: Context / Decision / Consequences). Number sequentially under `docs/adr/NNNN-short-title.md`.

The skill's operating model says: "Record important decisions as ADRs (`templates/ADR.md`) and update project context (`templates/CONTEXT.md`) when they affect future work."

---

## 9 Workflows

### How to discover them

Start from `SKILL.md`: the Routing table maps user intent (what the user actually says) to the primary workflow(s). The file `docs/workflows.md` is the human-readable catalog of every workflow in the repository.

Each workflow file under `workflows/` is self-describing: it states Purpose, When to use, Inputs, Prerequisites, Step-by-step procedure, Decisions the agent must make, Validation criteria, Deliverables, and explicit References to load.

### How to add one

1. Pick a descriptive, hyphenated kebab-case filename: `workflows/<task-name>.md`.
2. Copy the structural sections from an existing workflow (Purpose / When to use / Inputs / Prerequisites / Steps / Decisions / Validation / Deliverables / References).
3. Link to it from the `SKILL.md` routing table and `docs/workflows.md`.
4. Add an evaluation case in `evals/evals.json` that asserts the new workflow is routed correctly.
5. Run `py scripts/validate_project.py --strict` to confirm the new file is referenced and internal links resolve.

---

## 10 References

References are substantive domain knowledge stored under `references/` (SQL style, DAX CALCULATE semantics, IQR outliers, Power BI semantics, data modeling, observability, etc.).

They implement **progressive disclosure**:

- A reference is **never** loaded automatically.
- It is loaded **only** because a workflow explicitly lists it under "References to load" at the top of the workflow file.
- The agent reads a reference *only* for the current task and only after the correct workflow has been selected.

This prevents context overload and keeps prompts small and focused.

To add a reference: create `references/<topic>.md` and point one or more workflows at it via the "References to load" section.

---

## 11 Templates

Templates under `templates/` are reusable **artifact formats** that the agent fills in for concrete output. They ensure consistent, reviewable output across tasks.

Current artifact templates:

- `CONTEXT.md` — project context (see §7).
- `ADR.md` — architecture decision record (see §8).
- `business-question.md` — structured capture of the business question before any analysis.
- `analysis-report.md` — structured write-up of an analysis (Problem / Scope / Data / Methodology / Findings / Recommendations / etc.).
- `definition-of-done.md` — checklist the agent must satisfy to declare a task done.
- `project-structure.md` — recommended project layout for an analytics repository.
- `data-contract.yml` — schema + expectations for a data feed (columns, types, ranges, uniqueness, freshness).

Artifacts are composable: a single task typically produces `business-question.md` plus `analysis-report.md`, with decisions logged as `docs/adr/NNNN-*.md` and project state updated in `CONTEXT.md`.

---

## 12 Validation scripts

All scripts live under `scripts/`, support `--help`, exit `0` on success and `1` on validation failure, and use stdlib only by default (optional `pandas` / `pyarrow` for richer `quality_check.py` behavior).

List of validators:

1. **`scripts/validate_project.py`** — repo-level consistency: required dirs, required files, valid SKILL.md YAML frontmatter, internal markdown link checking, cross-reference existence checks for workflow/reference/template/script mentions. Run before every commit.
   ```bash
   py scripts/validate_project.py --strict
   ```
2. **`scripts/validate_sql.py`** — SQL static analysis: anti-patterns, naming conventions, comma style, NULL / aggregation safety.
   ```bash
   py scripts/validate_sql.py models/marts/mart_sales.sql --strict
   ```
3. **`scripts/validate_dax.py`** — DAX heuristic checks: common anti-patterns (nested IF inside CALCULATE, ALLSELECTED misuse, missing DIVIDE, SUMX simplification candidates, etc.). Heuristic warnings are explicitly tagged as heuristics, never presented as proof of incorrectness.
   ```bash
   py scripts/validate_dax.py extracts/model.bim --format json
   ```
4. **`scripts/validate_tmdl.py`** — TMDL structural checks: required fields, relationship integrity, display folders, numeric formats.
   ```bash
   py scripts/validate_tmdl.py TmdlModel/ --strict
   ```
5. **`scripts/quality_check.py`** — CSV / Parquet data quality: completeness, null ratios, uniqueness, IQR outliers, datetime gaps, range checks, primary-key validation.
   ```bash
   py scripts/quality_check.py data/raw/erp_sales.csv \
       --range qty:0:100000 \
       --primary-key sale_id \
       --datetime-gap-hours 25
   ```

Windows users are encouraged to use the `py` launcher rather than `python` to pick up the correct interpreter automatically.

---

## 13 Evaluations

`evals/evals.json` is a **custom internal behavioral evaluation schema**. It is not an Anthropic, OpenAI, or HuggingFace format — it is specific to this repository and used by (future) evaluation harnesses to assert that an agent routes and behaves correctly when using the skill.

Top-level structure:

- `version` — schema version.
- `description` — what the eval file covers.
- `cases[]` — one entry per evaluation case.

Each case currently carries:

- `id` — stable identifier (`eval-NNN`).
- `title` — human short description.
- `difficulty` — low / medium / high.
- `type` — positive (expect correct routing) or `negative_near_miss` (expect the agent to *resist* an anti-pattern).
- `input` — the prompt text.
- `expected_workflow_routing[]` — which workflows should be selected.
- `expected_behaviors[]` — concrete behaviors the agent must exhibit (phrased as natural-language assertions, not code).
- `expected_not[]` — concrete behaviors the agent must **not** exhibit.
- `references_loaded[]` — optional, asserts which reference files are loaded.

Cases cover both "do the right thing" (positive) and "don't do the wrong thing" (near-miss negatives such as over-engineering, over-questioning, p<0.05 → ship-it, etc.). Schema validation is enforced in CI via `.github/workflows/evals.yml`.

---

## 14 Contributing

Contributions are welcome — new workflows, reference articles, templates, validator rules, and evaluation cases all directly improve the skill.

See `CONTRIBUTING.md` in the repository root for:

- Which directory each contribution type lives in.
- Naming conventions (kebab-case `.md` for docs/workflows/references; PascalCase for Power BI/TMDL object names inside files but not in filenames).
- The review checklist.
- Pull-request process and expectations.
- Conventional-commit style for commit messages.
- The expanded checklist in `docs/contribution-guide.md` for examples of each contribution type.

---

## 15 Troubleshooting

### `validate_project.py` fails

- Run with `--verbose` to see exactly which file or link triggered the failure.
- If `--strict` fails on warnings from files your changes did not touch, note that in your PR description — but always confirm the warning is not newly introduced by your branch.
- Typical fix: a markdown link in a workflow or reference points to a file that was renamed or a reference no longer exists. Resolve or remove the link.
- Verify the Python invocation (Windows: prefer `py` launcher; Unix: `python3`). If `py` is not found, install the [Python Launcher for Windows](https://docs.python.org/3/using/windows.html#launcher) or fall back to `python -m scripts.validate_project …` with the correct interpreter on PATH.

### Broken internal links

`validate_project.py` catches relative links in markdown that do not resolve. Fix the link target or — if the target was intentionally removed — delete the reference. Do not add placeholder links that point to nothing.

### Python not on PATH (Windows)

On Windows, prefer the `py` launcher (`py scripts/validate_project.py --strict`) over `python` or `python3`. The launcher auto-discovers the latest installed interpreter and avoids PATH issues. If `py` itself is unavailable, repair your Python installation and select "Add Python to PATH" during setup; alternatively invoke the full path to `python.exe` explicitly.

### JSON syntax in `evals/evals.json`

CI runs both `python -m json.tool evals/evals.json > /dev/null` (pure syntax check) and a schema-validation step that verifies every case has all required keys with correct types. If the schema step fails, the error output lists the case `id` and which field is missing or typed incorrectly. Patch the case and re-run locally with:

```bash
python - <<'PY'
import json, sys
required = {"id","title","difficulty","type","input","expected_workflow_routing","expected_behaviors","expected_not"}
with open("evals/evals.json","r",encoding="utf-8") as f:
    data = json.load(f)
for i, case in enumerate(data["cases"]):
    missing = required - set(case.keys())
    bad = []
    for k in ("expected_workflow_routing","expected_behaviors","expected_not"):
        if k in case and not isinstance(case[k], list):
            bad.append((k, type(case[k]).__name__))
    if missing or bad:
        print(f"case #{i} id={case.get('id')}: missing={sorted(missing)} bad_types={bad}")
        sys.exit(1)
print(f"OK: {len(data['cases'])} cases validated")
PY
```
