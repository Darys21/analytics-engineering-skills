# Contribution Guide — Detailed Walkthrough

This guide is the **expanded version** of the high-level process described in
`CONTRIBUTING.md`. Read it when you are ready to add a new workflow, a new
reference, a new template, a new validator (or validator rule), or a new
evaluation case.

---

## 1. Prerequisites

Before any contribution:

1. **Read the design principles** in `docs/design-principles.md`. Every
   contribution should be consistent with them. If a principle feels like it
   blocks a genuinely good idea, open an issue *about the principle* first —
   they are intentionally slow to change, but they do evolve.
2. **Fork the repo** and create a branch. Descriptive branch names:
   - `add-workflow-onboard-source`
   - `new-ref-dax-calculate-semantics`
   - `add-template-tmdl-table`
   - `validator-sql-new-rule-distinct-on-agg`
   - `eval-quality-check-iqr-floats`
3. **Run `validate_project.py --strict` on the base `main`** so you know the
   baseline before you start.
   ```bash
   python scripts/validate_project.py --repo . --strict
   ```

---

## 2. Add a New Workflow

Use this walkthrough when you are documenting a repeatable agent task (for
example: "review a DAX measure" or "design a slowly-changing dimension").

### Step 2.1 — Copy the template or create the sections

Start with this skeleton in `workflows/<your-new-id>.md`:

```markdown
# <Human-friendly title>

- **ID**: `<your-new-id>` (matches filename without extension)
- **Status**: Draft / Approved
- **Owner**: @<github-handle or team name>
- **Last reviewed**: YYYY-MM-DD

## Inputs

What must exist or be true before the workflow starts.
Be concrete: list specific files, permissions, or preconditions.

- …

## Steps

Ordered list of atomic actions. Each step references the **reference** the
agent should read (if any) and the **template** to fill (if any). At the end
of a step, note which **validator** should run and whether `--strict` is
required.

1. **<Step title>**
   - Read: `references/<name>.md`
   - Use: `templates/<name>.sql`
   - Output: `<artifact produced>`
   - Gate: `python scripts/validate_<x>.py <path> --strict` (exit 0)
2. …

## Validator Gates (summary)

Copy-paste the gates from each step here so a reviewer can check them
without reading the whole workflow.

| Step | Script | Strict? |
|---|---|---|
| N | `scripts/validate_<x>.py` | Yes / No |

## Outputs

Artifacts delivered by the workflow, and which workflow consumes them next
(or "for human review" if none).

- …

## Failure Modes

List what can go wrong, how to detect it, and how to escalate:

- **<Failure name>** — How to detect. Action: (rerun previous step / escalate
  to warehouse admin / stop and ask human).
```

### Step 2.2 — Fill in content, keep it tight

- Steps should be **atomic** — one decision, one artifact, one validator run
  per step at most.
- If a step would be 50 lines long, it is two steps.
- Reference material lives in `references/`; **do not copy it into the
  workflow**. Link to it.

### Step 2.3 — Add to the catalogs

1. Add a row to the table in `docs/workflows.md`.
2. Add a one-line entry in `SKILL.md` under the workflows section.

### Step 2.4 — Add at least one evaluation case

Create `evals/<your-new-id>/case-001-basic/` with:

- `inputs/` (fixture files)
- `expected_outputs/` (golden files or assertions file)
- `README.md` explaining how to run.

### Step 2.5 — Validate

```bash
python scripts/validate_project.py --repo . --strict
```

---

## 3. Add a New Reference

Use this when you are adding facts the agent should *know* but that are not
the steps to do a job (for example: "DAX CALCULATE semantics", "snake_case
naming conventions", "IQR outlier detection explanation").

### Step 3.1 — Decide the scope

A reference should be **one concept, roughly one page or less**. If you feel
you need ten pages, split into sub-topics (e.g. `dax_calculate_semantics.md`,
`dax_context_transition_examples.md`, `dax_allselected_gotchas.md`) and
cross-reference them from an index.

### Step 3.2 — Structure

References live in `references/<id>.md`. Recommended sections:

```markdown
# <Title>

- **Ref ID**: `<id>` (matches filename)
- **Used by workflows**: `<workflow-id-1>`, `<workflow-id-2>` …

## Summary

One-paragraph executive summary of the concept.

## Details

The facts. Use code blocks liberally; label SQL/DAX/TMDL snippets so they
can be copied.

## Anti-patterns

What people (or agents) commonly get wrong, and why. Pair each anti-pattern
with a preferred alternative.

## Further reading

Links to external documentation, if any. Prefer official vendor docs.
```

### Step 3.3 — Link to it from consuming workflows

In every workflow step that relies on this knowledge, add a `Read:
references/<id>.md` line. Otherwise the agent will never open the reference.

---

## 4. Add a New Template

Use this when the agent is producing a file whose *shape* is predictable but
whose *content* varies (for example: a SQL model, a TMDL table stub, a
review checklist, an evaluation case).

### Step 4.1 — Decide placeholders

Placeholders use the `<UPPER_SNAKE_CASE>` convention so they are easy to
find. For example: `<TABLE_NAME>`, `<PRIMARY_KEY_COLUMN>`,
`<VALIDATOR_FLAGS>`.

### Step 4.2 — Add a header that links to documentation

Every template file should start with a comment or frontmatter that tells
the agent:

- Which workflow uses this template.
- Which reference to read before filling it in.
- Which validator to run after filling it in.

Example for a SQL template:

```sql
-- SQL model template
-- Workflow  : workflows/create_star_sql.md
-- Reference : references/sql_style.md, references/sql_cte_patterns.md
-- Validate  : python scripts/validate_sql.py <this-file> --strict
-- Placeholders:
--   <TABLE_NAME>       Name of the target dimension/fact
--   <PRIMARY_KEY>      Surrogate or natural key column
--   <SOURCE_CTES>      WITH clause CTEs for each source
```

### Step 4.3 — Reference it from the workflow

In the workflow step that produces the file, add:

```
- Use: `templates/sql_model_template.sql`
```

---

## 5. Add a New Validator Rule

Use this when an existing `validate_*.py` script should have an additional
check.

### Step 5.1 — Decide which script

| Scope | Script |
|---|---|
| Repo structure, markdown links | `validate_project.py` |
| SQL anti-patterns / style | `validate_sql.py` |
| DAX anti-patterns | `validate_dax.py` |
| TMDL structure / relationships | `validate_tmdl.py` |
| Data quality (CSV/Parquet) | `quality_check.py` |

### Step 5.2 — Follow the rule-authoring pattern

In every script, rules follow a consistent pattern:

1. **Define** the check as its own function
   `check_<rule_id>(stripped, original, file_ref, issues, […]).`
2. **Register** it in the per-file analyzer wrapped in
   `if "<rule_id>" not in disabled`.
3. **Document** the rule ID and what it checks in the script's module
   docstring, under *Limitations* or a dedicated *Checks performed* section.
4. **Emit** `ERROR` if the issue is almost always wrong and blocks review.
   Emit `WARN` if it's a heuristic (false positives possible). Emit `INFO`
   only for information that is useful in `--verbose` but never blocks.
5. **Add** a CLI `--disable <rule_id>` escape hatch.

### Step 5.3 — Add eval cases that both pass and fail

- `evals/<script>/rule-<rule_id>/should_fail_001.sql` (or `.dax`, `.tmdl`,
  `.csv`).
- `evals/<script>/rule-<rule_id>/should_pass_001.sql`.

Assert in the eval README:

```bash
# must exit 1 or 0 respectively
python scripts/validate_sql.py evals/validate_sql/rule-select_star/should_fail_001.sql
python scripts/validate_sql.py evals/validate_sql/rule-select_star/should_pass_001.sql
```

### Step 5.4 — Do not fake validation

If your rule is heuristic, it **must** emit `WARN` or `INFO`, not `ERROR`,
and you **must** say so in the module docstring. When in doubt, lower
severity and document.

---

## 6. Add a New Validator Script

Use this when none of the five existing scripts covers the thing you need to
validate (for example: YAML configuration files, dbt YAML schemas, Power BI
`pbit` manifest XML, Terraform HCL).

### Step 6.1 — Honor the validator contract

Re-read the **Contract for Anything in `scripts/`** table in
`docs/architecture.md`. These are non-negotiable: pure / no network / no LLM
/ `--help` / `--json` / exit codes 0-1-2 / limitations docstring / graceful
optional-deps.

### Step 6.2 — Register it

- Add the script filename to `README.md`'s validator table.
- Add the script filename to the `required_scripts` list in
  `scripts/validate_project.py` so the repo validator enforces its presence.
- Add a docs section: what it does, a CLI example, its limitations.

---

## 7. Add a New Evaluation Case

Use this whenever you add a workflow, a template, or a new validator rule.
Without evals you cannot prove the agent is getting better (or at least not
getting worse).

### Step 7.1 — Layout

```
evals/
  <workflow-or-script-id>/
    README.md                 ← how to run this eval
    case-001-<descriptive-name>/
      inputs/
        source.csv
        raw_query.sql
      expected_outputs/
        staging_table.sql
        assertions.json
```

### Step 7.2 — `assertions.json` format (recommended)

For evaluators that are not strict golden-file tests:

```json
{
  "eval_id": "validate_sql/rule-select_star/should_fail_001",
  "script": "scripts/validate_sql.py",
  "args": ["inputs/should_fail_001.sql"],
  "expected_exit_code": 1,
  "expected_issue_rules": ["select_star"],
  "expected_min_errors": 1
}
```

### Step 7.3 — Run it locally and record the result

Open the eval's `README.md` with:

```markdown
# Eval: <case>

## How to run

```bash
# from repo root
python scripts/validate_sql.py evals/validate_sql/rule-select_star/case-001/inputs/should_fail_001.sql
echo $?
```

## Expected

- Exit code: 1
- At least one issue with rule `select_star`
- Severity: WARN
```

---

## 8. Naming Conventions Cheat Sheet

| Thing | Convention | Example |
|---|---|---|
| Workflow files | `<verb-or-topic>_<descriptive>.md` | `onboard_source_system.md` |
| Reference files | `<topic>_<detail>.md` | `dax_calculate_semantics.md` |
| Template files | `<type>_<scope>_template.<ext>` | `sql_model_template.sql` |
| Validator scripts | `validate_<scope>.py` or `<noun>_check.py` | `validate_dax.py`, `quality_check.py` |
| Validator rule IDs | `snake_case`, descriptive | `select_star`, `distinct_count`, `divide_missing` |
| Eval case dirs | `case-NNN-<short-slug>` | `case-001-cte-with-subquery` |
| SQL identifiers | `snake_case` | `customer_key`, `order_total_amount` |
| DAX measures | `PascalCase` | `TotalSales`, `AvgDiscountPct` |
| TMDL objects (table / column / measure) | `PascalCase` | `Sales`, `SalesAmount` |
| Placeholders in templates | `<UPPER_SNAKE_CASE>` | `<TABLE_NAME>`, `<PRIMARY_KEY>` |

---

## 9. Review Checklist — Expanded

Before you mark a PR **ready for review**, verify every row that applies.
The reviewer will go through the same checklist.

### For *any* PR

- [ ] `python scripts/validate_project.py --repo . --strict` exits 0.
- [ ] CHANGELOG.md updated under `[Unreleased]` with one bullet describing the change.
- [ ] No large blocks of copy-pasted content across files (use cross-links instead).
- [ ] All markdown uses CommonMark; code blocks name the language.

### For *new workflow* PRs

- [ ] Workflow file includes the 5 sections: Inputs / Steps / Validator Gates / Outputs / Failure Modes.
- [ ] Each step references a template (if applicable) and a reference (if judgment is required).
- [ ] Added to `docs/workflows.md` table.
- [ ] Added a one-line entry in `SKILL.md`.
- [ ] At least one evaluation case exists in `evals/<workflow-id>/`.

### For *new reference* PRs

- [ ] Reference is about one concept; roughly ≤ 2 pages.
- [ ] References are linked from at least one workflow step.
- [ ] Anti-patterns section when the concept has common mistakes.

### For *new template* PRs

- [ ] Header comment names the consuming workflow, relevant reference, and validator command.
- [ ] Placeholders follow `<UPPER_SNAKE_CASE>` convention.
- [ ] At least one eval case exists that fills the template and runs the validator.

### For *new validator rule* PRs

- [ ] Rule function exists and is registered in the per-file analyzer.
- [ ] Rule can be disabled via `--disable <rule_id>`.
- [ ] Severity is ERROR only for obviously-wrong patterns.
- [ ] Module docstring documents the rule.
- [ ] Should-fail and should-pass eval cases exist.

### For *new validator script* PRs

- [ ] Full `--help` output describes every flag.
- [ ] `--json` mode produces valid, schema-stable JSON.
- [ ] Exit codes: 0 pass / 1 fail / 2 usage or IO error.
- [ ] Module docstring **honestly** lists limitations.
- [ ] Optional dependencies degrade gracefully.
- [ ] Registered in `README.md` validator table.
- [ ] Registered in `validate_project.py` required-scripts list.

### For *new eval case* PRs

- [ ] README describes how to run and expected exit code / assertions.
- [ ] Fixture inputs are small (well under 1MB), realistic, and anonymized.
- [ ] Expected outputs are committed as golden files or as `assertions.json`.
