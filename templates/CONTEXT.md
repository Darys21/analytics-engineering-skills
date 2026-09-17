# CONTEXT: [Project / Initiative Name]

> **Template Usage**: Replace bracketed placeholders `[...]` with project-specific content. This document serves as the single source of truth for analytics engineering work. Update whenever context changes.

---

## 1. Business Context

**Organization / Division:** [e.g., SETRAG — Société d'Exploitation du Transgabonais / Logistics Division]
**Initiative Sponsor:** [Name, Title]
**Business Problem / Opportunity:**
[2–4 paragraph narrative describing the business situation. Example: "SETRAG's manganese export volumes declined 8% YoY in H1 2025 despite stable production. Port congestion and rail wagon turnaround time variability are suspected root causes. The business requires an end-to-end supply chain visibility analytics solution to identify bottlenecks and optimize asset utilization."]

**Strategic Alignment:**
- Objective 1: [e.g., Improve on-time delivery performance to ≥95% for export contracts]
- Objective 2: [e.g., Reduce rail logistics cost per tonne by 10% within 12 months]
- Objective 3: [e.g., Achieve ISO 28000 supply chain security compliance visibility]

**Time Horizon / Urgency:**
- **Phase 1 (MVP):** [e.g., Weeks 1–8 — Core KPIs and bottleneck dashboard]
- **Phase 2 (Scale):** [e.g., Weeks 9–20 — Predictive ETAs and optimization models]
- **Phase 3 (Sustain):** [e.g., Ongoing — Continuous monitoring and model retraining]

---

## 2. Stakeholders

| Role / Group | Name(s) | RACI | Expectations / Needs | Contact |
|---|---|---|---|---|
| Executive Sponsor | [e.g., Director of Logistics] | **A** | Monthly exec briefings, risk dashboards, ROI tracking | [email / Teams] |
| Business Owner | [e.g., Supply Chain Manager] | **R** | Daily operational dashboards, drill-down analysis, decision support | [email / Teams] |
| Operations Managers | [e.g., Port Ops, Rail Ops, Warehouse Leads] | **C** | Shift-level KPIs, alerting, real-time views | [email / Teams] |
| Data Steward(s) | [e.g., ERP Data Owner, IoT Platform Owner] | **C** | Data quality issue resolution, schema change approvals | [email / Teams] |
| Analytics / BI Team | [e.g., Data Engineers, Analysts, Data Scientists] | **R** | Model definitions, data access, documentation, training | [email / Teams] |
| IT / Platform | [e.g., Cloud Architect, Security] | **I** | Deployment, access provisioning, compliance sign-off | [email / Teams] |
| End Consumers | [e.g., Planners, Dispatchers, Finance Controllers] | **I** | Self-service reports, export capability, user training | [email / Teams] |

---

## 3. Domain Terminology

| Term | Definition / Business Meaning | Synonyms / Abbrev. |
|---|---|---|
| **Wagon Turnaround Time (WTT)** | Elapsed time from wagon departure from port to return empty to port. Measured in days. | Tour de wagon, cycle time |
| **Dwell Time** | Time a wagon spends idle at a location (loading / unloading / staging). Sub-component of WTT. | Temps d'attente |
| **OTIF** | On-Time In-Full — % of shipments delivered by agreed date with agreed quantity. | Delivery performance |
| **TEU** | Twenty-Foot Equivalent Unit — standard container volume measure. | — |
| **GT** | Gross Tonne — weight including wagon tare and cargo. | — |
| **NT** | Net Tonne — cargo weight only (GT minus wagon tare). | — |
| **Consist** | A group of wagons coupled together and hauled by a single locomotive. | Rame / train composition |
| **ETD / ETA** | Estimated Time of Departure / Estimated Time of Arrival. | — |
| **UOM** | Unit of Measure (tonnes, m³, pieces, etc.). | — |
| **SLA** | Service Level Agreement — contractual performance target between parties. | — |
| **CDC / CDE** | Commande / Bon de livraison — order / delivery note identifiers in ERP. | PO / Delivery Note |
| **SKU** | Stock Keeping Unit — unique product identifier at the storage/location level. | — |
| **Mvt** | Mouvement / Movement transaction in the TMS (Transport Management System). | — |
| **IoT Gate** | Physical RFID / GPS checkpoint that records wagon passage events. | Portique |

---

## 4. KPI Definitions

> Each KPI must have: Name, Business Definition, **Formula**, Data Source(s), Grain, Owner, Target.

### 4.1 Operational KPIs

| # | KPI Name | Business Definition | Formula | Data Source(s) | Grain | Owner | Target |
|---|---|---|---|---|---|---|---|
| KPI-01 | **Wagon Turnaround Time (avg)** | Average days from wagon port departure to next port arrival (empty return). | `AVG(DATEDIFF(day, wagon_departure_port_ts, wagon_arrival_port_return_ts))` filtered to completed cycles. | TMS (`mvt_wagon_cycle`), IoT Gates (`gate_events`) | Per wagon, per cycle | Rail Ops Manager | ≤ 6.5 days |
| KPI-02 | **Dwell Time at Port (avg)** | Average hours a loaded wagon waits at port before unloading begins. | `AVG(DATEDIFF(hour, wagon_arrival_port_ts, unload_start_ts))` | IoT Gates, Port Ops System (`port_activities`) | Per wagon, per visit | Port Ops Manager | ≤ 12 hours |
| KPI-03 | **On-Time Departure (%)** | % of trains departing origin within ±30 min of scheduled time. | `COUNT(depart_on_time_flag = 1) / COUNT(total_trains) * 100` | Train Schedule (`train_schedule`), TMS Actuals | Per train, per origin / destination pair | Dispatch Manager | ≥ 90% |
| KPI-04 | **OTIF Delivery (%)** | % of shipments delivered by contract date and within ±2% of ordered quantity. | `COUNT(otif_flag = 1) / COUNT(total_shipments) * 100` where `otif_flag = 1` WHEN `delivery_date ≤ contract_due_date AND ABS(delivered_qty - ordered_qty) / ordered_qty ≤ 0.02` | ERP (`cde_lignes`), TMS (`shipment_receipts`) | Per shipment (CDC line) | Supply Chain Manager | ≥ 92% |
| KPI-05 | **Locomotive Utilization (%)** | % of total available hours a locomotive spends hauling (vs idle / maintenance). | `SUM(hauling_duration_hours) / (fleet_count * 24 * period_days) * 100` | Fleet Management (`locomotive_status_log`) | Fleet-wide, daily / weekly | Fleet Manager | ≥ 72% |
| KPI-06 | **Empty Running Ratio (%)** | % of total wagon-km traveled while empty. | `SUM(wagon_km_empty) / SUM(wagon_km_total) * 100` | IoT / GPS (`wagon_gps_trips`) | Fleet-wide, weekly | Planning Manager | ≤ 22% |

### 4.2 Financial / Commercial KPIs

| # | KPI Name | Business Definition | Formula | Data Source(s) | Grain | Owner | Target |
|---|---|---|---|---|---|---|---|
| KPI-07 | **Cost per Net Tonne-Km (€)** | Average logistics cost to move 1 tonne of cargo 1 km by rail. | `SUM(total_logistics_cost_eur) / SUM(net_tonne * distance_km)` | Finance (`cost_center_allocations`), TMS Distances | Monthly, per corridor | Controller | ≤ €0.045 / NT-km |
| KPI-08 | **Revenue per Wagon (€)** | Average revenue generated per loaded wagon movement. | `SUM(invoice_amount_eur) / COUNT(distinct loaded_wagon_movements)` | ERP (`factures`), TMS Shipments | Monthly, per product / corridor | Commercial | Benchmark QoQ |
| KPI-09 | **Demurrage Cost (€)** | Penalty charges incurred for late wagon return or port congestion. | `SUM(demurrage_charge_eur)` | ERP (`factures_fournisseurs` tags: DEM, PEN) | Monthly, by cause | Supply Chain Manager | Minimize / < budget |

### 4.3 Quality / Reliability KPIs

| # | KPI Name | Business Definition | Formula | Data Source(s) | Grain | Owner | Target |
|---|---|---|---|---|---|---|---|
| KPI-10 | **Cargo Loss / Damage Rate (%)** | % of shipments with reported loss or damage > 0.1% of value. | `COUNT(claim_count > 0 AND claim_pct > 0.001) / COUNT(total_shipments) * 100` | Claims DB (`insurance_claims`), ERP | Per shipment line | Quality Manager | ≤ 0.5% |
| KPI-11 | **Data Completeness - IoT (%)** | % of expected wagon-cycle events that have corresponding gate readings. | `COUNT(has_gate_event = 1) / COUNT(expected_wagon_events) * 100` | IoT Gates vs TMS Expected Itinerary | Daily, per gate location | Data Steward | ≥ 98% |

---

## 5. Data Sources

| ID | System / Source Name | Owner / Custodian | Technology | Freshness / Latency | Grain / Granularity | Access Method | Key Entities / Tables | Quality Notes |
|---|---|---|---|---|---|---|---|---|
| SRC-01 | **ERP (Sage X3)** | Finance / IT ERP Team | On-prem RDBMS (Oracle) | Nightly batch (02:00 local) — T-1 | Transaction level: order line, invoice line, GL journal | OData API / Stored procedure CDC | `cde_entete`, `cde_lignes`, `fac_entete`, `fac_lignes`, `fiche_article`, `fiche_tiers` | Order status field `STA` has undocumented values; confirm with finance before filtering. |
| SRC-02 | **TMS (Transport Management)** | Logistics Systems Manager | Cloud SaaS (Oracle OTM) | Streaming CDC — ~5 min lag | Movement (mvt) per wagon per leg | REST API + Kafka topic `tms.mvt.v1` | `mvt_wagon`, `mvt_train`, `shipment`, `itinerary`, `driver` | Event ordering not guaranteed across Kafka partitions; use `event_ts + mvt_id` dedup logic. |
| SRC-03 | **IoT Gate Sensors** | Infrastructure / Rail Ops | Edge → Azure IoT Hub → ADX | Near-real-time (≤ 2 min) | Per-gate, per-wagon passage event | ADX query (`gate_events` table) / Event Hub capture | `gate_events`, `gate_metadata`, `wagon_rfid_map` | Gate G-07 (Moanda) has 4% missing reads due to signal blind spot (known issue). Use GPS fallback for that location. |
| SRC-04 | **Wagon GPS / Telematics** | Fleet Manager | Third-party SaaS API (Geotab) | Polling every 10 min → raw lands every 15 min | Per-wagon, per GPS ping (position, speed, heading) | REST API → JSON landing | `wagon_gps_raw`, `wagon_trips`, `locomotive_status` | GPS drift in forested corridors (±200 m); map-match to rail network before distance calc. |
| SRC-05 | **Port Operations System** | Port Ops Manager | On-prem MS SQL | Nightly batch + manual data entry corrections | Per vessel, per berth, per crane operation | Linked server → staging tables | `vessel_call`, `cargo_handling`, `berth_schedule`, `crane_activity_log` | Manual entries have up to 48 hr correction latency; do not report current-month final numbers before T+3. |
| SRC-06 | **Fleet Management (Mainten.)** | Fleet Maintenance Manager | CMMS (Maximo) | Nightly batch | Work order, asset status event | CSV drop → Blob storage / REST | `work_order`, `asset_status_history`, `parts_usage`, `maintenance_schedule` | Locomotive `asset_id` differs from TMS `locomotive_code`; use mapping table `ref_locomotive_map`. |
| SRC-07 | **Weather (External)** | Data Engineering (acquired) | Open-Meteo API + NOAA | Daily (forecast 7d), Historical hourly | Per weather station (3 within network) | API → curated dim table | `dim_weather_station`, `fact_weather_hourly` | Use only for correlation / feature engineering; not as a causal explanation without statistical test. |
| SRC-08 | **Finance Allocations (Cube)** | Controlling | SAP BPC / Excel cubes | Monthly close — T+5 business days | Cost center, GL account, period | Manual extract → sharepoint → blob | `cost_center_allocations_monthly`, `gl_budget_vs_actual` | Allocations are *approximations*; do not use for individual wagon-level costing (only fleet / corridor aggregates). |

---

## 6. Architecture

### 6.1 Logical Data Flow
```
[Source Systems (SRC-01..08)]
        │
        ▼
[Ingestion Layer]
  ├─ CDC / Event Hub (SRC-02, SRC-03)
  ├─ API Pollers (SRC-04, SRC-07)
  ├─ Batch Copy (SRC-01, SRC-05, SRC-06)
  └─ File Drops (SRC-08)
        │
        ▼
[Bronze / Raw Zone (ADLS Gen2 - Parquet)]
  Immutable, append-only, source-aligned schema
        │
        ▼
[Silver / Clean Zone (Delta Lake on ADLS)]
  Deduplicated, conformed, typed, SCD-2 dimensions
        │
        ▼
[Gold / Curated Zone (Delta Lake + Azure SQL DWH)]
  Star schemas, KPI-aggregated marts, feature stores
        │
        ▼
[Serving Layer]
  ├─ Power BI Datasets (Import / DirectQuery)
  ├─ Azure Analysis Services Tabular Model
  ├─ dbt models for transformation logic
  └─ Python/R model endpoints (AML)
        │
        ▼
[Consumers]
  ├─ Dashboards (Power BI Service — App Workspace)
  ├─ Self-service (Power BI Desktop, Excel)
  ├─ Alerts (Power BI + Teams webhooks)
  ├─ Data Science Sandbox (Databricks)
  └─ API / Extracts (for external partners, per contract)
```

### 6.2 Technology Stack Summary
| Layer | Tool / Service | Purpose |
|---|---|---|
| Ingestion | Azure Data Factory (ADF) + Event Hub | Orchestrated pipelines + streaming intake |
| Storage | ADLS Gen2 (Hierarchical Namespace) | 3-zone lake (Bronze/Silver/Gold) |
| Compute — Transform | Azure Databricks (Spark) + dbt Core on ADF | Batch ELT, complex joins, feature engineering |
| Compute — Realtime | Azure Data Explorer (ADX) | IoT time-series, hot-path analytics |
| Warehouse | Azure Synapse Dedicated SQL Pool (if needed) — *current: use Serverless + Delta* | Large-scale aggregations, concurrent BI |
| Semantic / BI | Power BI Premium (P1) + AAS (optional) | Dashboards, shared datasets, row-level security |
| ML / Advanced | Azure Machine Learning + MLflow | Predictive models, experimentation tracking |
| Orchestration | ADF + Airflow (managed via ADF) | Workflow scheduling, retry, SLA monitoring |
| Testing / Quality | dbt tests + Great Expectations + custom PySpark checks | Schema, uniqueness, nullness, business-rule assertions |
| Observability | Azure Monitor + Log Analytics + Prometheus/Grafana | Pipeline telemetry, alerts, dashboards |
| IaC / CI-CD | Terraform + Azure DevOps Pipelines | Reproducible infra, PR gate deployments |

### 6.3 Naming Conventions for Zones / Objects
- **Bronze tables:** `bronze_{source_id}_{entity_plural}`  e.g., `bronze_src02_mvt_wagon`
- **Silver tables:** `silver_{domain}_{entity}` e.g., `silver_rail_wagon_cycle`, `silver_hr_employee`
- **Gold dimensions:** `dim_{entity}` (SCD Type 2 unless stated) e.g., `dim_wagon`, `dim_date`, `dim_location`
- **Gold facts:** `fact_{business_process}_{grain}` e.g., `fact_wagon_movement_per_leg`, `fact_shipment_otif`
- **Views / Marts:** `vw_mart_{subject_area}` e.g., `vw_mart_logistics_wtt_dashboard`

---

## 7. Constraints

### 7.1 Technical Constraints
- **Latency SLA:** Near-real-time IoT data ≤ 5 min from gate-event to dashboard visible. Batch data available by 07:00 local for previous day.
- **Concurrency:** Power BI workspace must support 50 concurrent report consumers during peak (08:00–09:00) without degradation.
- **Storage retention:** Bronze = immutable 7 years (regulatory), Silver = 3 years, Gold = current + 2 prior years online (archive beyond that to cool tier).
- **Compute cost cap:** Databricks total monthly spend ≤ €6,000 (monitor via Cost Management alert at 80%).
- **Region:** All customer / operational data must reside in **Azure Region: West Europe (Amsterdam)**. No cross-region data movement allowed for PII-bearing fields.

### 7.2 Business / Operational Constraints
- **Month-end close freeze:** No Gold schema changes or backfills during T+0 to T+5 (business close window).
- **Trader-facing numbers:** Any export shipment revenue / volume numbers must match signed commercial invoices. Do not publish "preliminary" numbers without explicit watermark + Finance sign-off.
- **Union / Labor relations:** Individual driver / operator performance data may be shown only in aggregate (≥ 5 drivers per cohort) to comply with works council agreement.
- **Third-party data terms:** Weather (SRC-07) and GPS (SRC-04) data are licensed for internal analytics use only; cannot be shared externally or re-sold without procurement approval.

### 7.3 Regulatory / Compliance Constraints
- **GDPR:** Employee, driver, and customer contact data is PII. Mask or pseudonymize in Silver+ layers unless access is role-granted via RLS.
- **SOX / Financial reporting:** KPI-07, KPI-08, KPI-09 feed into financial reporting → require audit trail (change log) for underlying calculation logic.
- **Local labor law (Gabonese Code du Travail):** Shift-work analysis must respect minimum rest period rules; do not produce analysis that could be used to pressure individual workers.

---

## 8. Known Data Issues

| ID | Issue Description | Source / Object | Impact | Severity | Mitigation / Workaround | Owner | Status |
|---|---|---|---|---|---|---|---|
| DI-001 | **Gate G-07 (Moanda) 4% missing reads** | SRC-03 `gate_events` where `gate_id = 'G-07'` | KPI-01 (WTT) under-reports dwell time for ~4% of wagons. | **High** | Fallback to SRC-04 GPS geofence-entry timestamp for location G-07. Log in DQ dashboard. | Infrastructure Ops | In Progress (HW upgrade ETA Q4 2025) |
| DI-002 | **ERP order status `STA` undocumented values** | SRC-01 `cde_entete.STA` | Queries filtering by `STA='5'` (shipped) may miss edge statuses `'5A'`, `'5B'`. | **Medium** | Confirm full STA enumeration with ERP team; use `IN ('5','5A','5B')` for shipped orders pending full mapping. | ERP Data Steward | Open |
| DI-003 | **TMS event ordering non-deterministic (Kafka)** | SRC-02 `tms.mvt.v1` topic | Same `mvt_id` may appear with out-of-order `event_ts` across partitions. | **Medium** | Dedup by `mvt_id + event_ts` rank, take latest `__ingest_ts` when tied. Document in silver ETL. | Data Engineering | Fixed in v2 pipeline |
| DI-004 | **GPS drift in forested corridors** | SRC-04 `wagon_gps_raw` | Distance calculations overstate trip length by up to 3% for the Franceville–Moanda leg. | **Medium** | Apply rail-network map-matching algorithm in Silver layer; use `matched_distance_km` column. | Data Engineering | Pending (map-matching library eval) |
| DI-005 | **Manual Port Ops corrections up to T+48 hr** | SRC-05 `cargo_handling` | Same-day / T-1 port throughput numbers may change materially. | **High** | Add watermark to dashboard: "Current-month port figures are preliminary and subject to revision." Freeze month-end snapshot at T+3. | Port Ops + BI | Accepted / documented |
| DI-006 | **Locomotive ID mismatch TMS vs CMMS** | SRC-02 vs SRC-06 | KPI-05 (Locomotive utilization) has ~12% of fleet unmatched pre-2024. | **Medium** | Use `ref_locomotive_map` mapping table; treat pre-2024 unmatched as separate cohort and disclose in reports. | Fleet Data Steward | Open (historical mapping effort) |
| DI-007 | **Duplicate `fact_insurance_claims` entries** | SRC-10 (Claims DB) → Silver | KPI-10 loss rate may be overstated by ~0.3pp. | **Low** | Dedupe by `claim_number + shipment_id` in silver; add dbt uniqueness test. | Data Engineering | Fixed (monitoring) |

> **How to report new data issues:** Create a ticket in [ADO Project / Analytics Board] tagged `area-data-quality` and link to a row appended to this table.

---

## 9. Conventions

### 9.1 Coding & Naming
- **Language:** English for code, comments (for portability), object names, and column names. Business-facing labels *may* be bilingual (FR-EN) if requested by stakeholders.
- **SQL:** Use lowercase keywords, CTEs for subqueries > 5 lines, qualify all columns with table aliases. Grain comment at top of every model.
- **Python:** Follow PEP 8, type hints for public functions, docstrings in Google style.
- **dbt models:** Every model has a `.yml` schema file with description + tests for primary key (not null + unique), documented foreign keys.

### 9.2 Date / Time
- All stored timestamps: **UTC**. Display timestamps in reports converted to **Africa/Libreville (WAT, UTC+1)** unless the business explicitly requests otherwise.
- Standard calendar: Gregorian. Fiscal calendar = Jan–Dec, aligned with calendar year (confirm with Finance if project spans FY boundary).
- Date dimension `dim_date` key format: `YYYYMMDD` (INT).

### 9.3 Currency & Units
- All stored monetary amounts: **EUR (€)**. Original currency stored alongside (`amount_orig`, `currency_orig`, `fx_rate_to_eur`) for audit.
- Weights: **tonnes (metric, 1000 kg)** unless stated. Distances: **kilometers**. Volumes: **m³**.
- Percentages stored as decimal (e.g., `0.92` = 92%) in models; formatted as % in BI layer.

### 9.4 Versioning
- **Semantic versioning for data models:** `{major}.{minor}.{patch}` — breaking schema change bumps major; new column/feature bumps minor; bugfix bumps patch.
- **ADR numbers:** Sequential `001-*`. See `docs/adrs/ADR-001.md` format.
- **Notebooks:** Prefix with `{YYYYMMDD}_{author-initials}_{short-description}.ipynb`.

### 9.5 Security & Access
- Row-Level Security (RLS) rules enforced at the semantic model level for:
  - **Site/location** — managers see only their site(s)
  - **Financial sensitivity** — controllers see cost data; operations see volumes only (unless explicitly granted)
- Column-Level Security (CLS) masks PII fields (driver phone, email, national ID) for roles outside HR / Payroll.

---

## 10. Deployment Information

| Environment | Purpose | URL / Endpoint | Deploy Pipeline | Data Freshness | Access |
|---|---|---|---|---|---|
| **DEV** | Development, unit testing, sandboxes | `dev-analytics-*.westeurope.cloudapp.azure.com` | CI trigger (PR) | Sample data + T-30 subset | Analytics team, devs |
| **UAT / QA** | User acceptance, integration, performance tests | `uat-analytics-*.westeurope.cloudapp.azure.com` | Manual approval after DEV green | Full copy (masked PII) from PROD T-1 | Business sponsors, testers, PM |
| **PROD** | Live dashboards, decision support | `prodeus-ws.powerbi.com/groups/...` | Scheduled Tuesdays 19:00 + hotfix on-demand | Live per source SLA | All approved consumers via AAD |

### 10.1 Deployment Gate Checklist (PROD)
- [ ] All DQ checks passed ≥ SLA threshold (see data contract)
- [ ] UAT signed-off by at least 2 business stakeholders
- [ ] Security review (if introduces new data source or user role)
- [ ] Performance test: dashboard load ≤ 5s at 2x peak concurrency
- [ ] Rollback plan written and tested in UAT
- [ ] Release notes published + stakeholders notified

---

## 11. Important Assumptions

> Assumptions are things we **accept as true for the purpose of this project**, but which may not hold. Document the *risk* and *validation plan* for each.

| ID | Assumption | If Violated / Risk | Validation Plan | Owner |
|---|---|---|---|---|
| ASM-001 | Wagon cycle is defined as **Port-to-Port** (departure to empty return). Alternative: Station-to-Station would change KPI-01 comparability. | Historical KPI-01 baseline (6.5 d target) not comparable; may over/under-state improvement. | Confirm with Supply Chain Director + document signed alignment in business-question.md. | Business Owner |
| ASM-002 | ERP `ordered_qty` and `delivered_qty` are in the same UOM for matching OTIF calc. | If UOMs differ (e.g., pieces vs kg), OTIF % will be materially wrong. | Add cross-check: `ordered_uom = delivered_uom` validation; map UOM conversion table if mismatches found. | Data Steward |
| ASM-003 | Fixed EUR/XXX FX rate from OANDA monthly close is acceptable for financial KPIs (KPI-07, 08, 09). | Realized FX differences vs invoice date rates cause ±2% variance in monthly € totals. | Align with Finance policy; they confirmed monthly close rate is standard. Log variance report each month. | Controller |
| ASM-004 | IoT gate reads are "truth" for wagon passage. If gate fails and no GPS fallback, wagon cycle is incomplete. | KPI-01 denominator decreases → looks better than reality. | Monitor `unfinished_cycle_pct` each week; alert if > 2%. Manually investigate and close cycles > 14 days. | Data Engineering |
| ASM-005 | No material pattern change in commercial contract terms during the analysis period. | A new SLA clause on demurrage after 2025-06 could make pre/post comparison unfair. | Review commercial change log; include "contract change" as covariate in trend analysis. | Commercial |
| ASM-006 | Historical data reconstruction pre-2024 is not required (MVP scope: Jan 2024 → now). | If stakeholders request YoY comparison to 2023, additional ingestion + mapping effort required (~6 weeks). | Confirm in business sign-off meeting. Document in scope exclusions. | PM |

---

*Document Owner: [Analytics Engineering Lead]*
*Last Updated: [YYYY-MM-DD]*
*Next Review: [YYYY-MM-DD or quarterly]*
