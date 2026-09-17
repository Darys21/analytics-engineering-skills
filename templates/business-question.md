# Business Question: [Short, Decision-Oriented Title of the Analysis Request]

> **Template Usage**: Fill this document **before** any analysis or development work begins. It is the *contract* between the analytics team and the business stakeholder. If any section cannot be completed, flag it as a *clarity gap* and schedule a meeting with the stakeholder — do not proceed with ambiguous requirements.
>
> **Approval**: This document must be co-signed (written approval) by the Business Owner and the Analytics Engineering Lead before work moves past the discovery phase.

---

## 1. Metadata

| Field | Value |
|---|---|
| **Request ID** | `BQ-YYYY-NNN` (e.g., BQ-2025-047) |
| **Requester** | [Name, Title, Department] |
| **Analytics Owner** | [Name, Title] |
| **Date Submitted** | [YYYY-MM-DD] |
| **Target Delivery Date** | [YYYY-MM-DD] |
| **Priority** | `P0-Critical` / `P1-High` / `P2-Medium` / `P3-Low` |
| **Related Initiative / Project** | [e.g., SETRAG-LGS-003 — Wagon Turnaround Dashboard] |
| **Status** | `Draft` → `Clarifying` → `Approved` → `In Progress` → `Delivered` → `Closed` / `Rejected` |

---

## 2. Problem Statement

> **Describe the pain, not the solution.** Answer: *What is going wrong, or what opportunity is missed?* Use facts, data points, or stakeholder quotes where available. Avoid leading with "we need a dashboard" or "we need SQL" — that belongs in later sections.

**[2–4 paragraph narrative. Example:]**

SETRAG's manganese export logistics division has experienced a 8% YoY decline in monthly export volumes (from 412 k tonnes in H1 2024 to 379 k tonnes in H1 2025) despite mine production remaining stable at ~430 k tonnes/month per the mine production report.

During the same period, demurrage charges paid to vessel operators increased 32% (from €210k H1 2024 to €277k H1 2025), per the Finance demurrage cost report. Informal feedback from the Port Operations team indicates rail wagons are arriving "late and in irregular patterns," causing port crane idle time and forcing vessels to wait at anchorage.

The business currently **cannot answer**:
- Where, exactly, in the rail network wagons are spending their time (which legs, which dwell points, which corridors)?
- Whether the 8% throughput gap is caused by (a) slower wagon turnaround, (b) locomotive capacity, (c) port handling capacity, or (d) a combination.
- Which specific actions (shifts, routes, asset reallocations) would recover the 33 k tonnes/month of lost throughput, and what the expected ROI is for each.

Decisions are currently being made using "gut feel" and weekly static Excel exports. The business is at risk of missing its 2025 annual export target of 5.0 MT, which triggers contractual penalties with the manganese offtake partner.

> **Clarity Gaps (if any):** [List open questions the requester must answer before the team can proceed. E.g., "Requester to confirm whether the 2025 export target is 5.0 MT contractual or 5.2 MT aspirational — KPIs differ."]

---

## 3. Business Objective

> **What does success look like for the business?** Write a single, specific, measurable objective using SMART criteria (Specific, Measurable, Achievable, Relevant, Time-bound). If there are sub-objectives, list them as bullet points below.

### Primary Objective
[1 sentence. Example: "Within 12 weeks, identify the top 3 actionable root causes of Wagon Turnaround Time (WTT) increase and quantify the throughput recoverable by addressing each, enabling the Supply Chain Manager to recover ≥ 25 k tonnes/month of export volume by end-Q4 2025."]

### Sub-Objectives (if applicable)
1. [e.g., Quantify the relative contribution of each dwell-point (port, mine, intermediate station) to total WTT variance.]
2. [e.g., Build a reusable dashboard that lets shift managers monitor WTT in near-real-time and receive alerts when a wagon exceeds threshold dwell time.]
3. [e.g., Produce a prioritized list of 5 operational interventions with estimated ROI (tonnes recovered / € cost / implementation time).]

---

## 4. Stakeholders & Decision Rights

> **Who** is affected by this analysis? **Who** will act on the results? **Who** has the authority to approve changes or budget? Use RACI if roles are non-trivial.

| Role | Name(s) | Involvement | Decision Right? |
|---|---|---|---|
| **Business Owner / Sponsor** | [e.g., M. Diop, Supply Chain Director] | Approves scope, signs off on final recommendations | **YES** — Approves / rejects recommendations and any follow-on projects |
| **Primary Decision-Maker** | [e.g., Mme. Ndong, Rail Operations Manager] | Uses analysis output for day-to-day decisions | **YES** — Acts on operational recommendations; approves dashboard design |
| **Subject Matter Experts (SMEs)** | [e.g., Port Ops Lead, Fleet Maintenance, Train Dispatchers] | Validates assumptions, interprets results, proposes interventions | Consulted (C) |
| **Analytics Team** | [e.g., Ana Silva (Lead), Paul M. (Data Eng), Joan A. (Analytics Eng)] | Delivers analysis, dashboard, report | Responsible (R) |
| **Finance / Controlling** | [e.g., Controller, Logistics Cost Center] | Validates cost/benefit calculations, ROI assumptions | Consulted (C) |
| **End Users (Dashboard Consumers)** | [e.g., Shift Supervisors, Planners] | Uses the operational dashboard post-delivery | Informed (I) |
| **Data Stewards** | [e.g., ERP Data Owner, IoT Platform Owner] | Resolves data quality issues, approves data usage | Consulted (C) |

---

## 5. Decisions Supported

> **What specific decisions** will be made using this work? For each, describe: the decision, who makes it, when it must be made, and what information is required to make it. If you cannot name concrete decisions, the request is probably still too vague — go back to the stakeholder and clarify.

| # | Decision to Be Made | Decision Maker | Deadline | Information Required to Decide |
|---|---|---|---|---|
| D1 | [e.g., **Reallocate 6 locomotives from the Franceville–Lastoursville corridor to Franceville–Moanda** OR keep current allocation.] | Rail Operations Manager | [YYYY-MM-DD — e.g., 8 weeks from kickoff] | WTT by corridor, locomotive utilization %, expected tonnage throughput gain per locomotive moved, impact on the losing corridor |
| D2 | [e.g., **Approve €850k capital request for 2 additional port cranes** OR defer to 2026 budget.] | Supply Chain Director + CFO | [YYYY-MM-DD — e.g., 10 weeks from kickoff] | Current crane utilization %, queuing theory analysis of vessel wait time vs crane count, ROI payback period on demurrage savings |
| D3 | [e.g., **Implement mandatory 48-hour pre-arrival wagon sequencing** OR keep current free-sequencing policy.] | Port Ops Manager + Rail Dispatch Manager | [YYYY-MM-DD — e.g., 6 weeks from kickoff] | Dwell time distribution at port (pre-sequenced vs random), effect on port throughput, operational feasibility cost (staffing, scheduling) |
| D4 | [e.g., **Prioritize maintenance windows for the G-07 Moanda IoT gate** to reduce missing reads vs defer maintenance.] | Infrastructure Manager | [YYYY-MM-DD — e.g., Week 4 (early win)] | Impact of G-07 missing reads on WTT KPI accuracy %, cost of 48-hour maintenance vs benefit of improved KPI |

---

## 6. Success Criteria

> How will we **know** this work was successful? Separate **analytics success** (did we deliver correct, useful insight?) from **business success** (did the business actually improve outcomes?). The latter is not *guaranteed* by analytics alone, but we should define what we're jointly aiming for.

### 6.1 Analytics Delivery Success Criteria (Measured at Delivery)
- [ ] **Root causes identified**: Top 3 root causes of WTT degradation named, each with ≥ 95% statistical confidence (or documented limitation) and ≥ 5% contribution to total WTT variance.
- [ ] **ROI quantified**: Every recommended intervention has a documented, Finance-validated cost estimate, tonnes-recovered estimate, and simple payback period.
- [ ] **No material data surprises**: SME review confirms that analysis conclusions align with their on-the-ground intuition, or any counter-intuitive findings are documented with strong evidence.
- [ ] **Dashboard usable**: Operational dashboard passes UAT with 2/2 shift supervisors signing off that they can find required information in ≤ 3 clicks, and dashboard loads ≤ 5 seconds during peak.
- [ ] **Reproducible**: Third analyst can re-run the full analysis from raw data to final report in ≤ 4 hours using only committed code + instructions (no manual steps).

### 6.2 Business Impact Success Criteria (Measured 90 Days Post-Implementation)
- [ ] **Throughput recovery**: Export volumes recover by ≥ 20 k tonnes/month (target: 25 k) in Q4 2025 vs Q2 2025 baseline, *controlling for* mine production variation and weather days.
- [ ] **WTT improvement**: Fleet-average Wagon Turnaround Time drops from current baseline of 7.8 days to ≤ 7.0 days (target: 6.5 days).
- [ ] **Demurrage reduction**: Monthly demurrage charges decline by ≥ 15% (≥ €35k/month savings).
- [ ] **Decision adoption**: ≥ 3 of the 4 decisions in §5 are made *using* the analysis (not just coincidentally).

---

## 7. KPIs / Metrics to Be Produced

> Which specific metrics will the analysis or dashboard produce? Reference the master list in `CONTEXT.md §4` where applicable. Add any one-off / analysis-specific metrics.

| # | Metric Name | Type | Reference (if standard) | Definition / Formula (one-off metrics) |
|---|---|---|---|---|
| M1 | **Wagon Turnaround Time (avg, median, p90, p95)** | KPI | KPI-01 | Per CONTEXT.md §4.1 |
| M2 | **Dwell Time breakdown: by location, by shift, by wagon type** | Analysis | KPI-02 variant | `DATEDIFF(hour, location_arrival_ts, location_departure_ts)` aggregated |
| M3 | **Locomotive Utilization by corridor** | KPI | KPI-05 | Per CONTEXT.md §4.1, sliced by `corridor_id` |
| M4 | **Port crane utilization (hourly, daily)** | Analysis | *One-off* | `SUM(crane_active_seconds) / (crane_count * 3600)` per hour |
| M5 | **Vessel anchorage wait time (avg, p90)** | Analysis | *One-off* | `DATEDIFF(hour, vessel_eta_port, vessel_berth_start_ts)` |
| M6 | **WTT variance decomposition (ANOVA)** | Statistical | *One-off* | % of total WTT variance explained by: corridor, season/weather, wagon age, locomotive type, shift, port congestion factor |
| M7 | **Intervention cost–benefit matrix** | Decision | *One-off* | For each proposed action: `{ intervention, upfront_cost_€, recurring_cost_€/mo, tonnes_recovered/mo, payback_months, risk_level }` |

---

## 8. Dimensions / Grain / Timeframe

> Answer the reporter's questions: **Who, What, When, Where, How fine?**

### 8.1 Analysis Dimensions (Categorical Slices Required)
| Dimension | Values / Granularity | Mandatory? |
|---|---|---|
| **Time** | Hourly (IoT), Daily (operational), Weekly (trend), Monthly (management), Quarterly (YoY) | YES (all) |
| **Corridor / Route** | Origin↔Destination pair (Franceville↔Port Owendo, Franceville↔Moanda, etc.) | YES |
| **Location / Site** | Port, Mine, Stations, Gates (G-01..G-12), Berths, Cranes | YES |
| **Asset Type** | Wagon type (open-top, covered, tanker), Locomotive model | YES |
| **Product / Cargo** | Manganese lump, Manganese sinter, Other (if any) | YES |
| **Shift / Crew** | Morning / Afternoon / Night; Locomotive crew team | YES (aggregate ≥ 5 per cohort per labor rules) |
| **Weather** | Rainfall bucket (none / light / heavy), temperature bucket | Optional (control variable) |
| **Wagon Age Bucket** | <5 yr, 5–10 yr, 10–15 yr, >15 yr | Optional (for variance decomposition) |

### 8.2 Grain of Analysis / Output
- **Operational dashboard fact grain:** `1 row = 1 wagon's movement across 1 leg (origin→destination pair of consecutive gates)` — i.e., `fact_wagon_leg_movement`.
- **Management summary grain:** `1 row = 1 day × 1 corridor` for KPIs.
- **Root-cause statistical analysis grain:** `1 row = 1 completed wagon cycle (port-to-port)` — for ANOVA / regression.

### 8.3 Timeframe of the Analysis
| Boundary | Value | Rationale |
|---|---|---|
| **Historical start date** | `2024-01-01` | Provides 18 months of pre-decline baseline, enabling YoY + seasonal comparison. Excludes pre-2024 per ASM-006 (CONTEXT §11). |
| **Historical end date** | `[YYYY-MM-DD — last full closed month before kickoff]` | Uses data that is post-month-end-freeze, not subject to Port Ops T+48 corrections. |
| **Forecast / projection period** | 12 months (through end of next FY) | For intervention benefit projections. |
| **Dashboard refresh cadence** | Near-real-time (≤ 15 min lag) for IoT-sourced operational metrics; daily batch for ERP / finance-sourced metrics. | Per SLA in CONTEXT §7.1. |

---

## 9. Data Availability & Constraints

> Which **data sources** will be used (reference CONTEXT §5)? Which are **not** available or cannot be used? Any constraints on combining, exporting, or sharing?

### 9.1 Data Sources In Scope
| Source ID (CONTEXT §5) | Will Use? | How Used in This Analysis | Restrictions on Use |
|---|---|---|---|
| SRC-01 (ERP Sage X3) | ✅ Yes | Order line quantity, product, customer, invoice amounts for OTIF + revenue-per-wagon | No individual customer PII in dashboard (aggregate only) |
| SRC-02 (TMS OTM) | ✅ Yes | Wagon movement timeline, train composition, itinerary | Use `event_ts + mvt_id` dedup per DI-003 |
| SRC-03 (IoT Gates) | ✅ Yes | Actual wagon passage events for dwell / WTT calcs | G-07 fallback per DI-001 |
| SRC-04 (Wagon GPS) | ✅ Yes | Backup for G-07; distance / speed validation | Map-matched distances only per DI-004 |
| SRC-05 (Port Ops) | ✅ Yes | Berth schedule, crane activity, cargo handling | Watermark preliminary current-month data per DI-005 |
| SRC-06 (CMMS Maximo) | ✅ Optional | Locomotive maintenance windows, wagon age | Map locomotive ID per DI-006 |
| SRC-07 (Weather) | ✅ Optional (control) | Daily rainfall, temperature per station | Correlation only — no causal claims |
| SRC-08 (Finance Allocations) | ✅ Yes | Cost-per-NT-km (KPI-07), demurrage costs (KPI-09) | Fleet/corridor aggregates only; DO NOT use at wagon level per SRC-08 notes |

### 9.2 Data Sources Explicitly Out of Scope
| Source / Data Type | Why Excluded |
|---|---|
| Individual driver performance metrics (GPS, hours worked) | Labor agreement constraint per CONTEXT §7.2 — only cohort-level (≥ 5) aggregates allowed |
| Individual customer contract terms (unit price per offtake) | Commercial confidentiality. Only Finance-approved total-cost / total-revenue aggregates may be used. |
| Real-time locomotive engine telemetry (fuel consumption, etc.) | Not yet onboarded (Project ID: SETRAG-FLT-017, ETA 2026-Q1). Flag for Phase 2 if needed. |
| Pre-2024 historical data | Per ASM-006 (CONTEXT §11); would require 6-week reconstruction effort not in budget. |

### 9.3 Data Quality Risks (From CONTEXT §8) Mitigated In This Work
| Issue ID | Mitigation Applied Here |
|---|---|
| DI-001 (G-07 missing reads) | Use GPS geofence fallback; document in methodology section of report. Sensitivity test: calculate WTT both with and without G-07 cycles, show difference is < 2% at fleet level. |
| DI-005 (Port Ops 48 hr correction) | Analysis excludes current open month. Applies watermark to dashboard for any T / T-1 data shown. |
| DI-006 (Locomotive ID mismatch) | Pre-2024 data excluded anyway; for 2024+ unmatched ~2%, treat as "unknown fleet" cohort and disclose in dashboard footnote. |

---

## 10. Assumptions

> What do we **assume to be true** for this analysis, but haven't verified? List them. For each, document: *How will we validate this assumption before finalizing?* and *What happens if it's wrong?*

| # | Assumption | Validation Method | If Violated — Impact |
|---|---|---|---|
| A1 | **Port-to-port cycle is the correct KPI-01 definition** (ASM-001 in CONTEXT §11). Alternative definitions (e.g., station-to-station) would yield different numbers. | Signed written alignment from Supply Chain Director by Week 2. | If wrong: re-define KPI, re-compute all WTT stats, adjust baseline. 2–3 days of rework. |
| A2 | **UOM consistency** between ERP `ordered_qty` and `delivered_qty` for OTIF calcs (ASM-002). | Run validation query in Week 1: `COUNT(*)` where `ordered_uom != delivered_uom`. If < 0.5% of lines, accept; otherwise build UOM conversion table. | If wrong: OTIF KPI materially incorrect — lose stakeholder trust. |
| A3 | **No commercial contract regime change** during the analysis period (ASM-005). A new demurrage clause effective 2025-06-01 could make pre/post unfair. | Review commercial contract log with Commercial team in Week 1. Include contract-change covariate in trend analysis. | If violated: segmentation of pre/post period required; different baseline for period-over-period comparison. |
| A4 | **Mine production capacity is not the bottleneck** (stated in problem statement: mine production stable at ~430kT/mo vs exports ~379kT/mo). | Confirm against mine production report (SRC: Mine Planning dept, not in our 8 sources) — obtain via Business Owner in Week 1. | If violated: re-scope analysis to include mine output bottleneck; different levers. |
| A5 | **Weather (rainfall) explains ≤ 10% of WTT variance** (i.e., is a small control variable, not the dominant driver). | Include in ANOVA variance decomposition (metric M6). If weather explains > 20%, add a dedicated weather-adjusted WTT section. | If violated: analysis needs weather-normalized baseline; recommendations may shift to drainage / timetable adjustment instead of asset allocation. |
| A6 | **Dashboard user base: 50 concurrent consumers max** during peak, per CONTEXT §7.1 constraint. | Confirm with Business Owner — if actual expected > 50, escalate to Platform for capacity adjustment. | If violated: performance SLA (5s load) may fail. |

---

## 11. Scope Exclusions (What We Will *Not* Do)

> Explicitly list anything that could *reasonably be misinterpreted* as in scope, but is not. Prevents scope creep.

1. **No prescriptive scheduling optimization engine**. This analysis identifies bottlenecks and quantifies interventions. Building a real-time MILP-based train scheduler is a separate project (estimated ~€250k, 9 months). Requester to raise as follow-on if needed.
2. **No individual performance management**. Per labor rules (CONTEXT §7.2), the dashboard and report will NOT display data drillable to an individual driver or operator. Minimum cohort = 5.
3. **No prediction / ML model as part of MVP** (Phase 1). Predictive ETA for wagons is in Phase 2 scope (Project SETRAG-LGS-004) if Phase 1 proves value.
4. **No data from third-party ERP of mining offtake partner** (e.g., customer-side receiving data). We cannot access their systems per contract. Customer-side OTIF must be estimated from our shipment data + their monthly summary PDF extracts (if provided).
5. **No real-time vessel tracking (AIS)** data integration. Port Ops has a separate tool for this. We use only SRC-05 (scheduled / actual berth times).
6. **No mobile / tablet UI adaptation** for the dashboard in Phase 1. MVP is desktop-only; mobile to be evaluated in Phase 2 user feedback.

---

## 12. Approvals

> Sign-off that the business question is well-defined, all sections are accurate, and the analytics team may begin work.

| Role | Name | Signature / Written Approval | Date |
|---|---|---|---|
| **Business Owner / Sponsor** | [Printed Name] | [e.g., "Approved via email dated 2025-XX-XX — M. Diop"] | [YYYY-MM-DD] |
| **Analytics Engineering Lead** | [Printed Name] | [e.g., "Approved, scope understood, success criteria measurable — A. Silva"] | [YYYY-MM-DD] |
| **Finance Representative** (if cost/benefit involved) | [Printed Name] | [Optional — e.g., "Cost data access approved, SRC-08 corridor-only restriction noted"] | [YYYY-MM-DD] |

---

*Document Owner: Analytics Engineering Team*
*Last Updated: [YYYY-MM-DD]*
