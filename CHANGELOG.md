# Changelog

## [Unreleased]

### Changed

- **BREAKING (layout):** Installable skill moved to `skills/analytics-engineering-skills/` so standard installers work:
  - `npx skills add Darys21/analytics-engineering-skills`
  - `gh skill install Darys21/analytics-engineering-skills`
- CI and `validate_project.py` now target the skill package path (monorepo root still supported via auto-detect).
- Docs updated: README Install section, `docs/how-to-use.md`, `docs/architecture.md`, `CONTRIBUTING.md`.

### Migration

If you previously pointed an agent at the **repository root**, point it at the skill package instead, or reinstall with the commands above. Manual Copilot path: `.github/skills/analytics-engineering-skills/`.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
starting from `v1.0.0`. Pre-`1.0.0` releases use the convention
`MINOR` for feature additions and `PATCH` for fixes.

## [Unreleased]

### Changed

- Removed remaining company-specific name references from README, CONTRIBUTING
  and historical notes so the skill is fully general-purpose.

---

## [v0.2.0] — 2026-09-18

Consolidation and hardening release. See repository history for full notes.
