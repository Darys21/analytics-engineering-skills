---
name: analytics-engineering-skills
description: Modular analytics engineering skill. Trigger for: analytics engineering, data analysis, business analysis, SQL, Python, DAX, TMDL, Power BI, data modeling, data quality, BI, dashboards, statistics, data science, pipelines, ETL, ELT, semantic models, query optimization, data validation, analytical troubleshooting.
---

# Analytics Engineering Skills Repository

## Identity

General-purpose analytics engineering and data intelligence skill system. Covers the full analytics lifecycle from ambiguous business question through validated, maintainable delivery. Technology-aware but technology-independent.

## Mission

Help AI agents transform ambiguous business and data problems into validated, maintainable analytical solutions by applying rigorous methodology, progressive disclosure, and composable workflows.

## Operating Model

High-level workflow for every substantial task:

1. **Detect task type** from user intent.
2. **Determine whether clarification is required.** If the business problem, grain, or constraints are materially ambiguous, run the `grill` workflow. Do not ask questions whose answers cannot change the solution.
3. **Inspect project context.** Look for `CONTEXT.md` at the project root and ADRs under `docs/adr/` before reasoning. Never invent project context.
4. **Select the appropriate workflow(s)** from `workflows/`. Workflows compose. Do not force unnecessary workflows.
5. **Load only relevant references** from `references/`. Load by pointer from the workflow. Do not read the entire repository for every task.
6. **Execute** the workflow procedure. Use `templates/` for artifacts, `scripts/` for deterministic validation.
7. **Validate** against the workflow's completion criteria and the project's Definition of Done (`templates/definition-of-done.md`).
8. **Review** using the `review` workflow when scope, impact, or risk is non-trivial.
9. **Deliver** using the `delivery` workflow.
10. **Record important decisions** as ADRs (`templates/ADR.md`) and update project context (`templates/CONTEXT.md`) when they affect future work.

## Problem-Solving Framework

Core reasoning flow: **UNDERSTAND → SIMPLIFY → DECOMPOSE → SOLVE → TEST → MEASURE → EXPLAIN → IMPROVE**.

### Understand
objective, stakeholders, context, constraints, desired outcome, available information.

### Simplify
remove unnecessary complexity, identify actual question, distinguish symptoms from problems, strip unnecessary technical requirements.

### Decompose
business problem, data requirements, transformations, analytical logic, semantic model, presentation, validation, delivery.

### Solve
Select methodology and technology based on the problem, never personal preference. Descriptive before diagnostic before predictive before ML.

### Test
correctness, data quality, assumptions, edge cases, business logic, performance, reproducibility.

### Measure
requirements, baseline, expected behavior, KPIs, performance targets.

### Explain
Audience-appropriate. Trade-offs, not only steps.

### Improve
weaknesses, technical debt, monitoring, automation, future improvements.

## Routing

Select workflow(s) by intent. Compose rather than replace.

| User says (examples) | Primary workflow(s) |
|----------------------|---------------------|
| "Why did KPI change?", "What drives revenue?" | business-analysis → data-discovery → statistics |
| "What data do we have?", "Where is X stored?" | data-discovery → data-quality |
| "Fix duplicates", "Data is wrong" | diagnose → data-quality → reconciliation |
| "Build a model", "Star schema" | data-discovery → data-modeling → analytics-engineering |
| "ETL/ELT", "Daily pipeline" | analytics-engineering → pipeline → observability |
| "Write SQL", "Query this" | sql-analysis → data-quality |
| "Analyze in Python", "Notebook" | python-analysis → statistics |
| "DAX measure", "Power BI calc" | dax-analysis → review |
| "TMDL / semantic model", "PBIP export" | tmdl-analysis → dax-analysis → review |
| "Forecast", "Predict" | grill → statistics → data-science only if baseline insufficient |
| "Chart this", "Visualize" | visualization → business-analysis |
| "Dashboard", "Report" | grill → business-analysis → data-modeling → dax/tmdl → visualization → dashboard-ux → review |
| "Optimize this query / measure / pipeline" | diagnose → optimize → measure against baseline |
| "Review this project / code / dashboard" | review (all dimensions) |
| "Anything unclear" *before* coding | grill |

If the intent is genuinely ambiguous, enter `grill` first. Never jump into SQL/Python/DAX before the business question and grain are pinned.

**Optional worked example:** `references/ecommerce-retail-case-study.md` illustrates personas, grain, KPI hierarchy, and Context → KPI → Diagnosis → Detail → Action on a retail dashboard. Use only when you need a concrete illustration of good structure. Never force retail metrics (RFM, CLV, market basket, etc.) onto other domains — always re-derive from the current brief via `grill` + `business-analysis`.

## Progressive Disclosure

1. Read this file (`SKILL.md`).
2. Identify the relevant workflow from routing above.
3. Read only that workflow file from `workflows/<name>.md`.
4. Load only the `References to load` listed at the top of the workflow from `references/`.
5. Use templates (`templates/`) and scripts (`scripts/`) only when the workflow says so.

Do not read every reference up-front. Context overload degrades output.

## Quality Expectations

- **Business before technology.** If the problem is unclear, clarify first.
- **Explicit assumptions.** Every unvalidated assumption surfaces in the output.
- **Validate before declaring done.** Use the workflow's completion criteria and the Definition of Done.
- **Reproducible and maintainable** over clever.
- **No fake certainty.** State uncertainty; distinguish statistical significance from business meaning.
- **No secrets in code.** No PII in examples.
- **Simplest valid solution.** Descriptive analytics wins when sufficient.

## Completion

Before closing a task, verify:
- Business problem actually solved.
- Grain, KPI definitions, and assumptions are explicit.
- Data validated (quality, duplicates, nulls, grain).
- Code / transformations tested or reconciliation-provable.
- Output usable by the intended audience.
- Important decisions captured (ADR / CONTEXT.md where appropriate).
- No claims of testing that was not performed.

---

## Repository Layout

```
SKILL.md                     <- this file
workflows/                   <- composable, routing-driven procedures
references/                  <- substantive domain knowledge (loaded on demand)
templates/                   <- reusable project artifacts (CONTEXT, ADR, DoD, etc.)
scripts/                     <- deterministic validators / helpers
evals/                       <- evaluation cases (expected behavior)
docs/                        <- architecture, design, contribution docs
README.md                    <- repository entry point
LICENSE / CONTRIBUTING.md    <- open-source scaffolding
CHANGELOG.md                 <- release tracking
```

See `docs/architecture.md` for detailed responsibilities and extension points.
