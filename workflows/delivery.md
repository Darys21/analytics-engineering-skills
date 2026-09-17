# Workflow: delivery

## Purpose
Deliver analytical work into the hands of users in a controlled, reproducible, observable way. Covers version control, validation gates, deployment, rollback, documentation, stakeholder communication, and the handover of operational responsibility.

## When to use
- Any analytical work is moving from development → staging → production / user-visible state.
- Dashboard, semantic model, pipeline, dbt/SQL build, notebook app, or report is being released.
- A bugfix or hotfix is being shipped.

## Inputs
- Deliverable inventory: exact artifacts (files, dashboards, pipelines, tables, models).
- Target environment(s) and access.
- Change description (linked to request/ticket/ADR if any).
- Validation evidence (test runs, reconciliations, quality results, performance benchmarks).
- Rollback plan and deployment owner.
- Stakeholders to notify and message.

## Preconditions
- Definition of Done (`templates/definition-of-done.md`) items applicable to this change are signed off.
- At least one blocking/high finding from `review` unresolved → go back and resolve before delivery.
- Deployment target, credentials, and permissions are known and least-privilege.
- For hotfix: both the fix AND a rollback to previous known-good are tested in a staging-like environment (or the closest available).

## Procedure
1. **Version control.**
   - Changes on a branch; conventional commits or consistent commit style.
   - PR / MR description links to issue, includes: what, why, how validated, screenshots for visual changes, risk & rollback.
   - Peer code review when the team has reviewers. Self-review checklist if no reviewer.
2. **Validation gates (pre-merge or pre-deploy).**
   - CI runs: lint, unit tests, data tests, schema tests, reconciliation, build (dbt build, etc.), dependency check.
   - Manual validation checklist where automated is impossible: visual smoke tests, stakeholder sign-off for UX, statistical sample for data migrations.
3. **Deployment.**
   - Prefer progressive rollout: dev → staging → canary subset of users → full.
   - Deployment is scripted / pipeline-driven, never "click in UI and hope."
   - Record deployed version (commit SHA, semantic version, pipeline run id, timestamp, who deployed).
   - Confirm post-deploy health: refresh succeeded, key queries/measures return values, row counts in acceptable range, dashboards load.
4. **Rollback readiness.**
   - Test rollback command/process in staging at least once for major releases.
   - Keep rollback steps short and documented. For data changes: backup + restore path, or idempotent down-migration, or revert+redeploy path.
5. **Observability and alerting.**
   - Confirm freshness, duration, failure, and row-count monitors see the new deployment.
   - Turn on / update alerts for new pipelines, tables, dashboards, or refresh schedules.
   - In first 24–72h after a major change: extra watch (war-room / on-call aware if applicable).
6. **Documentation updates.**
   - Update user-facing docs (README, runbooks, dashboard docs, metric dictionary) if changed.
   - Update project `CONTEXT.md` if business/operational context has changed.
   - Record important architectural or business-interpretation changes as ADRs (`templates/ADR.md`).
   - Update CHANGELOG.md; tag a semantic version when appropriate.
7. **Stakeholder communication.**
   - Release note: what changed, why, how to use, what's different for users, known limitations or follow-up.
   - Who to contact for issues and during what hours.
   - Confirm owners and operational handoff (who runs day-to-day, who responds to incidents).
8. **Post-delivery follow-up.**
   - Check key business and system metrics post-release against pre-release baseline in the first N days (define N explicitly).
   - Capture user feedback, prioritize follow-up items in a backlog, close the loop with requesters.
   - Retire or deprecate old artifacts with an explicit sunset date if the release supersedes them.

## Decision points
- If any pre-deploy gate fails, stop. Do not push "just this once." Escalate with reasons.
- If rollout exposes Blocking/High issues mid-flight, roll back before root-causing. Root cause after safety.
- If scope grew during implementation, re-validate vs. DoD rather than shipping an unchecked surface area.
- If deployment requires elevated credentials the agent does not have, hand instructions to the deployer with explicit validation list.

## Validation
- Deployed artifacts match expected versions (SHA, version tag).
- Post-deploy health checks pass (document which checks were run).
- User-visible smoke test pass for the personas affected.
- Rollback was either executed successfully in a non-prod environment or is trivially reversible (and that fact is evidenced).
- Monitors fire on synthetic failures if possible; otherwise their presence and configuration is confirmed.

## Expected outputs
- Merge commit / deployed SHA and deployment log (or links thereto).
- Release notes / changelog entry.
- Post-deploy health report.
- Rollback plan: trigger conditions + steps + who can execute.
- Stakeholder communication sent.
- Updated CONTEXT.md / ADRs / runbooks as appropriate.
- Follow-up items backlog (for the post-release observation window).

## Common failure modes
- Deploying directly from local without CI / version control.
- No rollback plan; "we'll fix forward" combined with a major user-facing incident.
- Post-deploy validation is forgotten; issue discovered by users first.
- Alerting not updated for new pipelines; silent failures happen for weeks.
- Docs not updated; users use the old behavior and support teams can't help.
- Deployment is "done" when it's shipped; no post-release metric check.

## References to load
- `references/ci-cd.md` — version control, PRs, CI design, rollback.
- `references/observability.md` — monitors, run history, alerting.
- `references/security.md` — deployment credentials, least privilege.
- `templates/definition-of-done.md` — the sign-off checklist.
- `templates/ADR.md` — for important decisions made during the release.

## Completion criteria
- Artifacts deployed to the target environment(s) and health-verified.
- Version recorded; rollback plan documented and (where feasible) tested.
- CI validation gates passed; evidence recorded.
- Observability in place (monitors, alerts, run history, lineage for new entities).
- Docs, ADRs, CONTEXT, CHANGELOG updated for the change.
- Stakeholders notified and owners handed off.
- Post-release follow-up plan in place.
