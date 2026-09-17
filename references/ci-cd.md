# Reference: CI/CD and Delivery

## When to use
- Any analytics project with multiple developers, repeated releases, or production reliability expectations.
- Mandatory before a pipeline or semantic model supports business-critical decisions.

## When NOT to use
- Single-person throwaway notebook. Even then, git is cheap.

## Common mistakes
- No version control. "The server's version is the truth."
- Directly editing production via UI clicks. Undocumented, unrepeatable, dangerous.
- CI runs nothing: it's green because no tests or lint run.
- Deploy step runs `dbt run --full-refresh` without rollback plan.
- No changelog / release notes. Nobody knows what changed.
- Deploy on Friday afternoon. Don't.

## What to inspect first
1. **Source of truth.** Is code + semantic in git? If not, start there.
2. **Is there CI? What does it actually check?**
3. **Is deployment automated? Who can deploy? What is rollback?**
4. **Environments.** Dev / Test / Prod or equivalent?

## Good implementation

### 1. Version control and branching
- Git or equivalent. All code in: SQL, DAX (via TMDL/PBIP), Python, dbt project, pipeline definitions, semantic model TMDL.
- No binary `.pbix` as canonical source. Use PBIP + TMDL files.
- Branch strategy (choose per-team and enforce):
  - **GitHub flow:** short-lived feature branches off `main`, squash-merge after PR.
  - **GitLab flow / release branches** if scheduled release trains.
- Commit style: Conventional Commits recommended (`feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`) → changelogs and versioning automatable.
- Protect `main`: require PR + review + CI green before merge.

### 2. Pull requests and code review
- PR template prompts:
  - What / Why.
  - How validated (local runs, tests, screenshots, reconciliation).
  - Risk & rollback.
  - Related ADRs / tickets.
- Review for: correctness, data grain, edge cases, performance, maintainability, security, tests.
- At least 1 human review for risky changes. Self-review checklist for teams of 1.

### 3. Continuous Integration (CI)
Every PR and every merge to `main` runs, in order of fast-to-slow:
1. **Static checks** (fast): lint, format, import sort, security scan (secrets + dep scan), YAML schema lint.
2. **Unit tests** (fast): pure functions, DAX baseline assertions if framework exists, small sample data tests.
3. **Schema + data tests** (medium): against a sample database or dbt seed: `dbt test` or equivalent.
4. **Build + integration** (medium): `dbt build`, TMDL model compile/publish to a test workspace, pipeline dry-run.
5. **Reconciliation / regression tests** (slow, on main or scheduled): known-period tie-out of new pipeline vs. prior-known-good output.
6. **Performance smoke tests** (optional, scheduled): compare key query durations to baseline; alert on regressions.

If a step fails, block merge (or block deploy, for slower optional steps).

### 4. Environments and secrets
- Dev / Test / Prod or similar separation.
- Each environment has its own connections, workspaces, databases, secrets.
- Secrets: never in git. Repo secrets in CI; runtime secrets from a secret store in production.
- Config by environment (`.env.dev`, `.env.test`, `.env.prod` or config file loader) — never `if os.environ.get('ENV') == 'prod':` scattered across code.

### 5. Continuous Deployment / Release
Automate deployment after CI passes on `main`, with human gates for critical production changes.

Typical pipeline:
```
Commit → CI (lint/test/build) → Deploy Test → (optional) manual approval → Deploy Prod → Post-deploy health checks → Notify
```

**Deployment patterns (pick per risk):**
- **Simple replace:** deploy new version, tear down old. Fast. Suitable for batch pipelines with idempotent backfill.
- **Blue / green (or A/B):** two identical environments. Shift traffic only after green health checks. Best for dashboards / semantic models / critical APIs.
- **Canary:** deploy to 1% of users or one workspace first. Rollback easy. Best for high-risk UI changes.

### 6. Rollback
Test rollback. Don't just have a "we can rollback" bullet.
- Code-level: `git revert`, then redeploy.
- Data-level: snapshots of output tables / semantic model versions, or atomic swap to prior version. Never rely on restoring a full backup in a hurry; keep a versioned recent output copy.
- Dashboard/app-level: Power BI deployment pipelines can promote to prior stage; or deploy a prior commit to Test and roll-forward the fixed version to Prod.

### 7. Changelog and release notes
- `CHANGELOG.md` (Keep a Changelog format: Added / Changed / Deprecated / Removed / Fixed / Security).
- Automated from Conventional Commits if possible.
- Release notes to stakeholders: 5 bullet points max; focus on user impact and action required.

### 8. dbt-specific patterns
- `dbt build` over separate `run + test`.
- Slim CI on PRs: `dbt build --select state:modified+ --defer --state ...` → test only what changed.
- In production: separate `run` vs. `test` if failing tests should not fail entire run; but always run tests after and alert on failures.
- Docs: generate + publish `dbt docs` as part of release.

### 9. Power BI / semantic model patterns
- Canonical source: PBIP + TMDL in git.
- CI: `pbi-tools` / Tabular Editor CLI / XMLA scripts to validate TMDL and deploy to a test workspace.
- Deploy via deployment pipelines (Dev → Test → Prod) with rules, or via XMLA endpoint automation.
- After deploy: scheduled refresh + smoke tests (a simple EVALUATE on the dataset that asserts a known number).

## How to test CI/CD
- Break a test locally, push to a branch. Does CI fail? (Required: yes, before any merge.)
- Introduce a secret into a PR via a test branch. Does secrets scan fail the PR?
- Perform a test deployment. Then perform a rollback. Both paths work end-to-end.
- Post-deploy health check: kill the DB connection. Does the post-deploy step fail the deployment?

## Performance behavior
- CI is part of the engineering loop. Keep the PR pipeline < 10 min if possible. > 30 min → engineers start working around CI.
- Move slow tests (reconciliation, performance) to nightly / weekly, not per PR. Keep per-PR fast + useful.

## Pitfalls
- "We have CI" → it runs `echo "CI OK"` → zero value.
- "We deploy only via UI clicks because the automation is broken" → fix the automation. Every UI click is a future outage.
- "Rollback = restore from backup" → slow and risky; rollback to last-known-good release artifact instead.
- One giant monorepo pipeline: every change runs 45 min of unrelated tests → teams split off into shadow processes.

---
*See also:* `workflows/delivery.md`, `references/security.md`, `references/observability.md`, `references/testing.md`, `references/power-bi.md` (PBIP/TMDL/deployment pipelines).
