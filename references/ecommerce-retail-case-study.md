# Ecommerce Retail Case Study (Worked Example)

> **Status:** Optional reference — illustrative only.  
> **Do not** treat this as a domain template.  
> Load this file only when you need a concrete example of how a well-structured analytics + BI engagement looks end-to-end.  
> For transport, healthcare, finance, SaaS, manufacturing, or any other domain: re-derive personas, decisions, grain, and KPIs from the current brief via `grill` + `business-analysis`. Never copy retail metrics.

**Source inspiration**
- Pipeline & models: [musatouray/ecommerce-retail-pipeline](https://github.com/musatouray/ecommerce-retail-pipeline)
- Live dashboard: [Power BI report](https://app.powerbi.com/view?r=eyJrIjoiMWYwMTA1NjMtMmZiYy00YmYzLTgxN2UtMjI3MjFhMzY0MGQ4IiwidCI6ImU3ZmRiMmEyLTUzODAtNDBmMC04MmQ4LWEzYjU0YzFmODE3ZiJ9)

---

## 1. Context & objective of this case study

This document shows **how a production-grade retail analytics platform was thought**, not what every project must copy.

It answers:
- Which decisions does the dashboard actually support?
- Who uses it, with how much time, and what action follows?
- What is the explicit grain of each fact?
- How is information hierarchy organized (Context → KPI → Diagnosis → Detail → Action)?
- What patterns transfer to any other domain?

---

## 2. Personas & primary decisions

| Persona | Typical session | Primary decision(s) |
|---------|-----------------|---------------------|
| **Head of CRM / Retention** | 5–10 min, weekly | Which customer segments to prioritize for retention campaigns? |
| **Marketing / Growth lead** | 10–15 min, weekly | Which acquisition cohorts produce sticky, high-value customers? |
| **Product / Merchandising** | 10 min, ad-hoc | Which products co-purchase? What bundles or recommendations to push? |
| **Executive (C-level / board)** | 60–90 seconds glance | Are we retaining value? Is CLV healthy? Any segment at risk? |

**One primary decision per major surface** (or tightly related cluster). Multiple unrelated decisions → separate dashboards or clearly separated entry points.

---

## 3. Grain (declared before any SQL)

| Entity | Grain (plain language) |
|--------|------------------------|
| Orders | One row per **order** |
| Order items | One row per **order line** (product × order) |
| Payments | One row per **payment attempt / installment** |
| RFM segments | One row per **customer × snapshot month** |
| CLV | One row per **customer** (12-month projection) |
| Cohort retention | One row per **acquisition cohort month × observation month** |
| Market basket | One row per **product pair** (co-occurrence) |

Grain is always stated as: *one [entity] per [unit of time / context]*, using nouns that exist in the business systems.

---

## 4. Core analytics models (illustration only)

### Customer intelligence
- **fct_rfm_segments** — Recency, Frequency, Monetary scores + segment labels (Champions, Loyal, At-Risk, Lost…)
- **fct_clv_customer** — 12-month projected CLV, purchase probability, value tier
- **fct_cohort_retention** — GRR / NRR by acquisition month

### Core commerce
- **fct_orders**, **fct_order_items**, **fct_order_payments**
- **fct_market_basket** — pair frequency, support, confidence

### Dimensions
- **dim_customers**, **dim_products**, **dim_sellers**, **dim_dates**

These names and metrics are **retail-specific illustrations**. On a transport project you would have on-time %, delay minutes, vehicle utilization, route fill rate, etc. The *structure* (fact grain + dim + clear KPI ownership) is what transfers.

---

## 5. Dashboard information hierarchy (worked example)

Applied consistently across pages:

1. **Context bar** (top)  
   Active filters, last refresh / freshness, page name, any data warning.

2. **Layer 1 — KPI strip** (3–7 cards)  
   Value + delta vs baseline/target + sparkline + status (ok / warn / critical).

3. **Layer 2 — Diagnosis**  
   Why did the KPI move? Time trend + segment breakdown + driver / Pareto.

4. **Layer 3 — Detail**  
   Drill tables, low-level charts, root-cause investigation. Progressive disclosure by default.

5. **Layer 4 — Action**  
   Explicit next step: export list of at-risk customers, link to campaign tool, owner contact, related dashboard.

### Example page mapping (retail illustration)

| Page / zone | Decision it serves | Typical KPI strip | Diagnosis layer |
|-------------|--------------------|-------------------|-----------------|
| Customer overview | Prioritize retention effort | # customers, revenue, avg CLV, % at-risk | RFM distribution, segment trend |
| Cohort retention | Judge acquisition quality | GRR, NRR, retention % M1/M3/M6 | Cohort heatmap, channel breakdown |
| CLV & value tiers | Allocate acquisition spend | Predicted 12-mo CLV, high-value share | CLV by segment / channel |
| Market basket | Drive bundles & recommendations | Top pair support/confidence | Co-purchase matrix / network |
| Orders / operations | Monitor revenue & delivery health | Revenue, AOV, on-time delivery % | Trend + seller / category breakdown |

Pages are named by **user task**, not by table name.

---

## 6. Architecture snapshot (for context only)

```
Synthetic / source data
        → S3 (landing)
        → Snowflake RAW (Bronze)
        → dbt models (Silver → Gold / marts)
        → Power BI semantic model + dashboards
```

Orchestration: Airflow. CI/CD: GitHub Actions. Environment isolation: DEV / PROD. Observability: Slack alerts on pipeline failure.

The agent does not need to reproduce this stack. The useful pattern is: **clear medallion / staging → marts with explicit grain → semantic layer → decision-oriented dashboard**.

---

## 7. Principes généralisables (what the agent must retain)

These principles apply to **any** domain (transport, healthcare, finance, SaaS, manufacturing, public sector…):

1. **Decision first**  
   One primary decision (or tightly related cluster) per dashboard surface. If two independent decisions exist, split.

2. **Personas + session flow**  
   Who opens it, on what device, with how much time, what action they take after.

3. **Grain before code**  
   Declare grain in business language before writing SQL / DAX / Python. Validate against sample rows to catch fan-out.

4. **KPI discipline**  
   One primary KPI that drives the decision. Secondary KPIs only diagnose *why*. Full definition blocks (business + technical + unit + direction + owner). Baseline, target, yellow/red thresholds.

5. **Information hierarchy**  
   Context → KPI strip → Diagnosis → Detail → Action. Never start with a wall of charts.

6. **Progressive disclosure**  
   Default view answers the decision in ~60 seconds. Detail and methodology live behind drill / tabs / info icons.

7. **Action layer is mandatory**  
   Every surface should make the next operational step obvious (export list, open ticket, contact owner, open related report).

8. **Name by task, not by data**  
   "Daily Operations", "At-Risk Customers", "On-Time Performance" — not "FactOrders" or "stg_shipments".

9. **Error / empty / stale states**  
   Never leave blank charts. Show "no data for selection", freshness banner, or error with contact.

10. **Domain metrics are local; structure is global**  
    RFM / CLV / market basket are retail illustrations. On a transport project you invent the equivalent (on-time %, delay drivers, vehicle utilization). Re-run `grill` + `business-analysis` every time.

---

## 8. How the agent should use this file

- **When to load:** only if you need a concrete illustration of good dashboard hierarchy, grain declaration, or persona/decision mapping.
- **When not to load:** default path for any new engagement. Prefer `grill` → `business-analysis` → domain-specific modeling.
- **Never:** copy RFM, CLV, or market-basket logic into a non-retail project without explicit stakeholder request and re-validation of the decision.

---

## 9. Related workflows & references

| Need | Load |
|------|------|
| Clarify ambiguous request | `workflows/grill.md` |
| Turn decision into KPI / grain / dimensions | `workflows/business-analysis.md` |
| Design dashboard layout & hierarchy | `workflows/dashboard-ux.md` |
| Choose individual charts | `workflows/visualization.md` |
| Dimensional modeling | `workflows/data-modeling.md` |
| DAX / semantic model | `workflows/dax-analysis.md`, `workflows/tmdl-analysis.md` |

---

*End of worked example. Extract principles; leave the retail metrics behind.*
