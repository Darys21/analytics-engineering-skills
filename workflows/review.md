# Workflow: review

## Purpose
Audit an analytical deliverable (project, dashboard, pipeline, model, query set, or report) across business, data, logic, engineering, performance, security, UX, and operations dimensions. Provide a structured, actionable list of findings with severity.

## When to use
- Before or after delivery of a non-trivial analytical project.
- User explicitly asks to review / audit / quality-check something.
- Before a significant refactor or handoff.
- When inheriting an existing project with unknown quality.
- After implementation of high-risk or high-scope work.

## Inputs
- Artifact(s) under review: code, queries, DAX, semantic model (TMDL/PBIP), dashboards, notebooks, pipeline definitions, data samples, documentation.
- Business intent: original request, decision the output supports, KPIs, target audience.
- Any prior context: CONTEXT.md, ADRs, prior reviews, known issues.
- Test or validation results already produced.

## Preconditions
- At minimum the core artifacts must be inspectable. If key artifacts are unavailable, scope the review to the accessible subset and state the blind spots explicitly.

## Procedure
1. Confirm scope: what is in review, what is out, success criteria for the review itself (e.g., blocking vs. advisory only).
2. **Business review.**
   - Is the actual business problem solved? (Not just the literal request.)
   - Are KPIs, metric definitions, and grain explicit and correct?
   - Is the result actionable? Can the intended user make the intended decision with this output?
   - Are assumptions, limitations, and "known unknowns" surfaced to the user?
3. **Data review.**
   - Grain correct in every fact / aggregation / output?
   - Relationships valid (cardinality, filter direction, referential integrity, no ambiguous paths)?
   - Duplicates, nulls, missing periods, outliers handled or explicitly flagged?
   - Freshness understood and communicated (source vs. user-visible)?
   - Data lineage traceable from output to source at the grain of the metric?
4. **Logic review.**
   - Transformations correct end-to-end? (Spot-check from source to output across at least three slices: typical, edge, empty.)
   - Assumptions explicit? Are they defensible?
   - Time logic correct (cutoffs, fiscal calendars, DST, timezone handling, partial periods)?
   - Semi-additive and non-additive measures handled correctly per grain?
5. **Engineering review.**
   - Maintainable: naming, modularity, comments only where intent is non-obvious, dead code absent.
   - Reproducible: versions, envs, seeds, deterministic seeds for any randomness, idempotent pipelines.
   - Testable: validation/assertions exist for the high-risk logic.
   - No secrets, credentials, or PII in code, examples, or logs.
6. **Performance review.**
   - Bottlenecks evidenced (not guessed). Do baselines exist?
   - Are optimizations justified and measured? (Reject "looks slow" — require measurement.)
   - Refresh / query SLOs and headroom clear.
7. **Security review.**
   - Secrets handling (env vars / secret store; never hardcoded).
   - Least-privilege access; no broad READ on entire warehouse unless justified.
   - Sensitive data / PII: masked or excluded from outputs and examples. Logs scrubbed.
   - Dependency hygiene: pinned versions, no known vulnerabilities where trivially checkable.
8. **UX review (dashboards, reports, notebooks).**
   - Intended user persona explicit.
   - Can user understand output in < 60 seconds and act?
   - Hierarchy: Context → KPI → Diagnosis → Detail → Action respected.
   - Filters, tooltips, drill-downs, progressive disclosure correct.
   - Accessibility (color, contrast, alt text/descriptions) not ignored.
9. **Operations review (pipelines / production systems).**
   - What happens on partial failure? Recovery? Retry? Backfill?
   - Late-arriving data, schema drift, duplicated batches handled?
   - Observability: logs, metrics, run history, lineage, freshness SLO present?
   - Alerting: on the right signal (failure is obvious; silent wrong data is the real risk).
10. Triage findings by severity (Blocking / High / Medium / Low / Advisory) and group by dimension.
11. For each finding: concrete reproduction + recommended fix (or explicit "no fix required, rationale") and estimated effort/impact.
12. Deliver the review artifact; optionally route to `diagnose` or `optimize` for any actionable finding not yet resolved.

## Decision points
- If Blocking findings exist, do **not** recommend delivery until resolved.
- If High findings exist with no remediation plan, escalate rather than approve.
- If the review reveals the wrong problem is being solved, escalate to `business-analysis` and `grill` before continuing engineering work.

## Validation
- Every finding has a severity, a reproduction, and a proposed next step.
- Blind spots (artifacts unavailable, not inspectable) are explicitly listed.
- No claims of verification for anything not actually inspected.

## Expected outputs
- Executive summary: overall posture (pass / pass with conditions / hold), count of findings by severity.
- Findings list per dimension with severity, evidence (links, code refs, slices), and recommendation.
- Suggested next actions: route to `diagnose`, `optimize`, `data-quality`, or other workflows as needed.
- Definition of "ready to deliver" for this specific review.

## Common failure modes
- Shallow review: "looks good" without spot-checks.
- Style-only review: focuses on formatting while missing logical correctness.
- No severity triage: every finding equally weighted, making the review useless.
- No evidence: claims of "wrong numbers" without a reproducible slice and source-of-truth comparison.
- Scope creep: reviewing items explicitly declared out of scope.
- False confidence: declaring things correct that were not actually inspectable.

## References to load
- `references/testing.md`
- `references/performance.md`
- `references/security.md`
- `references/observability.md`
- Technology references matching artifacts (`sql.md`, `python.md`, `dax.md`, `tmdl.md`, `power-bi.md`, `analytics-engineering.md`, `data-modeling.md`).

## Completion criteria
- All eight dimensions covered at the level permitted by available artifacts.
- Each finding has severity, evidence, recommendation.
- Executive posture is stated.
- Blind spots and uninspectable areas are explicitly listed.
- Recommended next workflows/actions are assigned.
- If Blocking/High findings exist, they are explicitly escalated rather than buried.
