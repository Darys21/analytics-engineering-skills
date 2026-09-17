# Reference: Observability

## When to use
- Any pipeline, semantic model refresh, dashboard, or analytical system that will run more than once and on which decisions depend.
- Before production release. If you can't answer "is it working right now?" you aren't ready.
- When building a pipeline (see `pipeline.md`): observability is part of the spec, not an afterthought.

## When NOT to use
- One-off exploratory scripts that run once and are thrown away. Even then, logs are useful for your future self.

## Why observability
- Dashboards and pipelines fail silently most of the time. Users notice wrong numbers weeks later.
- Alerting on "job failed" catches less than half of real incidents. The silent bad-data incidents are the expensive ones.

## Common mistakes
- "We have logs" (gigabytes of unstructured stdout) but no metrics, no dashboards, and no alerts.
- Alerting on every tiny thing → alert fatigue → critical alerts ignored.
- Alerting only on job failure. Not on: freshness drift, row-count anomalies, semantic model refresh duration regression, data quality failures.
- No run history → impossible to answer "when did this start?"
- Lineage documented once in a Confluence page, never updated.

## Trade-offs
| Level | Cost | Coverage |
|-------|------|----------|
| Logs + manual grep | Low | Incident response only |
| Structured logs + dashboards for key metrics | Medium | Good trend & anomaly detection |
| Logs + metrics + traces + data contracts + SLOs + lineage | High | Mature; catch silent failures fast |

Progress iteratively. Level 2 is far better than level 0.

## What to inspect first
- **Can I tell the current freshness of every table/output in 10 seconds?** If not, add freshness first.
- **Do I know the expected row count / order of magnitude of each step?** Row-count anomaly detection catches more data bugs than schema tests.
- **Who is paged when something fails?** Write it down.

## Good implementation

### 1. The Three Pillars
- **Logs:** structured JSON. Per-run id, per-task id, timestamp, severity, source system, message, any correlation ids.
  - Never log secrets, tokens, PII.
  - In Python, use the standard `logging` module; write JSON in prod.
- **Metrics:** numeric series over time.
  - Per pipeline/task: duration, success/fail count, queue wait.
  - Per data output: rows written, rows read, bytes, nulls (%), duplicates.
  - Per BI: model refresh duration, failure, visual query time (if exported via Power BI REST / Graph / etc.).
  - Per data quality: number and severity of failed DQ checks.
- **Traces** (when system is non-trivially distributed): spans across tasks, services, data stores. OpenTelemetry is the standard target.

### 2. The data-specific signals that actually catch incidents
#### Freshness
- For every table / model users depend on: "When were these data last updated, as reported by the pipeline?"
- SLO for each (e.g., `fact_sales` updated by 07:00 local every day).
- Alert when data older than SLO window.

#### Row counts
- Per run per step: expected range (min/max) or rolling 30-day mean ± σ.
- Alert on 0 rows (source down / filter too aggressive), 10× rows (duplicates / join explosion), missing days.

#### Schema / distribution drift
- Column add/drop/type change.
- Value distribution shifts: a column's mean / cardinality / unique count outside historical band → warning.
- Use a dq-library or compute during pipeline run. Even the simplest version (save 5-number summary per numeric column and compare to last N) catches issues.

#### Data quality checks (see `data-quality.md`)
- Run checks post-materialization per table/model.
- Severity levels: Low (warn), High (block downstream / alert), Critical (page).
- Surface the failing check ID + failing row IDs in the alert.

#### BI-specific
- Power BI / Tableau etc: semantic model refresh success + duration.
- Dashboard load time from a synthetic test user (basic synthetic monitoring).
- RLS role smoke tests daily.

### 3. Lineage and run history
- **Lineage:** an always-up-to-date map of source → bronze → silver → gold → dataset → dashboard. At minimum: a markdown file or wiki page with the current list.
- **Run history:** queryable store of the last N runs with: run id, start/end, duration, status, inputs used (watermarks/params), output counts, errors.
- From an alert, one click to the run history, one click to the relevant logs, one click to the runbook.

### 4. Alerting design
- Fewer, better alerts. Each page must be actionable.
- Alerts routed to the team responsible for that pipeline.
- For every alert:
  - Severity.
  - Runbook link (what to do first).
  - Escalation path after X minutes unacknowledged.
- Typical minimum alerts for a new pipeline:
  1. Pipeline failed.
  2. Pipeline running longer than expected (SLO duration).
  3. Output data stale (freshness SLO violated).
  4. Row count anomaly on any step.
  5. Data quality check severity ≥ High fails.
  6. Semantic model refresh or downstream dashboard build fails.

### 5. SLOs and error budgets
- Name SLOs explicitly: `fact_sales` updated daily by 07:00 with 99% success.
- Measure them.
- If SLOs are repeatedly missed: stop shipping features, fix reliability first.

## How to test observability
- Inject failures in staging:
  - Stop upstream source. Does freshness alert fire?
  - Duplicate a batch. Does row-count anomaly alert fire?
  - Change a column name upstream. Does schema drift alert fire?
  - Make pipeline fail at step X. Does failure alert fire? Can you trace to the right run?
- Walk through a fire-drill: from alert to root cause documented in < 15 min. If not, add the missing link (log lines, run history, dashboards, runbook).

## Performance behavior
- Observability has a cost: extra queries, metric emission, log volume. Budget for it.
- Sampling / aggregation: don't log per-row in 100M row pipelines. Log per-chunk summary.
- Distributed tracing is expensive; enable selectively, not by default on every column of every table.

## Pitfalls
- **Dashboard on dashboards:** 20 observability dashboards nobody looks at. Focus on alerts + a single "health home" page.
- **Alerts without runbooks.** On-call at 03:00 without a runbook = guessing.
- **Alerts without owners.** Everyone's job = nobody's job.
- **No severity.** Every alert fires same paging = low value.

---
*See also:* `workflows/pipeline.md`, `references/data-quality.md`, `references/ci-cd.md`, `references/security.md`, `workflows/delivery.md`.
