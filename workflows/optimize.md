# Workflow: optimize

## Purpose
Improve performance (time, cost, resource usage) of an analytical workload: SQL query, DAX measure, Power BI semantic model, Python transformation, pipeline, or API. Avoid blind "cleanup" that changes nothing measurable or breaks correctness.

## When to use
- User asks to optimize / tune / speed up a specific artifact.
- Slowness confirmed and bottleneck localized (via `diagnose`).
- Cost (credits, memory, storage) is materially above baseline.
- SLA or refresh window is being missed.

Do **NOT** use:
- Because code "looks complex" — complexity alone is never evidence of a bottleneck.
- Before the business logic is correct.
- Before there is a measured baseline.

## Inputs
- The specific artifact to optimize (query, measure, script, pipeline).
- Baseline: current timing, resource usage, dataset size, frequency, environment.
- Success criteria: target duration / cost / memory, validated by user.
- Sizing: row counts, cardinality, data types, partition strategy, refresh mode.
- Correctness reference: known-good output for at least two representative slices.

## Preconditions
- Correctness of current implementation is validated or a correctness oracle exists.
- A reproducible baseline exists (timing, query plan, Server Timings, profile trace).
- Optimization target (latency vs. throughput vs. cost vs. memory) is explicit.

## Procedure
1. **MEASURE baseline.**
   - SQL: run in representative environment, capture actual plan, IO/CPU, duration with warm + cold cache.
   - DAX: DAX Studio Server Timings, xmSQL, cardinality estimates; distinguish Storage Engine vs. Formula Engine.
   - Python: cProfile / line_profiler, memory via tracemalloc, pandas `.memory_usage()`.
   - Pipelines: step-level duration, row counts, bytes read/written, queue wait.
   - Power BI / semantic: Performance Analyzer, refresh traces, Vertipaq Analyzer (column sizes, relationships, dictionary sizes).
2. **IDENTIFY bottleneck.**
   - Attribute 80% of time/cost to the smallest set of operations (Pareto).
   - Name the bottleneck type: scan/join/aggregation/materialization/context-transition/network/refresh/spill-to-disk/remote-source round-trip/cardinality explosion.
3. **FORM HYPOTHESIS.**
   - For each bottleneck, propose exactly one targeted change and predict its effect.
   - Change **one meaningful factor at a time** so results are attributable.
4. **OPTIMIZE (single change).**
   - Apply the change. Keep a side-by-side copy or version of the original for reconciliation.
5. **BENCHMARK.**
   - Same environment, same inputs, same warm/cold state as baseline.
   - Run multiple times; report median and variance.
   - Measure the bottleneck metric again, not just end-to-end.
6. **VALIDATE correctness.**
   - Numerical equivalence against the known-good outputs across representative slices.
   - Edge cases: empty set, min date, max date, key with nulls, single-row group.
   - If numbers differ, root-cause before proceeding — the optimization may be subtly wrong.
7. **DOCUMENT.**
   - Baseline, bottleneck, change, new measurement, correctness confirmation, known trade-off, remaining headroom.
   - If semantic/Power BI: update TMDL descriptions / display folders / annotations accordingly.
8. Repeat 3–7 only while the next bottleneck is **larger** than the remaining cost of stopping. Stop when target is met or next optimization cost exceeds its value.

## Decision points
- If the change trades latency for cost (or memory for CPU, etc.), stop and confirm trade-off with stakeholders before committing.
- If correctness drifts, revert; do not layer a "fix" on top.
- If the bottleneck is in an upstream source (not local code), escalate rather than papering over (and propose a workaround if urgent).
- If change improves a benchmark but has production risks (maintainability, dependency, schema coupling), open a `review`.

## Validation
- Measured improvement against baseline on the bottleneck metric (e.g., query duration p50 reduced ≥ X%).
- No regression on representative slices: numerical equivalence within tolerance.
- No regression on non-target slices or total workload (where measurable).
- Maintainability not degraded without explicit justification and sign-off.

## Expected outputs
- Baseline numbers (duration/cost/memory) and measurement method.
- Identified bottleneck(s) with evidence (plans, traces, profiles).
- Each attempted change: description, expected impact, measured impact, trade-offs.
- Final chosen state and why.
- Correctness reconciliation: sample slices where outputs matched, and any tolerances used.
- Remaining known headroom or hard limits.

## Common failure modes
- Optimizing by style, not measurement. "Rewrote with CTEs" is not an optimization unless measured.
- Benchmarking in dev on tiny data and expecting the same gains in production.
- Changing multiple factors per iteration, making attribution impossible.
- Confusing cold-cache worst case with warm-cache steady state; reporting whichever is more favorable.
- Accepting numeric drift because "it's close enough" without defining tolerance with the business.
- Optimizing an already-dominated path and ignoring the 90% bottleneck.

## References to load
- `references/performance.md` — core methodology + per-technology checklists.
- Technology reference matching the artifact (`sql.md`, `python.md`, `dax.md`, `tmdl.md`, `power-bi.md`, `analytics-engineering.md`).
- `references/testing.md` — numerical equivalence and regression strategy.

## Completion criteria
- Baseline measured and recorded.
- Bottleneck identified with evidence.
- One factor changed per iteration; each iteration benchmarked.
- Final state achieves the agreed target or a clear reason why it cannot is documented with evidence.
- Correctness validated: representative slices match baseline output (or tolerance agreed and recorded).
- Trade-offs and remaining headroom documented.
- Implementation passes `review` where scope/risk/materiality requires it.
