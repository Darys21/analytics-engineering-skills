# Analysis Report: [Title of the Analysis / Study]

> **Template Usage**: Final deliverable document summarizing a completed analytics engagement. Should be written for a mixed audience: executives (skim §1 + §7 + §8), managers (read §1–§3 + §5 + §7), and technical analysts (deep-dive §4 + §6 + Appendices).
>
> **Companion documents**: Reference `business-question.md` (the request that started this), `CONTEXT.md` (master glossary / data definitions), and the code / notebooks in the repo.

---

## 1. Metadata

| Field | Value |
|---|---|
| **Report ID** | `RPT-YYYY-NNN` (e.g., RPT-2025-019) |
| **Related Business Question** | [Link to BQ-YYYY-NNN / business-question.md] |
| **Prepared For** | [Business Owner name(s) + title(s)] |
| **Prepared By** | [Analytics team members — roles: Lead Analyst, Data Engineer, SMEs consulted] |
| **Date Published** | [YYYY-MM-DD] |
| **Version** | `1.0` |
| **Status** | `Draft` / `For Review` / `Final Approved` |
| **Classification** | `Internal Use` / `Confidential` / `Restricted (Named Recipients)` |

### Revision History
| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | [YYYY-MM-DD] | [Name] | Initial draft for internal review |
| 0.9 | [YYYY-MM-DD] | [Name] | Incorporated SME feedback; added sensitivity analysis §6.4 |
| 1.0 | [YYYY-MM-DD] | [Name] | Final approved version for distribution |

---

## 2. Executive Summary

> **Read this first — 1 page max.** Written for time-constrained executives. Answer four questions:
> 1. **What problem did we study?** (1 sentence)
> 2. **What did we find?** (Top 3 findings, each 1 sentence + a number)
> 3. **What do you recommend we do?** (Top 3 ranked recommendations)
> 4. **What is the estimated business impact?** (Quantified: €, tonnes, days, payback)

**[Write 3–5 tight paragraphs. Example structure:]**

This report analyzes the 8% year-over-year decline in SETRAG manganese export volumes (H1 2024 vs H1 2025) despite stable mine production, and the concurrent 32% increase in vessel demurrage charges. The analysis covers 18 months of wagon movement data (Jan 2024 – Jun 2025), combining TMS transaction records, IoT gate reads, port operations logs, and finance cost allocations per the approved scope in `BQ-2025-047`.

### Key Findings
1. **Port-side dwell is the dominant bottleneck.** Port Owendo average wagon dwell time before unloading increased from 9.1 hr (H1 2024) to 16.4 hr (H1 2025), accounting for **58% of the total Wagon Turnaround Time (WTT) increase**. This is driven by crane saturation and poor inbound wagon sequencing.
2. **Locomotive allocation is suboptimal by corridor.** The Franceville–Lastoursville corridor operates at 59% locomotive utilization vs Franceville–Moanda at 91%, yet Moanda carries 62% of total tonnage. Reallocating assets could recover ~15 k tonnes/month with zero capital expenditure.
3. **Demurrage charges are forecast to exceed €3.6M annually** if current trends continue (Q2 2025 run rate), a 70% YoY increase. Approximately €2.1M of this is avoidable with the interventions below.

### Top Recommendations (Ranked by Net Benefit)
| Rank | Recommendation | Cost | 12-Month Benefit | Net | Payback |
|---|---|---|---|---|---|
| 1 | **R1**: Reallocate 6 locomotives Franceville-LT → Franceville-Moanda corridor | €0 (reallocation) | €780k demurrage saved + 182 kT extra throughput | **€780k** | Immediate |
| 2 | **R2**: Implement mandatory 48-hour pre-arrival wagon sequencing at Port Owendo | €45k (TMS config + training) | €620k demurrage saved + 144 kT extra throughput | **€575k** | 1 month |
| 3 | **R3**: Approve 2 additional rubber-tyred gantry (RTG) cranes at Port Owendo | €850k capital | €1,020k demurrage saved + 276 kT extra throughput | **€170k Year 1; €1,020k/yr Y2+** | 10 months |

### Expected Business Impact (If All R1–R3 Implemented)
- **WTT improvement**: Fleet average from 7.8 d → 6.2 d (exceeds the 6.5 d stretch target).
- **Throughput recovery**: ~+50 k tonnes/month (600 kT/year), recovering 150% of the current 33 kT monthly gap.
- **Cost savings**: ~€2.42M annualized demurrage reduction.
- **Payback on total capital + operating cost**: 5.1 months.

> **Decision Requested:** Business Owner to approve R1 and R2 for immediate implementation, and approve R3 capital request to proceed to 80/20 detailed engineering and CFO sign-off.

---

## 3. Business Context

> **Frame the problem** for readers who didn't live the engagement. Reference the business question document. Keep this section short — 2–4 paragraphs. Readers who want deep context should follow the link to `CONTEXT.md`.

**[Example:]**

This engagement responds to Business Question `BQ-2025-047`, approved by Supply Chain Director M. Diop on 2025-07-02. The full scope, success criteria, and stakeholder list are documented in `/docs/business-question.md` in this repository.

### 3.1 Business Situation (Brief)
- **Export volume gap**: H1 2024 = 412 kT/month avg; H1 2025 = 379 kT/month avg (−8%) while mine production held steady at ~430 kT/month.
- **Demurrage cost**: H1 2024 = €210k total; H1 2025 = €277k (+32%), accelerating in Q2.
- **Driver for action**: Contractual 2025 export target = 5.0 MT; miss triggers penalty clauses in the offtake agreement estimated at €12–18M.

### 3.2 Objectives (From BQ-2025-047)
1. Identify top 3 actionable root causes of WTT increase with ≥ 95% confidence.
2. Quantify throughput recoverable by each proposed intervention.
3. Deliver an operational dashboard for near-real-time WTT monitoring by shift managers.

### 3.3 Stakeholders Consulted
- Rail Operations Manager, Port Ops Lead, Fleet Maintenance Supervisor, 2 Shift Supervisors, Finance Controller (Logistics Cost Center), Commercial Manager (Offtake Contracts).

---

## 4. Methodology

> **Transparency about HOW we arrived at our answers.** This section should be detailed enough that a competent analyst from another team could reproduce your work without asking you questions. Break it into subsections.

### 4.1 Scope & Assumptions
**Analysis Period**: `2024-01-01` to `2025-06-30` (18 months), excluding the current open month of July 2025 per Port Ops data freeze policy.

**Core assumptions (validated per §10 of the business question document):**
| Assumption | Validation Outcome |
|---|---|
| A1: Port-to-port is the correct WTT definition | ✅ Confirmed in writing by Supply Chain Director, 2025-07-10 |
| A2: UOM consistency in ERP order/delivery qty | ✅ Mismatch rate = 0.21% (< 0.5% threshold); accepted with no conversion needed |
| A4: Mine production ≠ bottleneck | ✅ Confirmed via Mine Planning dept data — avg monthly output = 432 kT; max capacity = 475 kT |
| A5: Weather ≤ 10% of WTT variance | ⚠️ Partially violated — ANOVA shows weather explains 12.4% of variance; included as covariate in model |

**Exclusions per BQ scope (unchanged):**
- No individual driver/operator-level reporting (cohort ≥ 5 only).
- No MILP scheduling optimization (separate project).
- No predictive ML / ETA model in Phase 1.

### 4.2 Data Sources & Quality Assessment

| Source ID (CONTEXT §5) | Records Used | Known Issues Applied | Quality Score Assessment |
|---|---|---|---|
| SRC-01 (ERP Sage X3) | 18,432 shipment lines; 586 invoices | STA filter used: IN('5','5A','5B') per DI-002 | **A−** (0.21% UOM mismatch; low impact) |
| SRC-02 (TMS OTM) | 4.1M wagon movement events | Dedup by `mvt_id + event_ts` rank per DI-003 | **B+** (0.34% residual dups after dedup; monitored) |
| SRC-03 (IoT Gates) | 12.7M gate passage events | G-07 fallback to SRC-04 GPS per DI-001 | **A−** (G-07 ~4% missing handled; residual impact <2% at fleet level per sensitivity test) |
| SRC-04 (Wagon GPS) | 89M GPS pings | Map-matched distances only per DI-004 | **B+** (map-match overstatement reduced to <0.7%) |
| SRC-05 (Port Ops) | 6,211 cargo handling records; 218 vessel calls | Closed months only (not current) per DI-005 | **A** (no known material issues in closed data) |
| SRC-06 (CMMS) | 3,412 work orders; 79,200 asset status events | Locomotive mapping via `ref_locomotive_map` per DI-006 | **B** (2.1% unmatched 2024+; disclosed in reporting) |
| SRC-07 (Weather) | 26,280 hourly readings × 3 stations | Used as covariate only; no causal claims | **A** (public source, well-documented) |
| SRC-08 (Finance) | 18 monthly cost center allocation files | Used at corridor/fleet level only (no wagon-level) per SRC-08 note | **B+** (allocations are approximations; acceptable for trend / ROI analysis) |

**Overall data quality assessment**: Fit for purpose with documented mitigations. Three sensitivity tests (§6.4) confirm that known data issues change headline findings by < 4% in the worst case.

### 4.3 Analysis Approach (Step-by-Step)

**Phase 1 — Data Integration & Cohort Building (Weeks 1–2)**
1. Built a unified `wagon_cycle_fact` CTE (dbt model: `fact_wagon_cycle`), linking every port-departure → empty-port-return cycle across TMS events and IoT gate reads. Grain = 1 completed wagon cycle.
   - Cycles with missing intermediate events: 3.8% (flagged, excluded from per-leg analysis, included in fleet totals with completion-rate weighting).
   - Cycles > 30 days (outlier): 0.4% (reviewed individually — all valid: maintenance holds, out-of-gauge cargo).
2. Enriched cycle fact with:
   - Weather data (daily rainfall at origin + destination midpoint)
   - Locomotive attributes (age, model, horsepower, maintenance status)
   - Wagon attributes (type, capacity, year built)
   - Corridor / route attributes (distance, track class, number of intermediate stations)
3. Final analysis dataset: **2,142,897 completed wagon cycles** with 43 columns. Full SQL: `models/marts/logistics/fact_wagon_cycle.sql`.

**Phase 2 — Descriptive & Diagnostic Analysis (Weeks 3–4)**
1. **Pareto decomposition** of WTT into component dwell legs: port-in, port-out, loading-unloading, travel, intermediate-station, other.
2. **Segmentation analysis** by corridor, product, locomotive model, shift pattern, season (wet/dry).
3. **Before/after comparison** (H1 2024 vs H1 2025) on each dimension, with two-sample Mann-Whitney U tests for statistical significance of distribution shifts (not just mean).
4. **ANOVA variance decomposition** (% of total WTT variance explained by each factor) using `statsmodels` OLS ANOVA Type II (to handle unbalanced design). Notebook: `notebooks/20250715_js_wtt_variance_decomposition.ipynb`.

**Phase 3 — Intervention Simulation & ROI (Week 5)**
1. For each proposed intervention, built a **what-if simulation model** on the analysis dataset:
   - **R1 (Locomotive reallocation)**: Simulated moving 6 locomotives from the 5th quintile of utilization to the 1st quintile; modeled resultant wagon-cycle throughput gain via Little's Law (L = λW) holding total wagon fleet constant.
   - **R2 (Wagon sequencing)**: Estimated effect size from the 14% of current cycles that arrive in a naturally-sequenced batch (control group) — their port dwell time was 38% shorter. Applied this effect size (capped at −30% conservatively) to 80% of cycles (the maximum feasible sequencing rate per TMS team).
   - **R3 (Additional cranes)**: Queuing theory (M/M/c model) with current λ = 248 wagons/day, μ = 42 wagons/day per crane, c = 4 → current ρ ≈ 1.48 (saturated). Simulated c = 6 → ρ = 0.98. Derived port dwell distribution from model output.
2. **Cost side of ROI**: Obtained validated cost estimates:
   - Locomotive reallocation: €0 operating cost (reallocation), €12k one-time training / timetable adjustment.
   - Wagon sequencing: €32k TMS configuration + €13k 2-week training + €0 recurring.
   - Crane purchase: €425k/unit capital × 2 = €850k; €90k/unit/year operating cost.
3. Payback period = Total one-time cost / (monthly benefit × 12).

**Phase 4 — Validation & Sensitivity (Week 6)**
1. SME walkthrough of preliminary findings with Ops managers — confirmed qualitative plausibility; one adjustment (R2 sequencing feasibility capped at 80% from 100%).
2. Three sensitivity tests (§6.4) on data quality edge cases.
3. External benchmark check: WTT of 7.8 d vs African rail peer benchmark range of 5.5–9.5 d (per UNCTAD 2024 Rail Logistics Report) — plausible, slightly above median.

### 4.4 Reproducibility Notes
- **Environment**: Databricks Runtime 13.3 LTS, Python 3.10.12, dbt-core 1.7.4, dbt-databricks 1.7.6, statsmodels 0.14.2, scipy 1.11.4, pandas 2.1.4.
- **Random seed**: `42` for all simulation runs.
- **Commit**: All analysis code committed to repo at tag `v1.0.0-rpt-2025-019`, SHA `a73f9c2`.
- **Full reproduction runbook**: `docs/runbooks/reproduce-rpt-2025-019.md` — 17 steps, ETA 3h20m on a Standard_DS13_v2 cluster.

---

## 5. Results & Findings

> **Present the evidence.** Structure each finding with: a **claim sentence** (bold), followed by **supporting data** (tables / chart references / statistical test results), then **interpretation** (what the number *means* for the business).
>
> Order findings from most impactful to least impactful.

---

### Finding 1 — Port Dwell Time at Owendo Is the #1 Bottleneck (58% of WTT Increase)

**The single largest driver of WTT degradation is the near-doubling of average port dwell time before unloading at Port Owendo, from 9.1 hr (H1 2024) to 16.4 hr (H1 2025). This single factor explains 58% of the total increase in fleet-average WTT.**

**Supporting Data:**
| Component | H1 2024 Avg | H1 2025 Avg | Δ Absolute | Δ % | % of Total WTT Δ |
|---|---|---|---|---|---|
| Port Dwell (pre-unload) | 9.1 hr | 16.4 hr | +7.3 hr | +80.2% | **58.0%** |
| Intermediate Station Dwell | 4.8 hr | 6.7 hr | +1.9 hr | +39.6% | 15.1% |
| Mine Loading Dwell | 6.2 hr | 7.8 hr | +1.6 hr | +25.8% | 12.7% |
| Travel Time (in motion) | 28.4 hr | 29.8 hr | +1.4 hr | +4.9% | 11.1% |
| Post-Load / Departure Prep | 5.7 hr | 6.3 hr | +0.6 hr | +10.5% | 3.1% |
| **Total WTT** | **54.2 hr ≈ 2.26 d** (port-leg only component shown; full cycle = 7.8 d) | **67.0 hr ≈ 2.79 d** (port-leg only) | **+12.8 hr** | **+23.6%** | **100%** |

*Note: Table shows the port-leg dwell sub-components which add up to the total port-in-to-port-out time increase. The full WTT (7.8 d) includes the loaded + empty return rail legs — their change was small (+4.9%) and not statistically significant.*

**Statistical Significance**: Two-sample Mann-Whitney U test on port dwell distributions: U-statistic = 2.14×10¹¹, *p* < 10⁻¹⁶ (highly significant; distribution has shifted, not just the mean).

**Interpretation**: In H1 2024, the port was essentially keeping up with rail arrivals. In H1 2025, the port has become the bottleneck. This is not a rail-network speed problem — wagons are moving at essentially the same speed on the tracks. They are **waiting longer to unload at the port**. This is consistent with port anecdotal feedback (crane saturation) and with the vessel demurrage increase (vessels are waiting because wagons can't unload fast enough to release the next vessel).

**Chart References**:
- Appendix A, Fig 1: WTT component stacked bar (monthly, Jan 2024 – Jun 2025) — visually shows the port-dwell orange segment growing after Jan 2025.
- Appendix A, Fig 2: Port dwell time distribution H1 2024 vs H1 2025 (density plot + box plot) — shows right tail fattening with p90 going from 22 hr to 48 hr.

---

### Finding 2 — Locomotive Allocation Between Corridors Is Highly Inefficient

**Franceville–Moanda corridor (62% of tonnage) operates locomotives at 91% average utilization vs Franceville–Lastoursville at only 59% — a 32 pp gap. There is no technical or contractual reason why locomotives cannot be reallocated. Doing so is a zero-capital "quick win."**

**Supporting Data:**
| Corridor | Tonnes/mo (H1 2025) | % of Total | Locomotive Fleet Avg Utilization | Locomotive Count | Tonne-km / Locomotive / Day |
|---|---|---|---|---|---|
| Fville–Owendo (Main Export) | 217 kT | 57.3% | 78% | 22 | 8,920 |
| **Fville–Moanda (Mine)** | **235 kT** | **62.1%** | **91%** | **18** | **12,430** |
| Fville–Lastoursville (LT) | 74 kT | 19.5% | 59% | 12 | 5,610 |
| Fville–Mounana (Small) | 28 kT | 7.4% | 71% | 4 | 6,580 |
| Other / Ad-hoc | ~5 kT | 1.3% | N/A | 3 (pool) | N/A |
| **Fleet Total** | **379 kT** | **100%** | **77.5%** | **59** | — |

*Note: % of total tonnage sums to > 100% because a wagon may serve 2 segments per cycle.*

**Statistical Significance**: The 32 pp utilization gap is 4.2× the typical 7.6 pp month-to-month standard deviation in corridor utilization — highly unlikely to be random. Confirmed against 18-month history: Moanda utilization ≥ Lastoursville + 25 pp in every month since Aug 2024.

**Interpretation**: The rail network has enough aggregate locomotive capacity to close the throughput gap. The problem is that some locomotives are "idling" (or lightly used) on a lower-tonnage corridor while the highest-tonnage corridor is starved. Reallocating 6 locomotives (half of the surplus on Lastoursville) is modeled to increase Moanda throughput by ~15 kT/month with zero new capital cost. No new drivers would need to be hired — Lastoursville driver pool would shrink by the same headcount that Moanda grows by (net zero hiring).

**Operational feasibility check**: Per Fleet Maintenance and Dispatch managers, the locomotive pool is already fungible — there is no physical restriction on which corridor a locomotive serves. Last reallocation of this type was done in March 2024 (different corridors), completed in 3 business days with zero incidents.

---

### Finding 3 — Poor Inbound Wagon Sequencing Adds ~6 Hr of Port Dwell Per Cycle

**14% of cycles arrive in a naturally "good sequence" (same product, same destination vessel, consecutive in the consist). These cycles experience 38% lower port dwell time (avg 10.4 hr vs 16.7 hr for poorly sequenced). Mandatory 48-hr pre-arrival sequencing at the dispatch yard is expected to bring 80% of cycles to at least 80% of this "good sequence" benefit.**

**Supporting Data: Natural Experiment Analysis**

We identified a natural experiment: when a single mine ships 20+ wagons of the same product in a 12-hour window, those wagons tend to arrive at port in product-clustered sequence (whether by design or luck — we verified no formal sequencing rule was in place). We compared this treatment group (N = 142,307 wagon cycles = 13.9% of total) against all others, controlling for port congestion, shift, and product type via ANCOVA.

| Group | Avg Port Dwell | 95% CI | p90 Port Dwell | Sample N |
|---|---|---|---|---|
| **Good Sequencing (treatment)** | **10.4 hr** | [10.2, 10.6] | 24 hr | 142,307 |
| Poor / No Sequencing (control) | 16.7 hr | [16.6, 16.8] | 47 hr | 881,975 |
| **Controlled Δ (ANCOVA)** | **−5.8 hr** | [−5.9, −5.7] | −21 hr | — |

*The ANCOVA controls for: daily port congestion level, 2-hour arrival window bucket, product type, and number of cranes active that day. p-value on the sequencing coefficient: p < 10⁻²⁰⁰.*

**Interpretation**: There is a large, statistically robust, causal-seeming effect from better wagon sequencing. Port cranes spend less time switching between product types and crane moves are shorter (closer together parking positions). The mandatory 48-hr pre-arrival sequencing intervention (R2) requires the dispatch yard to group wagons by product and destination vessel before departure — this is essentially what the "good sequence" group is already doing naturally 14% of the time, but scaled.

We **capped** the expected benefit at **−30% port dwell** (vs the 35% ANCOVA effect) for the ROI model, to be conservative — TMS team advises 100% perfect sequencing is operationally impossible due to mine arrival variation; 80% sequencing rate × 80% of maximum benefit = ~30% net effect.

---

### Finding 4 — Weather Explains ~12% of WTT Variance (Secondary Factor)

**Rainfall and temperature together explain 12.4% of WTT variance (ANOVA Type II). This is larger than we initially assumed (ASM-A5: ≤ 10%), but still secondary to port (58%) and allocation (21%) factors. Heavy-rain days (> 20 mm) increase travel time by ~1.2 hr/cycle (+5%) and intermediate station dwell by ~0.8 hr/cycle (+17%) due to slower safe operating speeds and reduced manual shunting staff.**

**Supporting Data (ANOVA — Full Model R² = 0.612)**:
| Factor | Partial η² | % of Explained Variance | p-value |
|---|---|---|---|
| Port Congestion Index | 0.281 | **45.9%** | < 10⁻³⁰⁰ |
| Corridor × Locomotive Count | 0.145 | **23.7%** | < 10⁻³⁰⁰ |
| Rainfall Bucket (none/light/heavy) | 0.076 | 12.4% | < 10⁻²⁰⁰ |
| Wagon Age Bucket | 0.032 | 5.2% | < 10⁻⁸⁰ |
| Shift (Morn/Aft/Night) | 0.028 | 4.6% | < 10⁻⁷⁰ |
| Product Type | 0.019 | 3.1% | < 10⁻⁴⁰ |
| Locomotive Model | 0.012 | 2.0% | < 10⁻²⁰ |
| Residual (unexplained) | 0.388 | 3.1% (of total) | — |

**Interpretation**: Weather is a real factor (we did not fully dismiss it in our assumptions), but it is not the dominant driver. The 8% YoY throughput decline happened during a period with no YoY increase in rainfall (verified: H1 2024 total rainfall = 612 mm; H1 2025 = 598 mm, essentially flat). So weather cannot explain the *decline* — it just adds noise. We include weather as a covariate in all our before/after comparisons, so our headline numbers are effectively weather-normalized.

**Operational implication**: For the dashboard, we will include a "WTT — Weather Adjusted" metric to prevent the team from being unfairly penalized during a heavy-rain week, or taking credit during a dry spell.

---

### Finding 5 (Secondary) — Fleet Age Correlates With WTT, But Has Modest Impact

Wagons > 15 years old have 1.1 hr/cycle (+4.2%) longer average dwell time than wagons < 5 years. The partial η² = 0.032 (5.2% of variance) — material but not top-3. There are 42 wagons (7% of fleet) > 20 years old. **Replacing the oldest 10% of the fleet is a valid medium-term investment** (estimated 1.2% WTT improvement per €2.5M capex), but does not crack our top 3 recommendations because payback is ~7 years (slower than R1–R3).

---

### Finding 6 (Monitoring) — G-07 IoT Gate Fix Is Still Materially Impactful

Even though we successfully applied the GPS fallback (DI-001), the G-07 Moanda gate missing-read rate still correlates with a ~0.7 hr/cycle increase in Moanda mine dwell time (because the fallback GPS geofence trigger is less precise, causing downstream TMS dispatching logic to occasionally misclassify a wagon as "arrived" and dispatch a loader prematurely, or vice versa). The cost of the 48-hour gate maintenance window is estimated at €18k in planned downtime. Benefit: estimated €47k/year in avoided dwell-time throughput loss. **Simple payback = 4.6 months.** We recommend this maintenance be scheduled for the next planned network shutdown (currently proposed for Sept 2025).

---

## 6. Validation & Limitations

> **Build trust by being transparent about what we do NOT know, what could be wrong, and what simplifications we made.** Readers should come away feeling: "they've thought about this carefully, their numbers are directionally right even if not perfect."

### 6.1 Internal Validation Checks Performed
| Check | Method | Result |
|---|---|---|
| **Row-level reconciliation vs source** | For 1% of cycles sampled (N = 21,429), hand-verified cycle end-to-end against raw SRC-02 + SRC-03 events. | 98.4% match; 1.6% had minor differences due to fallback ordering — no impact on aggregate metrics. |
| **KPI-01 total vs Finance manual report** | Q1 2025 fleet-average WTT from our model vs manually-compiled report from Rail Ops KPI workbook. | Our value = 7.32 d; manual report = 7.28 d; Δ = 0.5%. Within acceptable tolerance. |
| **Port tonnage totals vs Port Ops report** | Monthly port throughput (tonnes) H1 2025. | Sum of squares of relative differences = 0.32%; max Δ on any single month = 1.1%. |
| **Residual analysis (ANOVA model)** | Plot of residuals vs fitted values, Q-Q plot. | Heteroskedasticity minor (Breusch-Pagan p = 0.003; use robust standard errors for CIs, which we did). Residuals acceptably normal for large N. |
| **Outlier removal sensitivity** | Removed top 0.5% WTT cycles (>30 d) vs retaining. | Headline WTT Δ estimate changed by 0.2 days (2.8%). Materiality: low — we kept them as valid. |

### 6.2 External / SME Validation
- **2025-08-07 Ops Review**: Presented preliminary F1 (port dwell bottleneck) to Port Ops + Rail Ops managers. Both stated: "This matches exactly what we see on the ground every day — port crane capacity has been the problem since December." No factual corrections requested.
- **2025-08-11 Finance Review**: Controller validated cost inputs for R1–R3 ROI; noted only one adjustment (crane operating cost should include crane operator labor; we revised R3 operating cost from €75k → €90k/unit/year, reducing Year 1 net benefit from €250k to €170k — still positive).
- **2025-08-13 Dispatch Team Review**: Shift supervisors validated locomotive reallocation (R1) and sequencing (R2) operational feasibility; one adjustment — sequencing feasibility capped at 80% of cycles from 100% (due to mine arrival variation).

### 6.3 Limitations (Caveats for Interpretation)

| # | Limitation | Impact on Findings | How We Mitigated or Suggest User Interpret With Caution |
|---|---|---|---|
| L1 | **No causal RCT** — findings are observational (natural experiment for R2, regression for others). We cannot claim strict causality with p = 0.000 confidence. | Overconfidence risk in recommendations; actual effect may be ± 20–30% of modeled. | All benefit figures are **conservative estimates** (capped). We include a 30% "benefit haircut" scenario in Appendix B and still show positive NPV for all R1–R3. |
| L2 | **SRC-08 Finance allocations are approximations**, not exact wagon-level costing. Cost-per-NT-km (KPI-07) may be ± 8% at corridor level. | ROI figures (especially KPI-07-derived savings) may be off by ~10%. | Used independent verified cost inputs (demurrage actuals, crane capex quotes) wherever possible; only used SRC-08 for small shared-cost allocations. Sensitivity test: ± 10% on cost side — still positive ROI. |
| L3 | **Predictions assume no regime change** (no new labor rule, no new contract structure, no major weather event beyond historical norm). | A black-swan event (e.g., 1-in-20 year rainy season, strike) could materially change outcomes. | Recommendation: Treat 12-month projections as **scenario central**; maintain upside and downside scenarios (Appendix B). Quarterly reforecast. |
| L4 | **No individual driver behavior data** per labor rules. Driver skill / fatigue variance is in the residual (38.8% of WTT variance unexplained). | We may be overestimating how "easy" it is to achieve gains on the ground if driver behavior is the hidden residual factor. | Mitigated via Shift Supervisor validation: they report driver skill variance is "stable and not worsening" over the past 2 years; residual trend is flat (no worsening) — consistent with our belief that residual is random noise, not a trend. |
| L5 | **Queuing model for R3 (cranes) assumes steady-state Poisson arrivals**. Real-world arrivals are bursty (mine shifts, train consists). | Port dwell time for R3 may be slightly (10–15%) higher than M/M/c model predicts in first 3 months of operation as cranes ramp. | In R3 ROI, we applied a 15% haircut to Year 1 benefit. R3 still payback in 10 months. |

### 6.4 Sensitivity Analysis (How Much Could Key Numbers Be Wrong?)

We ran 3 targeted sensitivity tests on our headline results: **"WTT reduction if all 3 R's implemented = from 7.8 d → 6.2 d (−1.6 d or −20.5%)"**

| Sensitivity Scenario | Assumption Change | Headline WTT Result | Δ From Baseline |
|---|---|---|---|
| **Baseline (central scenario)** | All assumptions per §4.1 | **6.20 d (−20.5%)** | Reference |
| **S1: Data quality worst-case** | G-07 fallback +20% error (worse than measured); port ops corrections +5% error; locomotive mapping +4% error (all simultaneously applied to data inputs) | 6.45 d (−17.3%) | +0.25 d (+16% of Δ) — still very material improvement |
| **S2: Intervention benefit 30% haircut** | Assume each intervention delivers 70% of modeled benefit (pessimistic on execution) | 6.65 d (−14.7%) | +0.45 d (+28% of Δ) — still clears the 6.5 d stretch target (6.65 < 7.8; and 6.5 target is the *as-is* KPI not the "after" target) |
| **S3: Simultaneous S1 + S2** | Worst-case data + 30% benefit haircut | 6.89 d (−11.7%) | +0.69 d (+43% of Δ) — still a double-digit percentage improvement; demurrage savings still ~€1.4M/year (well > total cost) |

**Conclusion of sensitivity**: Even under the most pessimistic combination of assumptions, the package of recommendations R1–R3 delivers a double-digit percentage WTT improvement and > €1M annualized demurrage savings. The business case is robust.

---

## 7. Recommendations

> **Actionable list.** Each recommendation has: what to do, who does it, by when, quantified expected benefit, cost, and risk level. Ranked by **net 12-month benefit** (largest first).

### Summary Table
| Rank | ID | Recommendation | Owner | Deadline | 12-Month Gross Benefit (€ + tonnes) | Cost (€) | Net Benefit | Payback | Risk |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **R1** | Reallocate 6 locomotives Fville-LT → Fville-Moanda | Rail Ops Mgr + Fleet Mgr | **4 weeks from approval** | €780k + 182 kT | €12k (one-time) | **€768k + 182 kT** | < 1 month | **Low** |
| 2 | **R2** | Implement 48-hr pre-arrival wagon sequencing (TMS config + training) | Dispatch Mgr + TMS Team | **8 weeks from approval** | €620k + 144 kT | €45k (one-time) | **€575k + 144 kT** | 1 month | **Medium** |
| 3 | **R3** | Approve 2 additional RTG cranes at Port Owendo (capex + install) | Port Ops + CFO | **CFO sign-off → 16 weeks delivery** | €1,020k/yr + 276 kT/yr | €850k capex + €180k/yr op | **−€10k Yr 1; +€840k/yr Y2+** | **10 months** | **Medium** |
| 4 | **R4** | Schedule G-07 Moanda IoT gate hardware maintenance | Infrastructure Mgr | Next network shutdown window (Sep 2025) | €47k/yr + ~2.5 kT/mo | €18k (one-time) | **€29k Yr 1; +€47k/yr** | 4.6 months | **Low** |
| 5 | **R5** | Deploy WTT operational dashboard to shift supervisors (UAT + training) | BI Team + Training | **10 weeks from approval** | Soft benefit: faster issue resolution (~€120k/yr avoided demurrage from faster interventions) | €22k (training + hosting) | **~€98k/yr** | 3 months | **Low** |

---

### Detailed Recommendations

#### R1 — Reallocate 6 Locomotives to the Moanda Corridor (Rank 1, Low Risk, Immediate)
**What to do**: Move 6 locomotives from the Franceville–Lastoursville corridor fleet (12 → 6 locomotives) to the Franceville–Moanda corridor fleet (18 → 24). Reallocate drivers proportionally from the LT driver pool (net zero hiring).

**Why rank 1?**
- **Zero capital cost** (assets already exist).
- **Lowest risk**: Same type of reallocation was done successfully in March 2024 with zero incidents.
- **Fastest impact**: Full effect expected 4 weeks after approval.
- **Benefit comes from two places**: (1) More capacity on the bottleneck corridor; (2) Reduced "empty runs" on the over-resourced LT corridor (KPI-06 empty-km ratio expected to improve 2 pp).

**Implementation steps**:
1. Week 1: Dispatch team publishes revised timetable with new corridor fleet counts.
2. Week 2: Driver rosters adjusted (HR notified — no net headcount change).
3. Week 3: Pilot 3 locomotives one week ahead; monitor corridor utilization for unexpected bottlenecks.
4. Week 4: Deploy remaining 3. Monitor WTT daily via dashboard (R5).

**Risk**: If Lastoursville corridor throughput is impacted more than modeled, 2 locomotives can be swapped back in 24 hrs. We recommend a **2-month probation period** with weekly corridor review.

---

#### R2 — Mandatory 48-Hour Pre-Arrival Wagon Sequencing (Rank 2, Medium Risk)
**What to do**: Configure the TMS dispatch system to require that, at least 48 hours before a wagon consist departs Franceville yard for the port, the wagons are physically re-sorted by (a) product type, (b) destination vessel (when known), and (c) weight class (lightest first to unload fastest). Implement a mandatory "sequence quality check" gate in the TMS departure workflow (cannot depart if sequence score < 80%).

**Why rank 2?**
- Very high benefit-to-cost ratio (€575k net on €45k spend).
- But **requires a change to operational behavior** (dispatchers will need training, and there will be resistance to the extra step in the workflow) → medium adoption risk.
- Effect proven via natural experiment (Finding 3); the effect size is not modeled from thin air.

**Implementation steps**:
1. Weeks 1–2: TMS team builds and tests sequence score logic in UAT.
2. Weeks 3–4: 2-week pilot on 1 shift (Morning) with 2 dispatchers volunteer; measure sequence score vs dwell time vs control shift.
3. Week 5: Adjust threshold if pilot shows 80% is too aggressive (target 70–75% realistically achievable).
4. Weeks 6–7: Mandatory training for all 12 dispatchers across 3 shifts (2-hour session × 2).
5. Week 8: Full rollout to all shifts. Dashboard flag added: "Sequence Compliance %" (R5 dashboard).

**Risk mitigation**: Adoption risk. We recommend the sequence check be "soft block" for first month (warning, can override with reason), then hard block Month 2 if compliance > 75%. Provide monthly €500 team bonus for the shift with best sequence compliance for first 3 months (total €4,500 — absorbed within the €45k budget).

---

#### R3 — Two Additional RTG Cranes at Port Owendo (Rank 3, Medium Risk, Capex Required)
**What to do**: Approve capital expenditure request for 2 additional Kalmar DRG450 rubber-tyred gantry cranes (€425k each list price; procurement estimates €850k total fully installed). Install on berths 3 and 4 at Port Owendo.

**Why rank 3?**
- Largest absolute total benefit once deployed (~€840k net/yr by Year 2).
- But requires **CFO-level capex approval** and 16-week lead time (manufacturing + shipping + commissioning) — slower than R1/R2.
- Year 1 net benefit is near-zero (−€10k) because of upfront capex amortization and 15% ramp-up haircut.

**Implementation steps**:
1. Immediate: Business Owner submits formal capex request to CFO using this report's ROI analysis.
2. Week 1 after CFO approval: Procurement issues RFP (pre-qualified list of 3 vendors).
3. Weeks 4–16: Manufacturing, shipping, installation, commissioning.
4. Week 17: 4-week ramp-up (operator training + real-world tuning).
5. Week 21: Full benefit run-rate expected.

**Risk mitigation**: Supplier delivery risk (lead time slip). We recommend RFP include 10-week delivery bonus (€25k) and 14-week penalty clause (2% of contract price per week late beyond 16 weeks).

---

#### R4 — G-07 Moanda IoT Gate Maintenance (Rank 4, Low Risk, Quick Win)
**What to do**: Schedule 48-hour maintenance window for G-07 Moanda gate (antenna alignment + RFID reader replacement + backup power supply). Perform during the next pre-planned full-network shutdown window (currently scheduled Sept 15–16 2025 per Infrastructure team calendar).

**Why this matters**: Finding 6 shows even *with* GPS fallback, G-07 errors cause ~0.7 hr/cycle Moanda dwell, costing ~€47k/year. Cost of maintenance (€18k) recovers in 4.6 months. Since the network will already be down anyway for other maintenance, there is zero incremental downtime cost.

**Decision required**: Infrastructure Manager to confirm G-07 on the Sept shutdown work order list.

---

#### R5 — Deploy WTT Operational Dashboard to Shift Supervisors (Rank 5, Low Risk)
**What to do**: Roll out the near-real-time WTT dashboard (built during this engagement) to the 6 shift supervisors (Port × 3, Rail × 3), with 2-hour individual hands-on training sessions and a 1-page quick-reference card. Enable Teams-channel alerts for:
- Any wagon > 48 hr in port dwell
- Any corridor locomotive utilization > 95% sustained 6 hr+
- Any 24 hr period where sequence compliance (R2) drops below 70%

**Why**: Dashboards are the *feedback loop* for R1–R4. Without visibility into whether interventions are working day-to-day, benefits will erode over time ("launch and leave").

**Cost**: €22k total (14 days BI dev time + 6 supervisor training days + Power BI embedded capacity bump). Included in Phase 1 project budget.

---

## 8. Business Impact

> **Quantified, consolidated view.** What changes for the business if we implement all recommendations? Provide multiple scenarios.

### Central Scenario (R1–R5 All Implemented, Baseline Assumptions)

| Metric | Current Baseline (H1 2025 Run-Rate) | 12 Months Post-R1–R5 Full Effect | Δ Absolute | Δ % |
|---|---|---|---|---|
| **Wagon Turnaround Time (avg)** | 7.8 days | 6.2 days | −1.6 days | **−20.5%** |
| **Export Throughput / month** | 379 kT | 429 kT | +50 kT / mo | **+13.2%** |
| **Annual Export Throughput** | 4.55 MT (run-rate) | 5.15 MT | **+0.60 MT / yr** | **+13.2%** |
| **Contract Target: 5.0 MT / yr** | ❌ Miss by 0.45 MT | ✅ Exceed by 0.15 MT | +0.60 MT vs target gap | — |
| **Annual Demurrage Cost** | €2.77M (run-rate) | €1.05M | **−€1.72M / yr** | **−62%** |
| **Cost per NT-km (KPI-07)** | €0.0482 | €0.0438 | −€0.0044 | **−9.1%** |
| **Locomotive Utilization (avg)** | 77.5% | 80.2% | +2.7 pp | **+3.5%** (more balanced across corridors) |
| **Empty Running Ratio (KPI-06)** | 24.8% | 22.7% | −2.1 pp | **−8.5%** |
| **OTIF Delivery % (KPI-04)** | 86.1% | 92.8% | +6.7 pp | **+7.8%** (exceeds 92% KPI target) |

### Financial Summary (All R1–R5, 3-Year Horizon, Nominal €, 5% Discount Rate)
| Line Item | Year 0 (2025 Q3–Q4) | Year 1 | Year 2 | Year 3 | 3-Yr Total (Nominal) |
|---|---|---|---|---|---|
| **Gross Benefit** (demurrage saved + throughput margin €22/T) | €325k | €2,565k | €2,565k | €2,565k | €8,020k |
| **Operating Cost** | −€57k | −€202k | −€202k | −€202k | −€663k |
| **Capital Expenditure** (R3 cranes) | −€850k | — | — | — | −€850k |
| **Net Cash Flow (Nominal)** | **−€582k** | **€2,363k** | **€2,363k** | **€2,363k** | **€6,507k** |
| **DCF NPV @ 5%** | — | — | — | — | **€5,842k** |
| **Simple Payback Period** | — | — | **4.8 months** (from R3 capex approval; **3.0 months** ex-capex) | — | — |
| **ROI (3-Year, ex-Capex for pure operating ROI)** | — | — | — | — | **1,315%** |

*Note: Throughput margin per tonne = €22, validated by Commercial Manager as the average variable margin per exported tonne of manganese in 2025 contracts.*

### Scenario Analysis (Appendix B — Sensitivity on All R's Combined)
| Scenario | 3-Yr NPV @ 5% | Payback Period | Meets 5.0 MT Annual Export Target? |
|---|---|---|---|
| **Upside (+20% benefit, −10% cost)** | €7,940k | 3.8 months | ✅ Yes, by +0.3 MT |
| **Central (base)** | €5,842k | 4.8 months | ✅ Yes, by +0.15 MT |
| **Downside (−30% benefit, +15% cost, S1+S2)** | €3,012k | 7.1 months | ⚠️ Just misses (4.98 MT — within 0.4% of target; achievable with 1 extra month of good weather or minor operational tweaks) |

**Worst-case conclusion**: Even under the pessimistic 30% benefit haircut + 15% cost overrun + data quality worst-case scenario, the 3-year project NPV is still **strongly positive (> €3M)**. This package of interventions is a robust business case.

---

## 9. Next Steps

> **Concrete next 4 weeks.** Assign owners and dates. This section bridges from the report into execution.

| # | Action | Owner | Deadline | Dependency |
|---|---|---|---|---|
| 1 | **Business Owner to sign-off on R1, R2, R4, R5** (greenlight implementation) and approve R3 to proceed to CFO capex review | Supply Chain Director (Business Owner) | **2025-08-28** (2 weeks from report publish) | This report |
| 2 | Submit R3 formal capex request (€850k, 2 RTG cranes) to CFO | Port Ops Manager + Finance Controller | **2025-08-29** | Action 1 (R3 approval) |
| 3 | Publish revised locomotive corridor timetable draft (R1) | Rail Operations Manager | **2025-09-03** | Action 1 (R1 greenlight) |
| 4 | R2 — TMS sequence-score logic design document v1 | TMS Tech Lead | **2025-09-05** | Action 1 (R2 greenlight) |
| 5 | R4 — Confirm G-07 on Sept 15–16 maintenance work order list | Infrastructure Manager | **2025-08-26** | None (independent) |
| 6 | R5 — Dashboard UAT scheduling with 6 shift supervisors | BI Team Lead | **2025-09-01** | Action 1 (R5 greenlight) |
| 7 | Schedule monthly benefits-realization review meeting (first meeting 4 weeks post-R1 go-live) | Program Manager (Joan A.) | **2025-08-26** | None |
| 8 | Begin Phase 2 scoping: Predictive Wagon ETA ML model (SET-RAG-LGS-004) — write draft business-question.md | Analytics Lead | **2025-09-19** | Action 1 (Phase 1 OK'd) |

---

## 10. Appendices

### Appendix A — Charts & Figures
> (Charts exported as high-resolution PNG/PDF and stored under `docs/reports/rpt-2025-019/figures/`. Reference below with captions.)

| Figure ID | Title | File | Page |
|---|---|---|---|
| Fig 1 | WTT Component Stacked Bar (Monthly, Jan 2024 – Jun 2025) | `fig1_wtt_components_stacked_bar.png` | — |
| Fig 2 | Port Dwell Distribution H1 2024 vs H1 2025 (density + box plot) | `fig2_port_dwell_distribution.png` | — |
| Fig 3 | Locomotive Utilization by Corridor (box plot, H1 2025) | `fig3_loco_utilization_by_corridor.png` | — |
| Fig 4 | WTT ANOVA — Variance Decomposition Bar Chart | `fig4_wtt_variance_decomposition.png` | — |
| Fig 5 | Natural Experiment: Sequencing vs Non-Sequencing Port Dwell (violin plot) | `fig5_sequencing_violin.png` | — |
| Fig 6 | R3 Queuing Model: Port dwell vs crane count (M/M/c output) | `fig6_crane_count_sensitivity.png` | — |

### Appendix B — Scenario & Sensitivity Tables (Full Output)
- Table B1: Intervention benefit sensitivity (10% steps from −50% to +50%): `tables/table_b1_intervention_sensitivity.xlsx`
- Table B2: R3 queuing model full output (λ, μ, c = 3..8, Wq, Lq, ρ): `tables/table_b2_queuing_model_full.csv`
- Table B3: 3-year financial DCF model full schedule (by month): `tables/table_b3_dcf_monthly_schedule.xlsx`

### Appendix C — Code References
| Component | File Path in Repo | Commit Tag |
|---|---|---|
| Core analysis CTE: `fact_wagon_cycle` | `models/marts/logistics/fact_wagon_cycle.sql` | `v1.0.0-rpt-2025-019` SHA: a73f9c2 |
| WTT variance decomposition | `notebooks/20250715_js_wtt_variance_decomposition.ipynb` | same |
| Natural experiment (sequencing) ANCOVA | `notebooks/20250722_js_sequencing_natural_experiment.ipynb` | same |
| Intervention ROI simulation | `notebooks/20250801_js_intervention_roi_simulation.ipynb` | same |
| Queuing model (R3 cranes) | `notebooks/20250803_js_crane_queuing_mmc.py` | same |
| Sensitivity tests S1–S3 | `notebooks/20250810_js_sensitivity_analysis.ipynb` | same |

### Appendix D — Stakeholder Sign-Off Sheet
*For physical sign-off if required by governance. Digital approvals via ADO work item tracking are acceptable and preferred per paperless policy.*

| Role | Name | Signature | Date | Comment |
|---|---|---|---|---|
| Business Owner (Supply Chain Director) | | | | |
| Rail Operations Manager | | | | |
| Port Operations Manager | | | | |
| Finance Controller | | | | |
| Analytics Engineering Lead (Author) | | | | |

### Appendix E — Glossary
All terms defined per the master `CONTEXT.md §3 (Domain Terminology)`. No report-specific glossary.

---

*End of Report RPT-2025-019.*
*Questions or corrections: Open an issue in the analytics repo tagged `report-correction`, referencing this report ID.*
