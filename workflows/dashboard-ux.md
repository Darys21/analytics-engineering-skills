# Workflow: dashboard-ux

## Purpose
Design a dashboard as a decision interface, not as a collection of charts. Optimize for the user's decision, their information hierarchy, and their workflow.

## When to use
- User asks to "build a dashboard," "create a Power BI report," or produce any multi-chart interactive analytical interface intended for repeated use.
- Before `visualization` (decide layout and hierarchy before individual chart design).

## Inputs
- Decision / user problem the dashboard is built to support (if unclear, use `grill` + `business-analysis` first).
- Target persona(s): role, data literacy level, device, frequency of use, time they have per session.
- KPIs, dimensions, grain, and comparisons required (see `business-analysis` output).
- Refresh cadence and data-freshness expectations.
- Export / print requirements; regulatory or security constraints.
- Brand / corporate style constraints if any.

## Preconditions
- Business analysis has produced: personas, decisions, KPIs, grain, dimensions, comparisons, alerts, and actions.
- Semantic model (or data pipeline) exists or is designed in parallel (`data-modeling`, `tmdl-analysis`, `dax-analysis`).

## Procedure
1. **Confirm the dashboard's core decision.** One dashboard → one primary decision; if two primary decisions, two separate dashboards or clearly separated tabs with independent entry points.
2. **Persona and session flow.**
   - Who opens this dashboard? On what device? With how much time?
   - Typical session: "check morning KPIs, drill into outlier, export for meeting" — write it as a story.
3. **Information hierarchy (required, top to bottom, left to right).**
   - **Context bar** (top): filters active, refresh timestamp / freshness, data warnings, page name, last-updated.
   - **Layer 1 — KPI strip:** 3–7 most important KPIs. Each KPI = value + delta vs. baseline/target + sparkline/trend + status (ok/warn/critical if applicable).
   - **Layer 2 — Diagnosis:** charts that answer "why is the KPI up/down." Typically time-trend + segment breakdown + driver / Pareto.
   - **Layer 3 — Detail:** drill-through tab, table, or low-level chart for root cause investigation. Show by default only if typical session needs it; otherwise progressive disclosure (expand / tooltip / drill page).
   - **Layer 4 — Action:** explicit next step — links to source, ticketing system, related dashboards, owner contacts, export buttons, or notes/commentary.
4. **Navigation and layout.**
   - Max 5–7 pages/tabs; name them by user task, not by table name. Example: "Daily Operations" not "FactOps".
   - Default filter state: last full period, default region/segment = "all". Persistent filters on user devices if the BI tool supports it.
   - Responsive considerations: mobile = KPI strip + trend; desktop = full hierarchy. Design both.
5. **Filtering, interactions, tooltips.**
   - Global filters at top; page-level filters only where they logically override global. Avoid per-chart filters unless required.
   - Cross-filtering / cross-highlighting on by default only when it helps diagnosis; turn off for unrelated charts.
   - Drill-down paths designed per chart; each drill changes grain predictably.
   - Tooltips: metric definition, grain, value, comparison, and "what to do next" if status-based. Keep under ~8 lines.
6. **Progressive disclosure.**
   - Start with KPIs + top diagnosis. Move tables, raw data, and methodological notes to separate tabs or expandable "Details" panels.
   - Metric dictionary, sources, assumptions, refresh schedule: accessible via help icon / info tab, not crowding the main view.
7. **Accessibility.**
   - Tab order, keyboard-navigable.
   - Color never the sole encoder; 4.5:1 contrast; alt text on every KPI and chart.
   - No flashing indicators; statuses use icon + color + label.
8. **Performance expectations.**
   - KPI strip loads in < 2 s (target) on typical data volume.
   - Single visual interaction (filter, drill) < 3 s.
   - Long-running queries show loading state and (if feasible) cancel-ability.
9. **Error, empty, and stale-data states.**
   - Dashboard displays: error message with contact and retry, "no data for this selection" (never blank charts), "data stale as of X — investigating" banner if freshness exceeds SLA.
10. **Export and print requirements.**
    - PDF / PPTX / PNG export layout defined and tested (title page, page breaks, fixed filters applied at export time).
    - CSV / Excel export of underlying detail preserves grain and includes column descriptions where supported.

## Decision points
- If KPI count > 7 → split dashboards or promote only the primary KPIs.
- If a chart answers "what" but not "so what" → move it to Detail or drop it.
- If interaction model is ambiguous (what filters apply where) → simplify. Better fewer interactions than surprising ones.
- If refresh cadence is real-time vs. daily → architecture choices (DirectQuery vs. Import) are different; route to `power-bi.md` / TMDL / semantic design.

## Validation
- Persona test: can the intended user, in a simulated 60-second session, answer the primary decision question? (Record which KPIs/charts they used.)
- Representative filters applied, no page returns blank silently.
- Export produces a usable file for the stated scenario.
- Error states tested (e.g., data source down, empty filter selection).
- Performance within agreed targets on representative dataset.

## Expected outputs
- Dashboard design brief: personas, primary decision, session flow.
- Wireframe (or working prototype) per page with layout annotated.
- Interaction spec: filters, cross-filtering, drill-downs, tooltips, info pop-ups.
- Accessibility checklist result.
- Performance targets and measured values on representative data.
- Metric dictionary tab or link: definitions, sources, grain, owners, refresh cadence.

## Common failure modes
- 20+ charts because "we have the data." Dashboard unusable.
- Named after data sources, not user tasks. Nobody can find it.
- No context bar: users never know how fresh the data is or what filters are active.
- "Boss asked for one more chart" feature creep.
- No error states: blank dashboard when source fails, users think "all zeros".
- Mobile ignored. Half the user base opens it on a phone and the KPI strip is off-screen.

## References to load
- `references/dashboard-ux.md` — detailed hierarchy, interaction patterns, and anti-patterns.
- `references/visualization.md` — for individual chart design.
- `references/power-bi.md` + `workflows/dax-analysis.md` + `workflows/tmdl-analysis.md` if Power BI semantic.
- `references/performance.md` — dashboard response time, DAX tuning.
- `references/security.md` — row-level security, PII masking.
- **Optional example:** `references/ecommerce-retail-case-study.md` — concrete worked example of personas, grain, KPI strip, and Context → KPI → Diagnosis → Detail → Action hierarchy. Load only if you need an illustration; do **not** force retail metrics onto other domains.

## Completion criteria
- Primary decision defined; one dashboard serves that decision.
- Information hierarchy (Context → KPI → Diagnosis → Detail → Action) present.
- Filtering, navigation, interactions, tooltips designed and documented.
- Accessibility, performance, freshness, and error states addressed.
- Export / print and mobile layouts defined.
- Metric dictionary and info layer accessible.
- Persona test: 60-second scenario succeeds.
