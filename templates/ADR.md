# ADR-NNN: [Short, Present-Tense Title Describing the Decision]

> **Template Usage**: Copy this file to `docs/adrs/ADR-NNN-meaningful-slug.md` before editing. Replace `NNN` with the next sequential integer (zero-padded to 3 digits). Do not re-number existing ADRs.
>
> **Format**: This template follows the classic Michael Nygard / Joel Parker Henderson ADR structure. Each ADR is a single, immutable document; once status moves to *Accepted* or *Superseded*, only the Status field and the Superseding-ADR cross-reference may change.

---

## 1. Title

**ADR Number:** `NNN`
**Title:** [e.g., "Use Delta Lake as the Open Table Format for the Silver and Gold Zones"]

---

## 2. Status

**Status:** `Proposed` | `Accepted` | `Rejected` | `Deprecated` | `Superseded`

- **Proposed:** ADR written and under active discussion. Not yet acted on.
- **Accepted:** Decision ratified by stakeholders. Implementation may proceed.
- **Rejected:** Decision considered and explicitly not adopted. Documented for history.
- **Deprecated:** Decision was Accepted but is no longer enforced (no replacement yet).
- **Superseded:** Decision was Accepted but has been *replaced* by a newer ADR. Link:
  > **Superseded by:** ADR-NNN — Title of newer ADR (fill filename `./ADR-NNN-slug.md` when available)

**Proposed by:** [Name(s) / Role(s)]
**Date Proposed:** [YYYY-MM-DD]
**Date Accepted / Rejected:** [YYYY-MM-DD]
**Deciders:** [Names / Roles of the people who approved / rejected this ADR]

---

## 3. Context

> Describe **the situation** that forces a decision, including:
> - The problem or opportunity that motivates the change.
> - Technical, business, or regulatory constraints that narrow the solution space.
> - Any prior decisions or existing system state that the new decision must respect.
> - Forces at play (performance, cost, security, maintainability, team skill, schedule, risk).
>
> Be **factual and neutral.** Do not argue for a solution here — save that for Decision / Alternatives.

### 3.1 Situation
[2–5 paragraphs. Example:
The analytics platform currently stores Silver-zone tables as unpartitioned Parquet files on ADLS Gen2. As of June 2025, the Silver `mvt_wagon` table has grown to ~1.8B rows, with ~2M new rows ingested daily.

Three pain points are now blocking delivery of the Wagon Turnaround KPI dashboard (Project SETRAG-LGS-003):
1. **Schema evolution without rewrite**: The TMS team added a new `consist_sequence` field in v3.2 of their event schema. Adding a column required rewriting all historical Parquet files — a 36-hour job.
2. **Time-travel / rollback**: A bad backfill on 2025-06-14 corrupted 3 days of Silver data. Recovery required re-running 17 ADF pipelines from Bronze, taking 11 hours.
3. **ACID-compliant upserts**: The requirement to reconcile TMS late-arriving events (up to T+7 days) with IoT gate reads needs merge-on-read semantics; current append-only Parquet leads to ~0.3% duplicate rows that the BI team must deduplicate on every dashboard refresh.]

### 3.2 Constraints (Non-Negotiables)
- **REGION**: All files remain in Azure West Europe (Amsterdam) — no cross-region egress.
- **COST**: Budget for this architectural change is ≤ €4,000 one-time migration effort + ≤ €500/month recurring incremental cost.
- **COMPATIBILITY**: Existing Power BI DirectQuery datasets over Serverless SQL must continue working during and after migration (no downtime for business users).
- **TEAM SKILLS**: The analytics engineering team of 4 FTEs has PySpark + Parquet experience; no one has prior hands-on experience with Iceberg or Hudi.
- **SCHEDULE**: Migration must complete before KPI dashboard UAT start on 2025-09-01 (~10 weeks of runway).

### 3.3 Related Decisions & Dependencies
| Related ADR | Relationship | Notes |
|---|---|---|
| ADR-003 (ADLS Three-Zone Topology) | **Depends on** | This ADR is a change *within* the Bronze/Silver/Gold zones; zone topology itself is not in scope. |
| ADR-005 (Power BI Semantic Layer over Serverless SQL) | **Must not break** | Power BI connectivity via T-SQL OPENROWSET over the storage account must remain functional. |
| (Upcoming) ADR-012 (Feature Store for Predictive ETA) | **May inform** | If we adopt Delta, its CDF (Change Data Feed) is a candidate source for the feature store streaming ingest. |

---

## 4. Decision

> State **the chosen approach**, clearly and in the present tense. Then explain *why* this choice best resolves the forces described in Context.

We **will** [verb phrase the decision]. Specifically:

1. **[Concrete action / component 1]**: [e.g., "Adopt Delta Lake 3.0 (delta-spark 3.0.0, delta-rs 0.17+) as the open table format for the Silver and Gold storage zones."]
2. **[Concrete action / component 2]**: [e.g., "Migrate all existing Silver and Gold Parquet tables to Delta during a maintenance window, phased by domain (rail first, then port, then finance), starting 2025-07-07."]
3. **[Concrete action / component 3]**: [e.g., "Retire manual backfill scripts; replace with Delta MERGE operations using the bronze `__ingest_ts` watermark column."]
4. **[Concrete action / component 4]**: [e.g., "Enable Delta Change Data Feed (CDF) on Gold fact tables from launch date, in support of the future ADR-012 feature store."]

### 4.1 Rationale (Why This Choice)
[2–4 paragraphs. Tie directly to forces from §3.

Example:
Delta Lake best balances the three pain points against the five constraints:

- **Schema evolution**: Delta supports adding columns with `ALTER TABLE ADD COLUMN` in sub-second metadata operations, no rewrite required. This directly resolves pain point 1.
- **Time travel**: Delta's 30-day default log retention allows `VERSION AS OF` or `TIMESTAMP AS OF` in seconds. We will increase retention to 90 days for Silver / Gold to match our current backup policy. This resolves pain point 2 without a custom backup/restore system.
- **ACID MERGE**: Delta `MERGE` with `WHEN MATCHED UPDATE / WHEN NOT MATCHED INSERT` semantics, combined with CDF, eliminates the duplicate-row problem. Pain point 3 is addressed natively.

On constraints:
- **Cost**: Delta is free, open-source under Apache 2.0. Migration compute will use ~150 DBU of existing Databricks capacity (~€1,200 within budget). No incremental recurring cost.
- **Compatibility**: Serverless SQL supports Delta via `BULK OPENROWSET` and external tables — the same path we use today. BI dashboards require only a connection string parameter change (`deltaFormatVersion=3`) validated in DEV on 2025-06-22.
- **Team skills**: Delta's Spark API is a drop-in replacement for Parquet (`.format("delta")` instead of `.format("parquet")`). The learning curve is estimated at <1 week for the team.

Iceberg was a strong contender (see §6), but the team's zero prior experience with it, combined with weaker native Serverless SQL support as of Q2 2025, tips the balance to Delta for this decision cycle.]

---

## 5. Consequences

> Describe **outcomes** of adopting the decision — both positive (benefits) and negative (costs, risks, follow-up work). Be honest and balanced. No decision is free.

### 5.1 Beneficial Consequences
| # | Benefit | Quantified / Measurable? |
|---|---|---|
| C+1 | Eliminates full-table rewrite for most schema changes | Yes: reduces schema-change effort from ~36 hr to <1 hr per change |
| C+2 | Enables sub-minute time-travel recovery for Silver / Gold data | Yes: reduces worst-case recovery time from 11 hr to <5 min |
| C+3 | ACID upserts reduce BI deduplication overhead | Yes: estimated 15% faster dashboard load time (tested in DEV) |
| C+4 | CDF lays groundwork for streaming feature store | Soft: reduces ADR-012 estimated effort by ~30% |
| C+5 | Community adoption and documentation | Soft: larger Delta Lake talent pool available for future hiring |

### 5.2 Negative Consequences / Costs
| # | Drawback / Cost | Mitigation Plan |
|---|---|---|
| C−1 | **Migration effort**: ~40 engineering-hours to write + test migration notebooks + phased cutover | Phased cutover plan: §5.4. Runbook in docs/runbooks/migrate-parquet-to-delta.md |
| C−2 | **New failure modes**: Delta log corruption, orphaned files after failed commits | Enable `vacuum` weekly job with 168 hr (7-day) retention. Alert on `delta_log/_last_checkpoint` write failures. |
| C−3 | **Minor compute overhead**: Delta transaction log writes add ~3% to ETL job duration | Monitor via ADF pipeline telemetry; re-evaluate if overhead exceeds 8%. |
| C−4 | **Storage overhead**: Delta log files + retained versions = ~7% more ADLS bytes vs Parquet | Acceptable; well within storage budget. Vacuum keeps it bounded. |
| C−5 | **Tooling lock-in risk**: If future requirements favor Iceberg (e.g., multi-engine compute), a second migration is needed | Accept as deferred cost; ADR scoped to 3-year horizon. Re-evaluate in ADR review 2026-Q2. |

### 5.3 Risks (Probability × Impact)
| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Incompatibility of Delta 3.0 with current Databricks Runtime 12.2 LTS | Medium (15%) | High — block migration | Already tested DBR 13.3 LTS + Delta 3.0 in sandbox; upgrade DBR to 13.3 LTS as pre-migration step (1-week job). |
| BI report regression during cutover (connection string change) | Low (5%) | High — user downtime | Blue/green migration: run both Parquet and Delta in parallel for 10 days. Swap BI dataset connection only after 10-day reconciliation shows 100% row parity. |
| Team fails to adopt best practices (e.g., forgets VACUUM, misuses OPTIMIZE) | Medium (25%) | Medium — storage bloat / slow queries | 3-hour internal Delta training before go-live. Add automated linter (SQLFluff custom rule) to flag missing `OPTIMIZE` / `VACUUM` in production pipeline scripts. |

### 5.4 Required Follow-Up Actions
| # | Action | Owner | Deadline |
|---|---|---|---|
| F1 | Upgrade Databricks workspace clusters from DBR 12.2 LTS to DBR 13.3 LTS | Platform Eng | 2025-07-03 |
| F2 | Build and test Parquet→Delta migration notebook per domain | Data Eng — Ana | 2025-07-18 |
| F3 | Write cutover runbook + rollback steps | Data Eng — Paul | 2025-07-25 |
| F4 | Conduct Delta training for 4-person analytics engineering team | Tech Lead | 2025-07-31 |
| F5 | Add Delta-specific CI checks to dbt project (`dbt-delta` adapter v1.8) | Analytics Eng | 2025-08-15 |
| F6 | Execute phased migration (rail → port → finance) with 10-day parallel run + parity check for each domain | Data Eng Team | 2025-08-22 |
| F7 | Decommission old Parquet Silver/Gold (VACUUM old zone, read-only archive) | Platform Eng | 2025-09-05 |

---

## 6. Alternatives Considered

> List each plausible alternative (including "do nothing / status quo"). For each, give a short description and explain **why it was not chosen**.

### 6.1 Alternative A: Do Nothing (Stay with Append-Only Parquet)
**Description:** Keep current Parquet-based Silver/Gold zones. Address pain points with custom tooling:
- Schema evolution: Continue full-table rewrites (~36 hr) when columns are added.
- Recovery: Build a custom snapshot/restore system using blob point-in-time restore.
- Deduplication: Add scheduled `dedupe` Spark job (daily) to remove duplicate rows from append-only writes.

**Why NOT chosen:**
- Engineering cost of custom tooling is ~€12,000 (3x the Delta migration budget) + ~€1,000/month ongoing maintenance.
- Snapshot/restore system estimated 6 weeks development — misses the KPI dashboard UAT deadline by 4 weeks.
- Parquet is *already* the worst-performing option on all three measured pain points; doubling down on it with custom fixes has poor ROI.

### 6.2 Alternative B: Adopt Apache Iceberg Instead of Delta Lake
**Description:** Migrate to Apache Iceberg 1.5.x (using Spark iceberg-runtime jar) as the open table format.

**Pluses (Why considered):**
- Multi-engine compute promise (Trino / Flink / Spark) without format conversion.
- Stronger partition evolution semantics than Delta as of 2025-Q1.
- Growing industry backing from Snowflake, Cloudera, Tabular.

**Minuses (Why NOT chosen):**
- **Team skill gap**: Team has zero Iceberg experience. Estimated learning curve = 3–4 weeks, cutting into migration schedule buffer.
- **Serverless SQL compatibility**: Azure Synapse Serverless SQL Iceberg support is *Preview* as of 2025-Q2. Preview features are explicitly excluded from production use per Platform policy (ADR-007). This would force a move to Dedicated SQL Pool (~€6,000/month incremental cost), busting the cost constraint.
- **dbt adapter maturity**: `dbt-iceberg` is community-maintained with ~40k downloads/month vs `dbt-delta` (Databricks-maintained) ~1.1M/month. Higher risk of adapter bugs blocking CI.

**Reconsideration trigger**: If/when Synapse Serverless promotes Iceberg to GA, and the team has completed at least one Databricks certification track including Iceberg, revisit this decision as a new ADR (would supersede this one).

### 6.3 Alternative C: Adopt Apache Hudi Instead of Delta Lake
**Description:** Use Apache Hudi with MOR (Merge-On-Read) tables for upsert-heavy fact tables.

**Why NOT chosen:**
- Hudi's primary strength (very high-volume streaming upserts from Kafka) is not our top use case — our streaming TMS ingest is ~2M rows/day, which all three formats handle easily.
- Smallest community of the three; limited local talent pool.
- Team received a negative reference from internal mining division (TiMeR) that evaluated Hudi in 2024-Q4 and abandoned due to compaction job reliability issues.

### 6.4 Alternative D: Move Gold Zone to a Dedicated Synapse Dedicated SQL Pool
**Description:** Keep Parquet in Bronze/Silver, but load Gold into a Dedicated SQL Pool (DW500c ~ €1,500/month) for T-SQL-based MERGE, backup, and native Power BI import.

**Why NOT chosen:**
- **Cost**: €1,500/month × 12 = €18,000/year vs Delta's ~€0 incremental cost. 15× more expensive, well beyond the €500/month incremental cost cap.
- **Lock-in**: This moves data into a proprietary warehouse format rather than an open table format, which was an *implicit* goal confirmed in the project kickoff (see meeting notes 2025-05-12, item 4).
- **Does not solve the root problem**: Schema evolution in Parquet Bronze→Silver still requires full rewrites, and TMS late-arriving event deduplication still needs workarounds in the Bronze→Silver hop.

---

## 7. Decision Outcomes & Post-Implementation Review

> *To be filled after go-live.*

**Go-Live Date:** [YYYY-MM-DD]
**Initial Review Date:** [YYYY-MM-DD — recommended 4 weeks post go-live]

| Metric | Target (from §4.1 / §5) | Actual | Pass / Fail / Partial | Notes |
|---|---|---|---|---|
| Schema change: add 1 column to 1.8B-row table | ≤ 1 hour | | | |
| Recovery: restore 3 days of Silver data | ≤ 5 minutes | | | |
| BI dashboard load time improvement | ≥ 10% faster | | | |
| Migration engineering effort | ≤ 40 hours | | | |
| Incremental recurring cost | ≤ €500/month | | | |
| Downtime during cutover | 0 minutes (parallel run) | | | |

**Review Outcome / Lessons Learned:**
[Free text. What went well? What surprised us? If we had to make the decision again with hindsight, would we make the same call?]

---

*Document Template Version: 1.0 — Analytics Engineering Team*
*Based on: Joel Parker Henderson's ADR template (adr.github.io) + Michael Nygard's classic format.*
