# Analytics Engineering Project Structure

> **Template Version**: 1.1
> **Usage**: Copy this directory tree (as applicable) into the root of every analytics engineering repository. Not every project needs *every* folder — delete sections that are out of scope (e.g., a pure SQL report project may skip `src/python/ml/`). The principle: **a new team member should be able to clone the repo and, by following the top-level README, fully understand what exists, why it exists, and how to run it.**

---

## 1. Tree Layout (Complete Template)

```
analytics-project/                          # Repo / project root
│
├── README.md                               # 👉 FIRST file a new contributor reads
├── CONTRIBUTING.md                         # How to contribute: PR process, code style, testing
├── LICENSE                                 # License file (internal, MIT, Apache, etc.)
├── .gitignore                              # Python, Terraform, secrets, build artifacts
├── .gitattributes                          # Line endings, LFS for big files (parquet models)
├── .editorconfig                           # Cross-editor coding style (indent, charset)
├── .pre-commit-config.yaml                 # pre-commit hooks (black, ruff, sqlfluff, dbt-check)
├── Makefile                                # Common entrypoints: `make dev`, `make test`, `make docs`
├── justfile                                # Alternative to Make (just command runner; optional)
│
├── 00_setup/                               # 👉 All environment bootstrap lives here
│   ├── README.setup.md                     # Step-by-step: "from zero to productive dev env"
│   ├── prerequisites.md                    # Required tools + versions (Python 3.10, etc.)
│   │
│   ├── envs/                               # Environment variable templates
│   │   ├── .env.example                    # Master env template (all variables; NO REAL SECRETS)
│   │   ├── .env.dev.example                # DEV-specific overrides
│   │   ├── .env.uat.example                # UAT-specific overrides
│   │   └── .env.prod.example               # PROD variable *names* only (values in Key Vault)
│   │
│   ├── local/                              # Reproducible local development environments
│   │   ├── requirements.txt                # Pinned Python dependencies (pip-tools compile)
│   │   ├── requirements-dev.txt            # Dev-only: black, ruff, pytest, pre-commit
│   │   ├── pyproject.toml                  # Black, Ruff, pytest, mypy config + project metadata
│   │   ├── poetry.lock                     # OR: if using Poetry (choose ONE deps manager!)
│   │   ├── environment.yml                 # OR: conda environment (if conda/mamba)
│   │   ├── setup.cfg                       # Legacy (prefer pyproject.toml)
│   │   └── install.sh / install.ps1        # Shell script for 1-click local install
│   │
│   ├── containers/                         # Docker for reproducible runtime
│   │   ├── Dockerfile.dev                  # Dev image (with linters, tests, debug tools)
│   │   ├── Dockerfile.prod                 # Lean production image (no dev tools)
│   │   ├── docker-compose.yml              # Spin up local Postgres + MinIO (S3 mock) + ADX emulator
│   │   ├── docker-compose.override.yml.dev # Dev-only overrides (hot reload, debug ports)
│   │   └── .dockerignore
│   │
│   └── cloud/                              # Cloud / infra provisioning
│       ├── terraform/                      # IaC for Azure resources
│       │   ├── main.tf                     # Modules: RG, Storage, Databricks, ADF, Synapse, KV
│       │   ├── variables.tf                # Inputs: env, region, prefix, skus
│       │   ├── outputs.tf                  # Storage account name, workspace URL, etc.
│       │   ├── versions.tf                 # Pin Terraform + AzureRM provider versions
│       │   ├── backend.tf                  # Remote state (Azurerm storage backend)
│       │   ├── modules/                    # Reusable: databricks_workspace, adf_pipeline_ci
│       │   └── workspaces/                 # Per-env state: dev.tfvars, uat.tfvars, prod.tfvars
│       └── bicep/                          # ALTERNATIVE to Terraform (if org prefers Bicep)
│           ├── main.bicep
│           ├── modules/
│           └── parameters/
│
│
├── 01_src/                                 # 👉 SOURCE CODE (data pipelines, transforms, apps)
│   │
│   ├── ingestion/                          # Ingestion layer: pull from SRC-01..SRC-N
│   │   ├── adf_pipelines/                  # Azure Data Factory ARM / Terraform definitions
│   │   │   ├── linked_services/
│   │   │   ├── datasets/
│   │   │   └── pipelines/
│   │   │       ├── pl_src01_erp_full_copy.json
│   │   │       ├── pl_src02_tms_cdc_stream.json
│   │   │       └── pl_src07_weather_daily_pull.json
│   │   ├── python/                         # Custom extract/load scripts (if ADF not enough)
│   │   │   ├── common/                     # Shared helpers: auth, retries, logging
│   │   │   ├── extract_src04_gps.py        # API pollers for Geotab
│   │   │   └── load_src08_finance_csv.py   # File-drop parser + loader
│   │   └── eventhub/                       # Stream configs: topic specs, consumer groups
│   │
│   ├── dbt_project/                        # 👉 dbt (data build tool) — ELT transforms
│   │   ├── dbt_project.yml                 # dbt config: profile, model paths, versions
│   │   ├── profiles.yml                    # Connection profiles (DEV/UAT/PROD targets)
│   │   ├── packages.yml                    # dbt dependencies: dbt_utils, dbt_expectations
│   │   ├── selectors.yml                   # Named selectors: `dbt build --selector nightly`
│   │   │
│   │   ├── analyses/                       # Ad-hoc analytical SQL (not models; versioned)
│   │   │   └── logistics_wtt_pareto_2025q3.sql
│   │   │
│   │   ├── macros/                         # Reusable dbt/Jinja macros
│   │   │   ├── cents_to_eur.sql
│   │   │   ├── generate_schema_name.sql    # Custom schema naming logic
│   │   │   ├── iot_gate_fallback.sql       # G-07 GPS fallback per DI-001
│   │   │   └── tests/                      # Custom dbt test macros
│   │   │       └── assert_temporal_order.sql  # Timestamp-ordering generic test
│   │   │
│   │   ├── seeds/                          # Static reference data (checked into git)
│   │   │   ├── ref_corridors.csv           # 12 corridor codes, names, distances
│   │   │   ├── ref_locomotive_map.csv      # Locomotive ID TMS→CMMS mapping (DI-006)
│   │   │   └── ref_weather_stations.csv
│   │   │
│   │   ├── snapshots/                      # SCD Type 2 snapshots (slowly changing dims)
│   │   │   ├── snap_erp_article.sql        # SCD-2 for product attributes
│   │   │   └── snap_erp_tiers.sql          # SCD-2 for customer / supplier master
│   │   │
│   │   └── models/
│   │       ├── staging/                    # 1:1 from bronze; clean + type + rename
│   │       │   ├── src01_erp/
│   │       │   │   ├── stg_src01_erp__cde_entete.sql
│   │       │   │   ├── stg_src01_erp__cde_lignes.sql
│   │       │   │   └── src01_erp.yml       # Schema + column descriptions + stg tests
│   │       │   ├── src02_tms/
│   │       │   ├── src03_iot/
│   │       │   ├── src04_gps/
│   │       │   ├── src05_portops/
│   │       │   ├── src06_cmms/
│   │       │   └── src07_weather/
│   │       │
│   │       ├── intermediate/               # Between stg and marts — reusable joins
│   │       │   ├── logistics/
│   │       │   │   ├── int_wagon_legs.sql  # Wagon movement legs (gate-to-gate)
│   │       │   │   └── logistics.yml
│   │       │   └── finance/
│   │       │
│   │       └── marts/                      # 👉 Business-facing curated models (stars)
│   │           ├── common/                 # Conformed dimensions (shared across domains)
│   │           │   ├── dim_date.sql
│   │           │   ├── dim_time_of_day.sql
│   │           │   └── dim_currency.sql
│   │           ├── logistics/              # Rail / Port / Supply Chain domain
│   │           │   ├── dim_wagon.sql
│   │           │   ├── dim_locomotive.sql
│   │           │   ├── dim_corridor.sql
│   │           │   ├── dim_location.sql
│   │           │   ├── fact_wagon_leg_movement.sql
│   │           │   ├── fact_wagon_cycle.sql       # ⬅️ governed by data contract
│   │           │   ├── fact_train_consist.sql
│   │           │   ├── logistics.yml              # Column descriptions + dbt tests
│   │           │   └── vw_mart_wtt_dashboard.sql  # Dashboard-optimized view
│   │           ├── commercial/             # Orders, invoices, OTIF
│   │           │   ├── dim_product.sql
│   │           │   ├── dim_customer.sql
│   │           │   ├── fact_shipment_otif.sql
│   │           │   ├── fact_invoice_line.sql
│   │           │   └── commercial.yml
│   │           ├── fleet/                  # Fleet + maintenance
│   │           │   ├── fact_maintenance_workorder.sql
│   │           │   └── fleet.yml
│   │           └── finance/                # Cost center allocations
│   │               ├── fact_cost_allocations_monthly.sql
│   │               └── finance.yml
│   │
│   ├── sql/                                # Standalone SQL (if NOT using dbt)
│   │   ├── adhoc/
│   │   ├── reporting/
│   │   └── maintenance/                   # Vacuum, optimize, partition rebuilds
│   │
│   ├── python/                             # 👉 Python source (non-dbt, non-notebook)
│   │   ├── common/                         # Shared package: utils, logging, config
│   │   │   ├── __init__.py
│   │   │   ├── logging_setup.py
│   │   │   ├── config_loader.py            # Hierarchical .env + YAML config
│   │   │   ├── azure_auth.py               # DefaultAzureCredential helpers
│   │   │   └── uom.py                      # Unit-of-measure conversions
│   │   │
│   │   ├── pipelines/                      # Pipeline / ETL scripts (Databricks notebook or .py)
│   │   │   ├── bronze_to_silver_wagon.py
│   │   │   └── silver_to_gold_otif.py
│   │   │
│   │   ├── dq/                             # Data quality (Great Expectations or custom)
│   │   │   ├── great_expectations/
│   │   │   │   ├── great_expectations.yml
│   │   │   │   ├── expectations/
│   │   │   │   │   └── fact_wagon_cycle_suite.json
│   │   │   │   ├── checkpoints/
│   │   │   │   └── plugins/
│   │   │   └── custom/
│   │   │       └── run_dq_suite.py
│   │   │
│   │   ├── feature_eng/                    # Feature engineering for ML (Phase 2)
│   │   │   └── build_wtt_features.py
│   │   │
│   │   └── ml/                             # ML / modeling code (separate from pipelines)
│   │       ├── wtt_predictive_eta/         # One folder per model
│   │       │   ├── train.py
│   │       │   ├── predict.py
│   │       │   ├── evaluate.py
│   │       │   ├── model.py
│   │       │   ├── hyperparams.yml
│   │       │   └── mlproject               # MLflow project definition
│   │       └── common/
│   │
│   ├── dashboards/                         # 👉 BI artifacts (Power BI, etc.)
│   │   ├── powerbi/
│   │   │   ├── datasets/                   # Power BI Dataset .pbip projects (PBIR format)
│   │   │   │   └── wtt_ops_dataset/
│   │   │   │       ├── definition/
│   │   │   │       │   ├── dataset.json    # Tabular model TMSL (tables, measures, RLS)
│   │   │   │       │   └── connections.json
│   │   │   │       └── .pbir
│   │   │   ├── reports/                    # Power BI Reports (pbix-as-code / .pbit)
│   │   │   │   ├── wtt_operational_dashboard.pbit
│   │   │   │   ├── monthly_management_scorecard.pbit
│   │   │   │   └── otif_commercial_report.pbit
│   │   │   ├── themes/
│   │   │   │   ├── setrag_corporate_theme.json
│   │   │   │   └── accessibility_high_contrast_theme.json
│   │   │   └── deployment_pipelines/       # Power BI deployment pipeline configs
│   │   │
│   │   └── dax/                            # Shared DAX patterns + measure definitions
│   │       ├── kpi_wtt_measures.dax
│   │       └── time_intelligence_patterns.dax
│   │
│   └── config/                             # 👉 Non-secret config files (YAML / JSON)
│       ├── kpis/                           # KPI definitions as-code (single source of truth)
│       │   ├── kpi_001_wtt.yaml            # Matches CONTEXT.md §4
│       │   └── kpi_004_otif.yaml
│       ├── pipelines/                      # Pipeline schedules / DAG configs
│       │   ├── nightly_elt.yaml
│       │   └── realtime_iot.yaml
│       ├── rls/                            # Row-level security rules as-code
│       │   ├── site_manager_rls.yaml
│       │   └── finance_cost_rls.yaml
│       └── alerts/                         # Alerting / subscription configs
│           └── wtt_threshold_alerts.yaml
│
│
├── 02_tests/                               # 👉 TESTS (outside source; Python + dbt tests)
│   ├── README.tests.md                     # Test strategy, how to run, coverage targets
│   │
│   ├── unit/                               # Unit tests — no external deps, fast
│   │   ├── python/
│   │   │   ├── test_logging_setup.py
│   │   │   ├── test_config_loader.py
│   │   │   ├── test_uom_conversions.py
│   │   │   └── dq/
│   │   └── dbt/                            # dbt unit tests (dbt-core ≥1.8)
│   │       ├── test_iot_gate_fallback_macro.sql
│   │       └── test_temporal_order_test_macro.sql
│   │
│   ├── integration/                        # Integration tests — require test DB / storage
│   │   ├── dbt/
│   │   │   └── test_fact_wagon_cycle_builds_from_sample.sql
│   │   └── python/
│   │       ├── conftest.py                 # Fixtures: test DB, storage container, sample data
│   │       ├── test_bronze_to_silver_wagon.py
│   │       └── test_dq_fact_wagon_cycle_suite.py
│   │
│   ├── e2e/                                # End-to-end: run full pipeline + verify BI output
│   │   ├── test_full_nightly_elt_pipeline.py
│   │   └── fixtures/
│   │       └── sample_bronze/              # Synthetic representative sample data
│   │           ├── src01_erp/
│   │           └── src03_iot/
│   │
│   ├── contract/                           # Data contract conformance tests
│   │   └── test_data_contract_fact_wagon_cycle.py  # Validates spec.quality rules
│   │
│   └── performance/                        # Load / performance tests
│       ├── test_dashboard_query_perf.py    # Simulate 50 concurrent dashboard users
│       └── locustfile.py                   # OR k6.js script
│
│
├── 03_docs/                                # 👉 DOCUMENTATION (human-authored, auto-generated)
│   ├── README.docs.md
│   │
│   ├── context/                            # 👉 Context artifacts (from templates/)
│   │   ├── CONTEXT.md                      # Master glossary, KPI defs, data sources
│   │   ├── business-question.md            # Request that kicked off this project
│   │   ├── definition-of-done.md           # What "done" means for each deliverable
│   │   └── project-charter.md              # Optional: goals, scope, timeline, budget
│   │
│   ├── adrs/                               # 👉 Architecture Decision Records
│   │   ├── ADR-001-record-architectural-decisions.md
│   │   ├── ADR-002-medallion-lakehouse-topology.md
│   │   ├── ADR-003-use-dbt-for-transforms.md
│   │   └── index.md                        # ADR index (status, date, decider summary)
│   │
│   ├── contracts/                          # 👉 Data contracts
│   │   ├── gold/
│   │   │   └── logistics/
│   │   │       └── fact-wagon-cycle.contract.yml
│   │   ├── silver/
│   │   └── index.md                        # Contract catalog summary; link to Purview entry
│   │
│   ├── runbooks/                           # Step-by-step ops guides
│   │   ├── oncall-playbook.md              # What to do when the pipeline fails at 3 AM
│   │   ├── runbook_deploy_prod_release.md
│   │   ├── runbook_rollback_release.md
│   │   ├── runbook_backfill_missing_partition.md
│   │   ├── runbook_data_quality_incident.md
│   │   └── runbook_reproduce_report_rpt_2025_019.md
│   │
│   ├── howto/                              # End-user + contributor guides
│   │   ├── howto_add_new_data_source.md
│   │   ├── howto_deploy_powerbi_workspace.md
│   │   ├── howto_onboard_new_analyst.md
│   │   └── howto_write_a_kpi_definition.md
│   │
│   ├── reports/                            # Published analysis outputs
│   │   ├── rpt-2025-019-wtt-root-cause/
│   │   │   ├── analysis-report.md          # From templates/analysis-report.md
│   │   │   ├── figures/                    # High-res PNGs / PDFs
│   │   │   └── tables/                     # Excel / CSV appendix tables
│   │   └── index.md
│   │
│   ├── api/                                # Auto-generated API / data dictionary
│   │   └── dbt_docs/                       # `dbt docs generate` output
│   │
│   └── diagrams/                           # Architecture diagrams (Mermaid + DrawIO)
│       ├── logical_data_flow.mmd
│       ├── security_boundaries.mmd
│       ├── ci_cd_pipeline.mmd
│       └── exported_pngs/
│
│
├── 04_notebooks/                           # 👉 Exploratory analysis (NOT prod pipelines)
│   ├── README.notebooks.md                 # Notebook hygiene rules (no secrets, naming)
│   ├── archive/                            # Old explorations (keep, but signal not current)
│   ├── 2025-q3/
│   │   ├── 20250715_js_wtt_variance_decomposition.ipynb
│   │   ├── 20250722_js_sequencing_natural_experiment.ipynb
│   │   └── 20250801_js_intervention_roi_simulation.ipynb
│   └── shared/
│       └── common_imports_and_setup.ipynb  # %run-able notebook: imports + spark init
│
│
├── 05_data/                                # 👉 Sample / local-only data (NOT production data!)
│   ├── README.data.md                      # What this folder is for, what goes NOT here
│   ├── raw_samples/                        # Small (≤ 10 MB each) sample inputs for unit tests
│   ├── fixtures/                           # E2E test fixtures (generated)
│   ├── generated/                          # Output of local runs (.gitignore often)
│   └── external/                           # Third-party datasets (weather, benchmarks)
│
├── 06_cicd/                                # 👉 CI/CD: pipelines, workflows, gates
│   ├── azure-devops/                       # If using Azure DevOps Pipelines
│   │   ├── pipelines/
│   │   │   ├── ci-pr-gate.yml              # Runs on every PR: lint + unit tests
│   │   │   ├── ci-main.yml                 # Runs on merge to main: integration tests
│   │   │   ├── cd-dev.yml                  # Deploys to DEV after CI pass
│   │   │   ├── cd-uat.yml                  # After UAT sign-off: deploy UAT
│   │   │   └── cd-prod.yml                 # After PROD approval: deploy PROD + gates
│   │   ├── environments/
│   │   │   ├── dev.yaml
│   │   │   ├── uat.yaml
│   │   │   └── prod.yaml                   # Required approvers, protection rules
│   │   └── templates/                      # Reusable YAML templates/steps
│   │       ├── step-run-dbt-tests.yml
│   │       └── step-deploy-powerbi.yml
│   └── github/                             # ALTERNATIVE: GitHub Actions
│       └── workflows/
│
│
└── 99_scratch/                             # 👉 Ephemeral; delete anytime
    └── README.scratch.md                   # "This folder is NOT reviewed; clean up often."
```

---

## 2. Directory-by-Directory Rationale

| Folder | Purpose | What *NOT* to Put Here |
|---|---|---|
| **README.md** | Single source of truth: project overview, 10-second onboarding, links to setup + docs, status badge. | Don't bury runbooks or KPI definitions here — link to `03_docs/`. |
| **00_setup/** | *Everything* a new dev needs to get a working local or cloud dev environment in ≤ 30 minutes. Secrets (real keys, connection strings). Use `.env.example` + Key Vault references. |
| **01_src/dbt_project/** | dbt transformation logic. One of **three core pillars** of the project (alongside tests and docs). | Raw ingestion code. Notebook scratch work. |
| **01_src/python/** | Python code that *ships to production* (pipelines, DQ, ML). Organized by responsibility. | Analysis notebooks (use `04_notebooks`). 1-off ad-hoc scripts (put in `99_scratch/` then graduate if used > twice). |
| **01_src/dashboards/** | BI artifacts, ideally as-code (Power BI `.pbip` / Tabular Editor save). | Exported `.pbix` binaries (use `.pbit` templates or PBIR; track binary in LFS if must). |
| **01_src/config/** | *Non-secret* configuration as-code. KPI defs, pipeline schedules, RLS rules. | Connection strings, passwords, API keys. Those go in `.env` (gitignored) → Azure Key Vault. |
| **02_tests/** | All tests, split by scope (unit / integration / e2e / contract / perf). Mirror the `01_src/` structure inside. | Production code. Data fixtures live in `02_tests/e2e/fixtures/`; don't mix with `05_data/`. |
| **03_docs/context/** | Governance artifacts: CONTEXT, business question, DoD. Update these *first* when scope changes. | Meeting notes (use ADO / Confluence; link if needed). |
| **03_docs/adrs/** | ADRs, numbered sequentially. Create one for *every* consequential technical decision. | Design discussions that didn't reach a decision. Use ADR `Status: Rejected` for options considered. |
| **03_docs/contracts/** | Machine-readable data contracts. Every Gold model has a contract. Critical Silver models do too. | Informal column spreadsheets. Write the contract in YAML. |
| **04_notebooks/** | Exploratory work. Naming: `YYYYMMDD_{initials}_{short-slug}.ipynb`. Clear outputs before commit. | Production pipelines (refactor into `01_src/python/` or dbt when an analysis graduates). |
| **05_data/** | *Small*, *non-sensitive*, sample or fixture data for tests. ≤ 10 MB/file, ≤ 100 MB total in repo. | Real production data (use Dev storage accounts). Large files → use Git LFS or don't commit. |
| **06_cicd/** | Pipeline-as-code for CI/CD. Review changes here with extra care — they touch all environments. | Secret values (use pipeline secret variables + link to Key Vault). |
| **99_scratch/** | Temporary throwaway work. "I need to paste something for an hour." Can be `.gitignore`d entirely. | Anything you want a teammate to review. Anything that needs to survive a `git clean`. |

---

## 3. The Top-Level README.md Checklist (Every Project Must Answer These)

At an absolute minimum, your root `README.md` must answer:

1. **What is this project?** 1–2 sentences. "Logistics analytics platform for SETRAG rail operations: wagon turnaround KPI dashboards and root-cause analysis."
2. **Why does it exist?** Link to the business-question.md or a one-paragraph business driver.
3. **How do I run it locally?** A 5-step quickstart that a dev *actually tested*.
   ```bash
   # 1. Install prerequisites (Python 3.10, Docker, Azure CLI 2.50+)
   # 2. Clone + cd
   git clone <repo-url> && cd analytics-project
   # 3. Bootstrap (creates venv + installs deps)
   00_setup/local/install.sh
   # 4. Copy env template; fill in values from Azure Key Vault
   cp 00_setup/envs/.env.example .env
   # 5. Run local tests to verify
   make test-unit
   ```
4. **Where is the documentation?** Link to `03_docs/`, CONTEXT.md, and the onboarding guide.
5. **How do I deploy?** Link to `03_docs/runbooks/runbook_deploy_prod_release.md`.
6. **Who owns it?** Team name, oncall link, Slack channel, primary contact email.
7. **Status badges** (if CI/CD exists) — fill the badge image URL and target link:
   - CI main branch build status
   - Unit test coverage %
   - Last dbt run status
   - Data contract compliance score / SLO

---

## 4. Key Conventions Enforced By This Structure

### 4.1 Three "First-Class" Pillars
Code, tests, and documentation are **equal citizens**. A contribution that adds source code but no corresponding test change *and* no documentation update should be rejected at PR review.

### 4.2 Pipeline Isolation
**No notebook is a production pipeline.** If analysis graduates to a recurring pipeline:
1. Refactor logic into `01_src/python/` or a dbt model.
2. Add tests under `02_tests/`.
3. Scheduler config added to `01_src/config/pipelines/`.
4. Retire / archive the notebook to `04_notebooks/archive/`.

### 4.3 "Code Ownership By Directory"
GitHub `CODEOWNERS` (at repo root) assigns default reviewers per folder:
```ini
# CODEOWNERS
01_src/dbt_project/models/marts/logistics/  @setrag/analysts-logistics
01_src/python/ml/                            @setrag/data-science
03_docs/adrs/                                @setrag/architecture-review-board
06_cicd/                                     @setrag/devops
```

### 4.4 "Small First, Graduate Up"
Start work in `99_scratch/` → move to `04_notebooks/` if reusable → move to `01_src/` once it ships to production. This keeps the "core" repo clean while still versioning experimental work.

### 4.5 Reproducibility First
Any report, model, or KPI that leaves the team must have:
- A committed code path that reproduces it (dbt model + notebook + pipeline config),
- Exact environment (pinned `requirements.txt` / `poetry.lock`),
- Input data snapshot or a pointer to an immutable date/version of the input tables,
- Documented in the reports `03_docs/reports/<id>/analysis-report.md`.

---

*Template Owner: Analytics Engineering Guild / Architecture Review Board*
*Next Review: 2026-Q1 or when a core tool (dbt, Databricks, ADF) changes major version.*
