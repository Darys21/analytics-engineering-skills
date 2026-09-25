# Architecture

This document describes the responsibilities of each directory in the
repository, how the pieces compose, the **progressive disclosure** model that
lets an agent start simple and scale to complex tasks, and the extension points
for contributors.

## High-level View

The repository is a **layered toolkit** for an Analytics Engineering agent.

```
┌───────────────────────────────────────────────────────────────┐
│                     Agent / Orchestrator                       │
│  (reads SKILL.md, picks workflows, reads references, uses      │
│   templates, runs validators, measures with evals)             │
└──────┬───────────┬───────────┬───────────┬───────────┬────────┘
       │           │           │           │           │
       ▼           ▼           ▼           ▼           ▼
  workflows/   references/  templates/   scripts/    evals/
   (recipes)   (knowledge)   (blanks)   (checks)   (tests)
```

**Workflows** say *what to do, in what order*.  
**References** say *how and why each step is correct*.  
**Templates** give the agent a head start so every file is structured.  
**Scripts** deterministically verify the result.  
**Evals** measure quality over time so regressions are visible.

## Responsibilities per Directory

### `SKILL.md` (root)

Single entry point that an orchestrating agent reads *first*. It should be
short: a mission statement, a table of contents for workflows and references,
and pointers to the five validator scripts. It must never contain deep
technical detail — those live in `references/` and `docs/`.

### `workflows/`

Each file in `workflows/` is one **composable recipe** for a repeatable task.
A workflow is *not* code; it is prose with structured checklists. Every
workflow lists:

- **Inputs**: what must be true before running (e.g. "raw CSV landed in
  staging", "ERD of the source system exists").
- **Steps**: ordered, atomic actions. Each action references a template
  (from `templates/`) where applicable, and references (from `references/`)
  when the agent needs to *decide* something.
- **Validator gates**: which scripts in `scripts/` to run at the end of the
  step, and whether `--strict` should be used.
- **Outputs**: artifacts produced, and how to hand them to the next workflow.
- **Failure modes**: what can go wrong, and how to escalate to a human.

### `references/`

Reference material that the agent consults when it needs to make a judgment
call. Naming conventions, SQL style, DAX best practices, TMDL allowed
patterns, data-quality expectations, how to handle slowly-changing
dimensions, etc. References are **facts, not recipes** — workflows are the
recipes that consume references.

### `templates/`

Head-start files that the agent fills in. Each template has clearly marked
placeholders (e.g. `<TABLE_NAME>`, `<PRIMARY_KEY>`) and a header comment that
links to the reference and workflow that govern filling it in. The goal of a
template is to *remove blank-page anxiety* and guarantee consistent structure
without replacing engineering judgment.

### `scripts/`

**Deterministic validators.** They take a file or directory as input, run
checks, emit structured issues (ERROR / WARN / INFO), and return exit codes
0 / 1 / 2. Validators never call an LLM and never require a network
connection — they must be runnable offline on a developer's laptop.

Existing validators:

| Script | Scope |
|---|---|
| `validate_project.py` | Repository structure + markdown links. |
| `validate_sql.py` | SQL anti-patterns, style, naming. |
| `validate_dax.py` | DAX measure anti-patterns. |
| `validate_tmdl.py` | TMDL structure, relationships, naming. |
| `quality_check.py` | CSV/Parquet data quality + statistics. |

### `evals/`

Golden tests. Each evaluation case is:

1. **Inputs** (fixture files).
2. **Workflow invoked**.
3. **Expected outputs** (either exact golden files or structured assertions
   like "`validate_sql.py --strict` must exit 0 on the produced model").

Evaluations are the guardrails that let us change templates, add validator
rules, or rewrite workflows without silently making the agent worse.

### `docs/`

Long-form documentation *for humans contributing to the repository*:
architecture, workflow catalog, contribution guide, the design-principles
manifesto. Material in `docs/` is not consumed by the agent during normal
operation — it is consumed by humans maintaining and extending the agent.

## Composability Model

Workflows compose horizontally and vertically:

- **Horizontal composition**: an *onboard-source-system* workflow invokes
  *profile-source-data* → *design-staging-schema* → *create-staging-sql* →
  *review-staging-sql* → *run-data-quality-checks*. Each of those is its own
  workflow file; the parent workflow just orders them and passes outputs.
- **Vertical composition**: workflows nest. A *star-schema-design* workflow
  might call *dimension-table-design* for each dimension and
  *fact-table-design* for each fact.

A workflow never implements steps by copying them from another workflow.
Instead it references the other workflow by filename. This way improvements
propagate automatically.

## Progressive Disclosure Model

Agents (and humans) suffer from context limits. The repository is structured
so that the agent only loads what it needs:

1. **Step 0 — just the entry point.** The agent starts by reading only
   `SKILL.md` (≈ 1 page). That gives it a mission and a list of workflows
   with a one-line summary each.
2. **Step 1 — load the workflow.** It reads exactly one workflow file that
   matches the current task.
3. **Step 2 — load references on demand.** When a workflow step says "see
   `references/dax_calculate_semantics.md`", the agent reads that reference
   *just before* that step, not earlier.
4. **Step 3 — use templates to produce artifacts.** A step references
   `templates/sql_model_template.sql`; the agent fills it in.
5. **Step 4 — run validators to verify.** Validators are invoked only on
   files the agent just wrote, not on the whole repository.
6. **Step 5 — run evaluation cases.** When the workflow is "done", the
   evaluator runs `evals/<case>/` and compares expected vs actual.

Consequence: almost every file in the repo should be *small* and
*single-purpose*. If a reference exceeds ~2 pages, split it into subtopics
and cross-reference them from an index reference.

## Extension Points

Contributors can extend the repository without breaking existing agents by
sticking to these extension points:

1. **New workflow**: add a file to `workflows/`. If it reuses other
   workflows, reference them by filename. Register a one-line summary in
   `SKILL.md` so the agent can discover it. Add evaluation cases in
   `evals/`.
2. **New reference**: add a file to `references/`. Link to it from any
   workflow whose steps rely on that knowledge.
3. **New template**: add a file to `templates/`. Link to it from the
   workflow that uses it. Add a reference that explains how to fill it if
   the placeholders are non-obvious.
4. **New validator rule in an existing script**: add a check function in
   the appropriate `validate_*.py`, make it toggleable via `--disable` /
   CLI flags, document the rule in the script's module docstring, and add
   eval cases that both pass and fail.
5. **New validator script**: add to `scripts/`, satisfy the validator
   contract (argparse, `--json`, `--help`, exit codes 0/1/2, documented
   limitations), add an entry to `README.md` and to
   `validate_project.py`'s required-scripts list.
6. **New evaluation case**: add a directory under `evals/` with inputs,
   the workflow id, and expected outputs. Register it in an eval index
   (see `evals/README-template.md`).

## Contract for Anything in `scripts/`

Anything that lives in `scripts/` must honor this contract:

| Aspect | Requirement |
|---|---|
| Pure function | Same inputs → same outputs (no time or RNG-based logic). |
| No network | Must run fully offline. |
| No LLM calls | Deterministic only. |
| `--help` | Full argparse help that describes every flag. |
| `--json` | Structured machine-readable output mode. |
| Exit codes | `0` = pass, `1` = validation failure, `2` = usage / IO / env error. |
| Limitations docstring | Module docstring must explicitly state what the script *cannot* reliably check. No fake validators. |
| Dependencies | Prefer stdlib. Optional deps (pandas, etc.) are allowed only if the script degrades gracefully without them. |

This contract is enforced by `validate_project.py` (which checks that each
script exists) and by the review checklist in `CONTRIBUTING.md`.
