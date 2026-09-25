# Workflow: BUSINESS ANALYSIS — From Dashboard Request to Decision Problem

## Purpose

Translate a signed-off GRILL output into a precisely scoped decision problem with defined KPIs, dimensions, grain, baselines, targets, and actionability thresholds. The output of this workflow is an unambiguous specification that downstream teams (data discovery, modeling, engineering, visualization) can execute without re-interpreting stakeholder intent. This is the bridge between ambiguity resolution and technical work.

## When to use

- Immediately after `grill.md` has produced a signed-off synthesis.
- When stakeholder intent is clear but the analytical specification (what exactly to calculate, how to slice it, how to compare it) is not.
- When building or revising a dashboard, recurring report, or ad-hoc analysis that will drive a named decision.
- When scoping a data model or semantic layer addition that will support a specific decision surface.

## Inputs

- Signed-off GRILL document (`GRILL - <Engagement Name>.md`) with all 11 categories complete.
- Existing reports, Excel files, or dashboards that currently inform (or fail to inform) the decision.
- Any domain documentation: glossaries, KPI definitions, org charts, process maps.
- Access to a subject-matter expert (SME) who owns the business process being measured.

## Preconditions

- `grill.md` completion criteria are satisfied; GRILL synthesis is confirmed in writing.
- A SME has been identified and is available for at least one 60-minute working session.
- The analyst has read access to at least one sample of the source data referenced in the GRILL Data section (for sanity-checking definitions against actual columns).

## Procedure

1. **Restate the decision from GRILL.** Copy the Decision section verbatim. Confirm with the SME that the decision, its options, its frequency, and its deadline are still correct. If anything has changed, loop back to `grill.md` step 13 and re-sign-off before proceeding.
2. **Map the stakeholder personas.** For each persona listed in the GRILL Who section, write a one-paragraph persona card that includes: role, typical decision cadence (e.g., weekly on Monday morning), information they receive today, pain points with current information, and the one action they must take after consuming the output.
3. **Define the KPI candidates.** Brainstorm every metric that could inform the decision. Use the SME and existing reports as sources. Do not filter yet; capture even tentative or overlapping candidates. For each candidate, record a one-line working definition.
4. **Select the primary KPI.** From the candidates, pick exactly one metric whose movement directly changes the decision. Label it `Primary KPI`. If the stakeholder insists on multiple primary KPIs, ask: "If KPI A goes up and KPI B goes down, which one determines the decision?" Resolve the tie; multiple primary KPIs indicate an unresolved decision split and require re-grilling.
5. **Select secondary KPIs.** Pick 2–4 secondary KPIs that explain *why* the primary KPI moves, or that act as guardrails (e.g., "if primary is cost-per-ton, secondary might be yield, throughput, and safety incidents"). Secondary KPIs must not drive the decision; they only diagnose changes in the primary.
6. **Write formal KPI definitions.** For every selected KPI (primary + secondary), produce a definition block containing:
   - **KPI Name**: short, verb-free noun phrase (e.g., "Ore Haul Cost per Net Ton-Kilometer" not "Calculate Haul Cost")
   - **Business Definition**: plain-language explanation that a non-technical auditor would understand
   - **Technical Definition**: pseudocode or exact formula referencing source columns (e.g., `SUM(freight_invoice.total_amount) / SUM(shipment.net_weight_kg * shipment.route_distance_km / 1000)`)
   - **Unit of Measure**: tonnes, USD, %, days, tickets-per-shift — explicit and unambiguous
   - **Positive Direction**: "higher is better" / "lower is better" / "target band X–Y"
   - **Owner**: named business owner who approves definitional changes
7. **Enumerate analysis dimensions.** List every attribute by which the KPI must be sliced to support the decision. For each dimension, record:
   - **Dimension Name**: e.g., "Site", "Shift", "Asset Type", "Customer Segment"
   - **Values**: expected set of members (list them or state "open-ended, maintained in dim table X")
   - **Decision Relevance**: which option it helps choose (e.g., "Site identifies which locations are underperforming so we can reallocate maintenance budget")
   - **Cardinality**: approximate number of members (<10, 10–100, 100–10,000, >10,000) — this informs downstream visualization choices
8. **Confirm the grain.** Restate the GRILL grain. Validate it against the KPIs and dimensions: can every KPI be computed at that grain? Can every dimension be applied at that grain without fan-out or double-counting? If not, redefine the grain and re-confirm with GRILL step 7.
9. **Define the timeframe.** Specify:
   - **Reporting Period**: the cadence at which the KPI is produced (daily close, week-ending Sunday, month-end, quarter-end)
   - **History Length**: how many historical periods must be available at launch (e.g., "24 completed months + current partial month")
   - **Comparands**: what the current period is compared against (prior period, same period last year, budget/plan/forecast, a benchmark, or a statistical baseline)
   - **As-of Time**: the moment at which the report represents truth (e.g., "as of 06:00 daily" or "as of month-end close + 2 business days")
10. **Establish a baseline.** For the primary KPI, compute (or ask the SME for) the baseline value over a representative recent period of stable operations. Record the period and the value. If historical data is unavailable, label the baseline "TBD at data discovery" and flag it as a risk.
11. **Define targets and thresholds.** For every KPI, record:
    - **Target**: the value the business is aiming for in the current plan cycle (with owner and date)
    - **Alert Threshold (Yellow)**: the value at which the stakeholder should be notified to investigate (e.g., 5% deviation from target)
    - **Action Threshold (Red)**: the value at which the stakeholder must trigger a decision or intervention (e.g., 10% deviation)
    - If thresholds do not exist, facilitate the SME to define them; do not proceed with undefined thresholds or the dashboard cannot signal urgency.
12. **List constraints and filters (global and persona-based).**
    - **Global Constraints**: what rows are always excluded? (e.g., "test transactions", "voided invoices", "historical sites closed before 2020")
    - **Persona-Based Filters**: what default filters apply to each persona's view? (e.g., "Site Manager sees only their site by default; Regional Director sees all sites in their region but can drill")
    - For every constraint, record the business justification and confirm with the owner.
13. **Root cause levers map.** Working backwards from the primary KPI, draw a driver tree (3 levels minimum) of the operational levers that influence it. For example: `Haul Cost/Tonkm ← (Fuel Cost + Maintenance Cost + Labor Cost) / (Payload * Distance)`. Each leaf node should correspond to an actionable operational lever (e.g., "fuel price", "truck idle time", "payload fill rate", "route selection"). This map drives the secondary KPI selection and the dashboard's diagnosis layer.
14. **Assess actionability.** For each leaf in the driver tree, ask the SME: "If this lever moves by X%, can someone in the organization directly change it, within the decision timeframe, to bring the primary KPI back to target?" If the answer is "no", the lever is a non-actionable factor and should be marked as diagnostic only, not as a recommendation driver.
15. **Synthesize the business specification document.** Compile all above into a single document. Include: decision restatement, personas, KPIs (with full definition blocks), dimensions, grain, timeframe, baseline, targets/thresholds, constraints, driver tree, and actionability labels.
16. **Sign off with decision-maker and SME.** Walk through the specification document. Resolve every open item. Do not proceed to downstream work until both the decision-maker and the SME have confirmed in writing.

## Decision points

- **Step 4 (Primary KPI).** If after three attempts the stakeholder cannot select a single primary KPI (because "all are equally important"), split the engagement into two separate decision problems with separate GRILLs. Do not pack two independent decisions into one dashboard.
- **Step 8 (Grain).** If KPI computation produces fan-out at the proposed grain (e.g., joining a shipment header table to a line table multiplies freight cost per line), choose between: (a) refining grain to the finer level and using semi-additive measures for header-level amounts, or (b) pre-aggregating header-level metrics. Record the choice and its trade-off.
- **Step 11 (Thresholds).** If the SME cannot define thresholds despite prompting, present three computed percentiles (P25, P50, P75) from baseline data and ask the SME to pick. Document the chosen thresholds as "provisional, pending 60 days of operational usage."
- **Step 14 (Actionability).** If fewer than half of the driver-tree leaf nodes are actionable, the decision problem may be outside the control of the business; raise this as a risk and confirm the stakeholder still wants to proceed with a largely diagnostic deliverable.

## Validation

- One and only one `Primary KPI` is named, with a full definition block.
- Every secondary KPI traces to a node in the driver tree.
- Every dimension has an explicit decision relevance statement.
- Grain is validated against the KPI formulas — no fan-out or double-counting identified.
- Baseline, target, yellow, and red values exist for the primary KPI with attached time periods.
- Every global constraint has a business justification.
- The driver tree has at least 3 levels and every leaf has an actionability label (Actionable / Diagnostic).
- Decision-maker and SME written sign-off is on file.

## Expected outputs

- `BUSINESS-SPEC - <Engagement Name>.md` (or `.docx`) containing sections 1–15 above, typically 1,500–4,000 words.
- A driver tree diagram (embedded or linked) in PNG, Mermaid, or draw.io format with 3+ levels.
- A KPI definition table exportable as CSV for downstream ingestion into a data catalog or semantic layer.
- A signed-off entry in the work tracking system linking to the specification.

## Common failure modes

1. **Verbose KPI names that hide duplicates.** "Weekly average cost of maintenance per asset type including contracted services" versus "Maintenance cost per asset-week" may be the same KPI written two ways. Remedy: normalize names to a `[Metric] per [Grain]` pattern and cross-check formulas before selection.
2. **Secondary KPIs compete with primary KPIs for decision authority.** Remedy: explicitly label secondary KPIs "diagnostic only" and in the persona cards write that only the primary KPI triggers a decision.
3. **Dimensions are added without decision relevance.** Stakeholders ask for "Region, product, customer, month, sales rep, channel" because "we might need it." Remedy: in step 7, reject any dimension that cannot produce a concrete decision relevance sentence. Park low-relevance dimensions in an "out of scope unless justified" list.
4. **Grain mismatch discovered mid-modeling.** Remedy: perform a manual sample calculation using 10 rows of real data in step 8, before signing off, to catch fan-out early.
5. **Targets and thresholds are missing.** Dashboard renders as a chart with no "good vs bad" signal, making it useless for decision-making. Remedy: block sign-off on step 16 until thresholds are provided.
6. **Driver tree is aspirational, not causal.** "Improve customer experience" is not a lever. Remedy: prune any leaf node that the SME cannot tie to a specific operational action taken by a named role within the decision timeframe.
7. **Sign-off by proxy.** The wrong person approves the spec and the decision-maker rejects the final dashboard. Remedy: require the exact decision-maker named in GRILL step 5 to be one of the two signatories.

## References to load

- `references/kpi-definition-template.md` — fillable KPI definition block template with 12 examples
- `references/driver-tree-patterns.md` — industry-specific driver trees (mining haulage, processing throughput, warehousing, finance P&L, HR attrition) with editable Mermaid sources
- `references/threshold-setting-methods.md` — 5 methods (policy, statistical, benchmark, prior-period, expert-elicitation) for setting yellow/red thresholds when none exist
- `references/grain-fanout-checklist.md` — step-by-step fan-out detection using sample row calculations
- `references/business-spec-review-checklist.md` — 20-item pass/fail checklist for validating the BUSINESS-SPEC document before sign-off
- `references/decision-relevance-probes.md` — 15 follow-up questions to determine whether a dimension actually influences a choice
- **Optional example:** `references/ecommerce-retail-case-study.md` — concrete illustration of personas, primary decisions, grain declaration, and KPI hierarchy. Load only if helpful; re-derive everything for the current domain via GRILL + this workflow. Do **not** reuse retail metrics on non-retail projects.

## Completion criteria

- `BUSINESS-SPEC - <Engagement Name>.md` exists and contains every required section with non-empty, validated content.
- A driver tree with 3+ levels exists; leaves are individually labeled Actionable or Diagnostic.
- Primary KPI definition block is complete (Business + Technical + Unit + Direction + Owner).
- Baseline value, target, yellow threshold, and red threshold are recorded for the primary KPI with time periods.
- Every listed dimension has a decision relevance sentence.
- Decision-maker (from GRILL step 5) and SME have both provided written confirmation of the specification.
- The work item is transitioned to "Data Discovery."
