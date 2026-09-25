# Contributing

## Skill package path

All agent runtime content lives under **`skills/analytics-engineering-skills/`** (`SKILL.md`, `workflows/`, `references/`, `templates/`, `scripts/`, `evals/`).

- Edit the skill there — do **not** reintroduce `SKILL.md` at the git repository root.
- Validate with:

```bash
cd skills/analytics-engineering-skills
python scripts/validate_project.py --strict
```

- Human-facing packaging docs (`README.md`, root `docs/`, CI) stay at the monorepo root; keep root `docs/` and the skill’s `docs/` in sync when you change install or architecture guidance.

---

Contributions are welcome — especially new workflows, reference material, evaluation cases, and additional validator rules. See `docs/contribution-guide.md` for the detailed walkthrough.
