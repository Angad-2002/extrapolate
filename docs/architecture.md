# Architecture & system design

This document describes the high-level architecture of **Extrapolate** (GCP FinOps Dashboard): components, data flow, and how the CLI and API use the same core services.

## Overview

Extrapolate is a Python application (package name **xpol**) that:

1. **Reads GCP billing data** from BigQuery (billing export).
2. **Audits GCP resources** (Cloud Run, Cloud Functions, Compute Engine, Cloud SQL, Storage) via GCP client APIs and Monitoring.
3. **Aggregates costs and recommendations** into a single dashboard model.
4. **Exposes results** via a Click-based CLI and a FastAPI REST API; both use the same core runner and services.

## High-level architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ENTRY POINTS                                    │
├──────────────────────────────┬──────────────────────────────────────────────┤
│  CLI (Click)                  │  API (FastAPI)                               │
│  xpol.cli.main                │  xpol.api.main                               │
│  • audit, dashboard, report,   │  • /api/dashboard, /api/audits,              │
│    forecast, trend, api, run,  │    /api/forecast, /api/reports, /api/ai     │
│    setup, ai *                │  • Config + in-memory cache                  │
└──────────────┬───────────────┴──────────────────┬───────────────────────────┘
               │                                   │
               ▼                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         CORE ORCHESTRATION                                    │
│  xpol.core.DashboardRunner                                                    │
│  • CostProcessor (BigQuery billing)                                           │
│  • Auditors (Cloud Run, Functions, Compute, Cloud SQL, Storage)               │
│  • ForecastService (Prophet)                                                 │
│  • BudgetService, BQSpendService, ProjectManager                             │
│  • Produces: DashboardData (costs + audit_results + recommendations)         │
└──────────────────────────────────────┬───────────────────────────────────────┘
               │                         │
               ▼                         ▼
┌─────────────────────────────┐  ┌───────────────────────────────────────────┐
│  GCP & DATA ACCESS           │  │  OUTPUT & AI                               │
│  xpol.clients.GCPClient      │  │  • xpol.utils.reports.ReportGenerator (PDF)│
│  • BigQuery, Cloud Run,      │  │  • xpol.utils.visualizations (terminal)    │
│    Functions, Compute,       │  │  • xpol.services.llm.LLMService (multi-    │
│    Cloud SQL, Monitoring     │  │    provider: Groq, OpenAI, Anthropic)      │
│  • Lazy-initialized clients  │  │  • xpol.services.rag (RAG for documents)   │
└─────────────────────────────┘  └───────────────────────────────────────────┘
```

## Component roles

### Entry points

- **CLI** (`xpol.cli.main`): Click group with lazy-loaded subcommands. Global options: `--config-file`, `-v`, `--debug`, `--trace`. Commands (e.g. `audit`, `dashboard`, `report`, `forecast`, `trend`, `api`, `run`, `setup`, `ai *`) either call `DashboardRunner` (and related services) or start the API server.
- **API** (`xpol.api.main`): FastAPI app with CORS, routers for config, dashboard, costs, audits, recommendations, reports, AI, forecast. Configuration and dashboard/forecast caches live in `xpol.api.config`.

### Core orchestration

- **DashboardRunner** (`xpol.core.dashboard_runner`):
  - Instantiates `GCPClient`, `CostProcessor`, all auditors, `ForecastService`, `BudgetService`, `BQSpendService`, `ProjectManager`.
  - `run()`: Fetches current/last month and YTD costs, runs all auditors, aggregates recommendations, returns `DashboardData`.
  - Supports single-project and multi-project (`run_multi_project`); can run a single audit type for the API (`run_specific_audit`).

### Data and types

- **DashboardData** (`xpol.types`): project_id, billing_month, current_month_cost, last_month_cost, ytd_cost, service_costs, audit_results (dict by audit type), recommendations, total_potential_savings. Optional budget alerts when added by the runner.
- **AuditResult** (per audit type): total_count, idle_count, untagged_count, details list, recommendations list.
- **ForecastData**: Prophet output (e.g. daily predictions, total_predicted_cost, trend, model_confidence).

### GCP and billing

- **GCPClient** (`xpol.clients.gcp`): Holds project_id, credentials, and BigQuery location. Exposes lazy properties: bigquery, cloud_run, cloud_functions, compute_instances, compute_disks, compute_addresses, cloud_sql, monitoring. Used by auditors and by `CostProcessor` (BigQuery only).
- **CostProcessor** (`xpol.services.billing.cost_processor`): Queries BigQuery billing export (current month, last month, YTD, service costs). Uses billing_dataset and billing_table_prefix (including support for partitioned table naming).
- **BQSpendService**: BigQuery-based spend aggregation (used for multi-project or spend views).

### Auditors

Each auditor implements resource listing and optional metrics, then produces an `AuditResult` with recommendations.

- **CloudRunAuditor**: Cloud Run services + Monitoring metrics → idle/min instances, CPU/memory sizing.
- **CloudFunctionsAuditor**: Cloud Functions (v2) + metrics → invocations, memory, errors.
- **ComputeAuditor**: Compute Engine instances → running/stopped, machine type, idle.
- **CloudSQLAuditor**: Cloud SQL instances + monitoring.
- **StorageAuditor**: Persistent disks (unattached, size) and static IPs (unused).

Recommendations are typed as `OptimizationRecommendation` (priority, resource_type, description, potential_monthly_savings, etc.).

### Forecast

- **ForecastService** (`xpol.services.forecast`): Extends billing base service; reads daily costs from BigQuery, fits Prophet, returns `ForecastData`. Used for `/api/forecast`, summary, per-service forecast, and alert thresholds.

### API config and caching

- **api.config**: In-memory config (project_id, billing_dataset, regions, etc.) and two caches:
  - Dashboard: TTL 5 minutes; refreshed by `get_cached_dashboard_data(force_refresh=True)` or `POST /api/refresh`.
  - Forecast: TTL 15 minutes; optional refresh via query param on forecast endpoints.
- **REPORTS_DIR**: Package-root-level `reports/` directory; PDFs and temp chart images written there.

### AI (LLM)

- **LLMService** (`xpol.services.llm.service`): Chooses provider (Groq, OpenAI, Anthropic) via `AI_PROVIDER` and corresponding API key env vars. Methods: analyze_dashboard_data, explain_cost_spike, generate_executive_summary, answer_question, prioritize_recommendations, suggest_budget_alerts, analyze_resource_utilization. The API routes under `/api/ai/*` call these with cached dashboard data.

### Reports and output

- **ReportGenerator** (`xpol.utils.reports.generator`): Takes `DashboardData`, uses `ChartGenerator` for Plotly charts (saved as temp PNGs in output_dir), produces a PDF (e.g. ReportLab) with cost summary, audit sections, and recommendations.
- **DashboardVisualizer** (`xpol.utils.visualizations.dashboard`): Renders dashboard and multi-project dashboard to the terminal (e.g. Rich tables/panels).

## Data flow (typical)

1. **Config**: Env vars or `POST /api/config` (or CLI `--config-file`) set project_id, billing_dataset, regions, etc.
2. **Run**: `DashboardRunner.run()` → CostProcessor (BigQuery) + each auditor (GCP APIs + Monitoring) → `DashboardData`.
3. **API**: Routes call `get_cached_dashboard_data()` (or `get_dashboard_runner().run()` on refresh); serialize via `api.serializers` and return JSON.
4. **CLI**: `audit` (and similar) creates `DashboardRunner`, calls `run()`, passes `DashboardData` to `DashboardVisualizer.display_dashboard()`.
5. **Reports**: API or interactive menu gets `DashboardData`, instantiates `ReportGenerator(output_dir=REPORTS_DIR)`, calls `generate_report(data, output_path)`.
6. **Forecast**: API or CLI uses `ForecastService` with same billing_dataset/table_prefix; results cached in API layer.
7. **AI**: API routes get cached dashboard data and call `LLMService` methods; responses returned as JSON.

## Security and secrets

- Credentials: GCP Application Default Credentials (no keys in repo).
- API keys for LLM: From environment only (`GROQ_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).
- `.env` and config files with secrets are gitignored; use `.env.example` as a template.

## Dependencies (conceptual)

- **Core**: google-cloud-bigquery, google-cloud-run, google-cloud-functions, google-cloud-compute, google-api-python-client, google-cloud-monitoring, google-auth, etc.
- **CLI**: click, rich, inquirerpy, pyfiglet, textual (optional).
- **API**: fastapi, uvicorn, python-dotenv.
- **Forecast**: prophet, pandas.
- **Reports**: reportlab, plotly, kaleido.
- **AI**: groq, openai, anthropic, langchain*, chromadb, etc. (optional depending on features).

All are declared in `pyproject.toml`; the project uses `uv` (or pip) for install and lockfile.
