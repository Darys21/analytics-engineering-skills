# Analytics Engineer Agent Skills

Composable, opinionated building blocks for an **Analytics Engineering agent** that
operates on data warehouses, semantic models, and BI artifacts.

## Install

### One command (recommended)

```bash
npx skills add Darys21/analytics-engineering-skills
```

Works with GitHub Copilot (VS Code Agent mode), Claude Code, Cursor, Codex, and other Agent Skills hosts. The CLI copies the skill into the correct folder for your agent (e.g. `.github/skills/` for Copilot).

### GitHub CLI

```bash
gh skill install Darys21/analytics-engineering-skills
```

Requires [GitHub CLI](https://cli.github.com/) v2.90+.

### Manual (Copilot project skill)

```bash
git clone https://github.com/Darys21/analytics-engineering-skills.git /tmp/aes
mkdir -p .github/skills
cp -R /tmp/aes/skills/analytics-engineering-skills .github/skills/
```

Then open Copilot Chat → **Agent** mode → `/skills` and confirm `analytics-engineering-skills` is listed. Enable **Use Agent Skills** in VS Code settings if needed (`chat.useAgentSkills`).

### Verify the package

```bash
cd skills/analytics-engineering-skills   # from a full clone of this repo
python scripts/validate_project.py --strict
```

Full guide: [docs/how-to-use.md](docs/how-to-use.md)

---

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
analytics-engineering-skills/          ← git repo root
├── README.md, LICENSE, CHANGELOG…
├── docs/                             ← human docs
├── .github/workflows/
└── skills/
    └── analytics-engineering-skills/ ← installable skill package
        ├── SKILL.md
        ├── workflows/
        ├── references/
        ├── templates/
        ├── scripts/
        ├── evals/
        └── docs/
```

## License

Apache License 2.0. See the `LICENSE` file.

Official repository: <https://github.com/Darys21/analytics-engineering-skills.git>
