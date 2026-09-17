# Contributing to Analytics Engineer Agent Skills

Thank you for considering a contribution. Every workflow, reference, template,
validator, and evaluation case makes the agent better at doing trustworthy
analytics engineering.

This document gives a **high-level process**; the detailed walkthrough with
examples lives in `docs/contribution-guide.md`.

## 1. What to Contribute

Pick one or more of the following contribution types. Each one has a clear,
reviewable output.

| Type | Directory | Example output |
|---|---|---|
| **Workflow** | `workflows/` | A step-by-step recipe for a repeatable task (e.g. *onboard a new source system*, *design a dimension table*, *review a DAX measure*). |
| **Reference** | `references/` | Knowledge base entry (e.g. *snake_case naming conventions*, *DAX CALCULATE semantics*, *IQR outlier explanation*). |
| **Template** | `templates/` | A file template that the agent can fill in (e.g. `sql_model_template.sql`, `tmdl_table_template.tmdl`, `eval_case_template.md`). |
| **Validator** | `scripts/` | A deterministic Python script that checks a file/object and emits ERROR/WARN/INFO + exit codes. New rules are welcome. |
| **Evaluation** | `evals/` | Input/expected-output pairs that measure whether a workflow produces correct results (golden tests). |

If you are unsure where to start, an **evaluation case** paired with a small
**template** or **reference** is always welcome and easy to review.

## 2. Style Guide

- **English** throughout: filenames, markdown content, code comments, commit
  messages.
- **Markdown**: standard CommonMark. Headings use `#`, `##`, `###`. Code blocks
  specify a language when possible:

  ```markdown
  ```sql
  SELECT customer_id, SUM(amount) AS total_amount
  FROM sales
  GROUP BY customer_id;
  ``` ```

- **Python scripts** (validators):
  - Standard library first. Extra dependencies (`pandas`, etc.) are optional;
    degrade gracefully when they are absent.
  - Full `argparse` `--help`. Use subparsers only when strictly required.
  - Structured `--json` output mode for every validator.
  - Exit codes: `0` for success, `1` for validation failure, `2` for usage /
    IO errors.
  - State **limitations** explicitly in the module docstring. No fake
    validators — say when a check is heuristic or cannot be fully trusted.
- **Naming conventions**:
  - Files and folders: `snake_case.md` or `kebab-case` for readability in
    markdown (both are fine; be consistent within a directory).
  - SQL identifiers: `snake_case` unless the source system forces something
    else.
  - DAX / TMDL objects: `PascalCase` for tables, measures, columns.

## 3. Pull Request Process

1. **Open an issue first** for anything bigger than a typo or a single new
   reference. State the problem you are solving and the expected outcome.
   Small doc fixes, new single-file references, and additional validator
   rules do not need an issue.

2. **Fork and branch** from `main`. Use a descriptive branch name, e.g.
   `add-workflow-onboard-source`, `fix-dax-divide-rule`,
   `new-eval-sql-cte-recommendation`.

3. **Run the repo validator** before committing:
   ```bash
   python scripts/validate_project.py --repo . --strict
   ```
   Fix any ERRORs. If warnings come from areas your PR did not touch, note
   that in the PR description.

4. **Write or update evaluation cases** when your change affects behavior that
   an agent consumes. See `docs/contribution-guide.md` for the eval template.

5. **Open the PR**. In the description include:
   - What the PR changes (one sentence + bullets).
   - How you validated it (validator commands, sample outputs).
   - Any limitations or known follow-ups.
   - Screenshots / copy-pasted terminal output are *great* for validator work.

6. **Address review comments**. At least one approval is required before
   merge. Maintainers squash-merge by default.

## 4. Review Checklist

A reviewer will generally verify the following before approving:

- [ ] Repo validator passes (`validate_project.py --strict`).
- [ ] Naming conventions match the style guide.
- [ ] Any new Python script has a module docstring with limitations clearly
      stated.
- [ ] Any new validator rule has a corresponding evaluation case in
      `evals/`, or the PR description explains why one is not practical.
- [ ] Markdown files render cleanly; internal links are relative and resolve.
- [ ] For new workflows: inputs, outputs, preconditions, and failure modes
      are documented.

See `docs/contribution-guide.md` for the **expanded checklist** with examples
for each contribution type.

## 5. Code of Conduct

Be kind, be precise, assume good intent. When in doubt, ask clarifying
questions in the issue/PR rather than guessing.
