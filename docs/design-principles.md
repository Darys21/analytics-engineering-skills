# Design Principles

These 25 principles govern every contribution to the Analytics Engineer Agent
Skills repository. They are ordered approximately from *philosophical* to
*tactical*. Principles near the top tend to trump principle-specific tradeoffs
near the bottom, but all 25 should be read and applied as a whole.

When a contribution conflicts with a principle, prefer adjusting the
contribution. If you believe a principle itself needs to change, open an
issue describing the conflict and the proposed revision — principles evolve,
but slowly and deliberately.

---

## 1. Determinism over cleverness

Given the same inputs, any script, workflow step, or template fill must
produce the same output every time. Avoid randomness, avoid wall-clock-based
logic, avoid non-seeded hashing. The agent should be able to rerun a task and
compare results byte-for-byte.

## 2. No fake validators

If a validator cannot check something reliably, **say so explicitly** in the
module docstring. Emit `WARN` or `INFO`, never `ERROR`, for heuristic checks.
A validator that silently produces false confidence is worse than no
validator at all.

## 3. Progressive disclosure

Load only what the agent needs for the step it is currently on. Keep
`SKILL.md` short, keep workflows short, keep references focused on one
concept each. Context is a scarce resource for both humans and LLMs.

## 4. Composition over monoliths

Every workflow should be an atomic, composable unit. Big jobs are built by
stringing small workflows together, not by writing one 50-step mega-workflow.
If workflow B needs exactly what workflow A produces, B should reference A,
not copy its steps.

## 5. Evaluation-first

If you cannot write a simple evaluation case (input → expected output, or
input → validator exit codes), the task is probably not well-defined yet.
Every new workflow, every validator rule, and every template should ship
with at least one pass and one fail evaluation case.

## 6. Documented limitations, every time

Every script, every workflow, and every non-trivial reference must state
what it **does not** cover. Limitations are not bugs to hide; they are a
feature that lets the agent and the reviewer know when to escalate to a
human.

## 7. Exit codes are a contract

For anything in `scripts/`: `0` = pass, `1` = validation failure, `2` =
usage / environment / IO error. Do not overload exit codes with additional
meanings. Orchestrators rely on this.

## 8. Structured output everywhere

Every validator supports `--json` with a stable schema (same top-level keys
today and in a year). Orchestrators parse JSON; humans read `--verbose`
table output. Both are first-class citizens.

## 9. Standard library first, optional degrades gracefully

Prefer the Python standard library in `scripts/`. If a dependency like
`pandas` provides real value, make it optional and degrade to a stdlib
fallback with clear, documented behavior when the dependency is absent.

## 10. The agent reads like a human, writes like an engineer

Templates, references, and workflows should be understandable by a senior
analyst sitting next to you. If you would be embarrassed to show a file to
your reviewer, the agent should not produce it either.

## 11. One artifact per step

Each workflow step should produce **one** primary artifact (a SQL file, a
TMDL file, a profile report, a review comment list). If a step would create
two unrelated artifacts, it is two steps.

## 12. Validator gates after every artifact

Every artifact is immediately followed by a validator run. If there is no
validator for an artifact, write one before you finish the workflow.
Unvalidated artifacts are untrusted artifacts.

## 13. References are facts; workflows are recipes

A reference never says "do X then Y". It says "X is true because of Y", and
lists anti-patterns. Workflows say "do X then Y" and link to the references
that justify each step. Do not mix the two.

## 14. Naming consistency is a force multiplier

Pick one naming convention per layer (SQL: `snake_case`, DAX/TMDL:
`PascalCase`, templates: `<UPPER_SNAKE>` placeholders) and apply it
everywhere. The agent should never have to guess how a new artifact should
be named.

## 15. Be specific about failure modes

Every workflow lists at least two failure modes, with concrete detection
signals and escalation paths. A workflow that says "hope it works" has not
been designed.

## 16. Small files, many files

Prefer many small, single-purpose files to one large file. If a reference
needs two "see also" links to other references, that's a good sign — it
means the concept boundaries are clean.

## 17. Avoid magic, explain tradeoffs

When there are multiple valid approaches (e.g. SCD types 1, 2, 3, 4), a
reference should enumerate them and state the tradeoffs. It should not
silently pick one without explaining why.

## 18. Links are relative and resolvable

Internal cross-references use relative paths. Broken internal links are
treated as bugs; `validate_project.py` enforces this.

## 19. Severity has meaning

- `ERROR` — almost certainly wrong. Blocks review. The artifact should not
  merge without fixing or explicitly waiving the rule.
- `WARN` — heuristic or tradeoff. Should be reviewed by a human; many
  warnings are a smell. Does not block by default, blocks under `--strict`.
- `INFO` — potentially useful signal. Never blocks anything. Only visible
  with `--verbose`.

## 20. Templates reduce blank-page anxiety, not thinking

A template should provide structure (sections, placeholders, a header that
points to the relevant validator and reference). It should **not** contain
hard-coded logic unless that logic is literally always correct. The agent
still has to think.

## 21. Everything should be reproducible locally

`git clone` → `python scripts/validate_project.py --strict` → exit 0 on a
clean `main`. No remote services, no API keys, no SaaS-only tooling for the
core validators.

## 22. Changelog entries for every user-visible change

Every PR that touches behavior (new workflow, new validator rule, new
reference, new template, bug fix in a validator) updates `CHANGELOG.md`
under the `[Unreleased]` heading. Users of the repository rely on this to
know what changed.

## 23. Backwards compatibility of workflow IDs

Once a workflow ID (`workflows/<id>.md`) is in use, do not rename it. If
the workflow's scope changes significantly, create a new ID and mark the
old one as deprecated with a pointer in its frontmatter.

## 24. Documentation is product, not afterthought

If a feature is not documented in one of the canonical places (`README.md`,
`docs/`, the relevant reference, the script's `--help`), it does not exist
for the purposes of the agent. The agent reads documentation, not pull
request descriptions.

## 25. Trust is earned slowly, lost quickly

Every contribution either builds trust or erodes it. One undetected false
negative in a validator ("this SQL is fine" when it actually contains a
Cartesian product) erodes trust for months. Err on the side of more
warnings, fewer silent passes. State limitations. Write evaluation cases.
Be honest.
