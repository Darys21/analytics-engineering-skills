# Workflow: pipeline

## Purpose
Design, implement, and operate analytical data pipelines (ingestion → transformation → output) so they are predictable, reliable, observable, and recoverable. Handles operational edge cases explicitly.

## When to use
- User asks for a scheduled ETL/ELT, daily job, incremental build, streaming pipeline, or orchestrated workflow.
- A one-off transformation needs to be automated and run repeatedly.
- A pipeline exists but is failing or not observable.

## Inputs
- Data sources: type, owner, freshness SLA, access pattern, API/SFTP/DB/files, rate limits, schema change cadence.
- Targets: warehouse / lake / mart / BI semantic layer; output consumers and their SLA.
- Required transformations (from `analytics-engineering`) and output grain.
- Schedule: frequency, expected data arrival times, SLA for end-to-end.
- Environment: orchestrator (if any: Airflow, Dagster, Prefect, dbt Cloud, ADF, Synapse pipelines, GitHub Actions, etc.), compute, permissions.
- Failure owners (on-call, team contacts).

## Preconditions
- Sources are reachable and schema is documented (or discovered via `data-discovery`).
- At least bronze → silver → gold output design exists from `analytics-engineering`.
- Data quality expectations are defined (`data-quality`).

## Procedure
1. **Define the contract.**
   - Sources: name, owner, expected arrival time, file/schema pattern, freshness SLO.
   - Outputs: datasets/tables/models, grain, expected row count range, target latency.
   - SLOs: success rate, maximum end-to-end duration, maximum allowed staleness.
2. **Orchestration graph (DAG) design.**
   - Tasks grouped by: ingest → stage / bronze → silver / clean → gold / marts → semantic refresh → notification.
   - Explicit dependencies. No implicit ordering by "we schedule them in order."
   - Critical path identified; long poles understood.
3. **Idempotency and determinism.**
   - Every task, run twice with same inputs, produces the same output state.
   - Pattern examples: merge-based or replace-partition (not append-and-forget); run-id / watermark column; delete+re-insert for the window being reprocessed.
   - Deterministic seeds for any randomness; timestamp for "now" provided by orchestrator not the task.
4. **Scheduling, windows, and incremental logic.**
   - Event-driven vs. schedule-driven; choose explicitly.
   - Watermark / high-watermark tracking per source.
   - Late-arriving data: define allowed lateness window and a separate backfill path for records outside it.
   - Partial periods: close-window rules (e.g., finalize a day only after 6h buffer).
5. **Retries, backfills, and recovery.**
   - Per-task retry policy: count, backoff, retryable vs. non-retryable errors (e.g., 5xx vs. 4xx on API).
   - Backfill: tested path for re-running N past periods without reprocessing unrelated data.
   - Checkpointing: progress persisted so restart after crash resumes from the last completed step.
   - Atomic publishes: outputs are only visible downstream when a task fully succeeds (staging table swap, temp file rename, transaction commit).
6. **Operational scenario design. For each, write what happens:**
   - "Pipeline fails at 06:17 in step X": which tasks run/rollback, who is alerted, expected recovery steps.
   - "Yesterday's data arrives 3h late": does the scheduler re-trigger? How is the partial window handled?
   - "A source duplicates 10,000 rows": does dedupe in bronze catch it? Where is the reconciliation alert?
   - "A source schema changes (column added/renamed/dropped)": does the pipeline fail fast? Is there on-call guidance?
   - "An entire run succeeds but the numbers are silently wrong": which data-quality / reconciliation check catches it, when, and with what severity?
7. **Partial failure handling.**
   - One tenant/source/region fails mid-run: remaining continue? Or fail fast? Decide per consumer criticality.
   - Idempotent, task-level state so rerun does not double-count successful tasks.
8. **Monitoring, alerting, lineage, run history.**
   - Logs: structured, per-run + per-task ids, correlation across jobs.
   - Metrics: per-task duration, success/failure rate, rows read/written, bytes, queue wait.
   - Alerts: on (1) pipeline failure, (2) pipeline running too long, (3) source delay, (4) freshness SLO violation, (5) row count anomaly, (6) data quality failure (severity ≥ high), (7) semantic model refresh failure.
   - Lineage: trace per output table/model from source → intermediate → target (manual list is minimum; use the tool's native lineage if available).
   - Run history: queryable store for last N runs, parameters used, status, durations, errors.
9. **Deployment and CI for pipelines.**
   - Pipeline code in version control, CI runs tests + dry-run against staging.
   - Deploy with config per environment (dev/stage/prod) and no hardcoded secrets.
   - Blue/green or rollback strategy for pipeline code and for data outputs (e.g., versioned snapshots of gold tables).
10. **Operational handoff.**
    - Runbook with common failures, their likely causes, and step-by-step recovery.
    - On-call owner and escalation chain.
    - Scheduled pipeline review (quarterly): remove dead tasks, refresh SLOs, verify SLOs are met.

## Decision points
- Full refresh vs. incremental: only incremental when row volume justifies cost and complexity. Start with simple full refresh; graduate to incremental only when measured.
- Batch vs. streaming: latency requirement > batch cadence → streaming; otherwise batch. Keep it simple.
- Fail-fast vs. best-effort: if downstream is a critical compliance report → fail-fast. If internal monitoring dash → best-effort + alert. Decide explicitly.
- If SLO conflicts with cost: renegotiate SLO or add budget. Don't silently pick one.

## Validation
- Dry-run or test run with synthetically injected failures: source down, duplicates, late data, schema change, mid-run crash. Each path behaves as designed.
- Idempotency test: run the same window twice; row counts and values identical.
- Backfill test: re-run last 7 days; output values match known-good baseline.
- Freshness SLO met over N runs (or simulated N runs).
- Alerts fire for synthetic failures in staging (proof of alert coverage).

## Expected outputs
- Pipeline / DAG diagram + task inventory with dependencies.
- Contract: sources, outputs, SLOs, freshness, owners.
- Idempotency, incremental, and checkpointing design.
- Failure playbook for common scenarios.
- Monitoring/alerting configuration (or plan).
- Run history location + lineage table.
- CI/deploy process + per-environment config.
- Runbook + on-call owner.

## Common failure modes
- Append-only pipelines: re-run duplicates data, wrong totals for months.
- No atomic publishes: consumers see partial data.
- "It always succeeded before" — no retries, no SLOs, no playbook → outage when it finally fails.
- Over-engineered incremental on tiny data; complexity costs more than compute.
- Alert-only-on-failure: silent wrong data lives for weeks because no row-count / reconciliation check.
- Hardcoded parameters per run; every rerun needs manual edits, every manual edit produces defects.

## References to load
- `references/analytics-engineering.md` — medallion layers, modular transforms, data contracts.
- `references/observability.md` — logs, metrics, alerts, lineage.
- `references/data-quality.md` — reconciliation and DQ checks as gates.
- `references/ci-cd.md` — deployment, rollback.
- Technology references matching your stack (`sql.md`, `python.md`, `power-bi.md`, etc.).

## Completion criteria
- DAG with explicit dependencies built or defined.
- Idempotent and deterministic (proven via double-run).
- Scheduling, incremental logic, and late-data handling defined and tested.
- Operational scenarios documented and injected-failure tests run.
- Monitoring, alerts, lineage, and run history present.
- Deployment and rollback automated.
- Runbook + owner + escalation chain in place.
