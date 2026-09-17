# Workflow: diagnose

## Purpose
Systematically find and separate symptoms from root causes in analytical, pipeline, query, measure, or dashboard problems. Avoid jumping to random fixes.

## When to use
- User reports an error, wrong numbers, slow performance, missing data, or unexpected behavior.
- Analytical output contradicts expectations or another source.
- Something "used to work" and now does not.
- Before `optimize` (first confirm where the bottleneck is).
- Before writing a fix when the cause is uncertain.

## Inputs
- Observed behavior (messages, numbers, timings, screenshots, stack trace / query plan / DAX Studio output if available).
- Expected behavior and the basis for it (definition, baseline, prior run, another source).
- Scope: where and when it happens, reproducibility.
- Access to relevant code, SQL, DAX, pipeline definitions, data samples.
- Any recent changes (deploys, schema changes, upstream data changes, config changes).

## Preconditions
- At minimum a clear observed symptom and an expected result.
- Do not guess. If reproduction is impossible, state the limitation and propose experiments.

## Procedure
1. **OBSERVE.** Capture the exact symptom: error message verbatim, numbers with grain and filters, timing with environment, reproducibility steps. Confirm versions, refresh dates, user/tenant scope.
2. **REPRODUCE.** Reproduce the issue in the same environment and at the same grain. If not reproducible, document conditions under which it occurs vs. does not; isolate state.
3. **ISOLATE.** Bisect the system. Move the boundary between working and failing.
   - For wrong numbers: compare source vs. staging vs. mart vs. BI layer. Find the first layer producing the wrong result.
   - For SQL: progressively simplify joins, filters, CTEs until the anomaly disappears or a minimal repro is found.
   - For DAX: remove filters, remove iterators, split variables, compare DAX Studio Server Timings / xmSQL.
   - For pipelines: compare run metadata (row counts, duration) between good and bad runs.
4. **HYPOTHESIZE.** Write at least two hypotheses. For each, list a test that would disprove it. Prefer deterministic hypotheses ("grain mismatch between join keys") over speculative ones ("data corrupted").
5. **TEST.** Execute tests against each hypothesis. Measure or log precisely; do not infer from partial evidence.
6. **FIX (only after a hypothesis is confirmed).** Apply minimal targeted change. Distinguish:
   - Symptom vs. root cause
   - Contributing factor vs. root cause
   - Workaround (temporary, prevents user pain) vs. permanent fix (addresses root cause).
7. **REGRESSION TEST.** Re-run the repro from Step 2. Confirm the symptom is gone *and* previously working behavior is unchanged. Run adjacent test cases: edge dates, boundary values, empty inputs, different filters, different users.
8. **DOCUMENT.** Record: symptom, environment, root cause, fix category (workaround vs. permanent), evidence, regression scope, remaining risk. If project has ADRs/CONTEXT.md, update when systemic.

## Decision points
- If isolation cannot identify a single layer, escalate to source comparison in `data-quality` (reconciliation).
- If fix has performance or risk trade-offs, open a `review` before implementation.
- If issue is an upstream data defect (source system), do not "fix" downstream silently; escalate and apply a documented workaround with deprecation date.
- If performance is the symptom, route into `optimize` with the bottleneck now identified.

## Validation
- Reproduction steps produce correct output after fix.
- At least one adjacent case (different period, different segment, different filter) still correct.
- Root cause, not only symptom, addressed; or if workaround only, limitation and follow-up explicit.

## Expected outputs
- Diagnosis summary: symptom → root cause → contributing factors.
- Evidence (queries, logs, metrics) that supports the root cause.
- Fix proposed with category (workaround / permanent) and trade-offs.
- Regression test plan.
- If no root cause found: hypotheses ruled out, remaining unknowns, recommended next experiments.

## Common failure modes
- Jumping from observation to fix without isolation. Never "try changing X" first.
- Confusing symptom with cause (e.g., "measure returns BLANK" is not a cause; the cause is e.g. missing relationship + filter context direction).
- Testing only the failing case and not adjacent cases; fix introduces regressions.
- Ignoring recent changes; environment not pinned during reproduction.
- Silently patching downstream data quality instead of escalating the source.

## References to load
- `references/testing.md` — for regression strategy and numerical equivalence.
- `references/performance.md` — if the diagnosis is performance-related.
- `references/data-modeling.md` — if grain/relationship/cardinality is a candidate cause.
- The technology-specific reference matching the failing component (`sql.md`, `python.md`, `dax.md`, `tmdl.md`, `analytics-engineering.md`, `observability.md`).

## Completion criteria
- Symptom captured exactly.
- Reproduction available or inability to reproduce documented with reasons.
- At least two hypotheses enumerated and tested; evidence for/against recorded.
- Root cause identified (or all hypotheses eliminated with explicit unknowns).
- Fix proposed with: workaround vs. permanent label, scope, risks.
- Regression tests defined and executed where feasible.
- Fix, if applied, validated against baseline, and regression runs pass.
- Result documented so a future reader can understand why the change was made.
