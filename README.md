# xpol — GCP FinOps Dashboard

**xpol** is a GCP cost optimization and resource auditing toolkit. It analyzes BigQuery billing data, runs audits across Cloud Run, Cloud Functions, Compute Engine, Cloud SQL, and Storage, and provides a REST API and CLI for dashboards, PDF reports, cost forecasting, and AI-powered insights.

## Features

- **Cost analysis** — Current month, last month, and YTD spending from BigQuery billing export
- **Resource audits** — Cloud Run, Cloud Functions, Compute Engine, Cloud SQL, Storage (idle detection, right-sizing, recommendations)
- **Cost forecasting** — Prophet-based predictions and alert thresholds
- **PDF reports** — Generated via `xpol.utils.reports.ReportGenerator`
- **REST API** — FastAPI server with dashboard, costs, audits, recommendations, reports, AI, and forecast routes
- **AI insights** — Multiple providers (Groq, OpenAI, Anthropic); analysis, executive summary, Q&A, prioritization, budget suggestions, utilization analysis
- **Multi-project** — Audit single or multiple projects; combine by billing account

## Prerequisites

- Python 3.9+
- Google Cloud project with billing enabled
- BigQuery billing export configured
- GCP authentication (e.g. `gcloud auth application-default login`)

## Installation

### With uv (recommended)

```bash
cd extrapolate
uv sync
uv run xpol --help
```

### With pip

```bash
pip install -e .
xpol --help
```

## Quick start

### 1. Configure GCP

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

Set billing export dataset (required for API and full flows):

```bash
export GCP_PROJECT_ID=YOUR_PROJECT_ID
export GCP_BILLING_DATASET=YOUR_PROJECT.billing_export
```

Optional: `BIGQUERY_LOCATION` or `GCP_BIGQUERY_LOCATION` (default `US`), `GCP_REGIONS` (comma-separated).

### 2. Run an audit (CLI)

```bash
uv run xpol audit --project-id YOUR_PROJECT_ID
# Or with explicit billing dataset and regions:
uv run xpol audit --project-id YOUR_PROJECT_ID --billing-dataset YOUR_PROJECT.billing_export --regions us-central1,us-east1
```

### 3. Start the API server

```bash
uv run xpol api --port 8000
```

Then configure the API (if not using env vars) via `POST /api/config` with `project_id`, `billing_dataset`, etc. Open `http://localhost:8000/docs` for Swagger UI.

## CLI commands

| Command | Description |
|--------|--------------|
| `xpol audit` | Run cost optimization audit (single or multi-project) |
| `xpol dashboard` | Generate cost analysis dashboard (terminal) |
| `xpol report` | Generate reports (csv, json, pdf, dashboard) |
| `xpol forecast` | Generate cost forecast |
| `xpol trend` | Cost trend analysis |
| `xpol api` | Start FastAPI server (default port 8000) |
| `xpol run` | Run full analysis from config file |
| `xpol setup` | Setup instructions; use `--interactive` for menu |
| `xpol ai *` | AI subcommands (analyze, ask, summary, etc.) |

Common options (where applicable): `--config-file`, `--project-id`, `--billing-table-prefix`, `--location`. Audit also supports `--billing-dataset`, `--regions`, `--hide-project-id`, `--projects`, `--all`, `--combine`.

Use a config file (TOML, YAML, or JSON) with `--config-file path/to/config.toml`; `xpol run` uses it for project_id, dir, time_range, report_type, etc.

## API overview

- **Root:** `GET /` — name, version, status, link to `/docs`
- **Health:** `GET /api/health` — status, timestamp, configured
- **Config:** `GET /api/config`, `POST /api/config` — get/set project_id, billing_dataset, regions, etc.
- **Dashboard:** `GET /api/dashboard`, `GET /api/summary`, `POST /api/refresh`, `GET /api/resources/summary`
- **Costs:** `GET /api/costs/services`, `GET /api/costs/trend`
- **Audits:** `GET /api/audits`, `GET /api/audits/{audit_type}` (optional `?refresh=true`)
- **Recommendations:** `GET /api/recommendations` (optional `priority`, `resource_type`, `limit`)
- **Reports:** `POST /api/reports/generate`, `GET /api/reports`, `GET /api/reports/{filename}/download`, `DELETE /api/reports/{filename}`
- **AI:** `GET /api/ai/status`, `GET /api/ai/models`, `POST /api/ai/models/set`, `POST /api/ai/analyze`, `POST /api/ai/explain-spike`, `POST /api/ai/executive-summary`, `POST /api/ai/ask`, `POST /api/ai/prioritize-recommendations`, `POST /api/ai/suggest-budgets`, `POST /api/ai/analyze-utilization`
- **Forecast:** `GET /api/forecast`, `GET /api/forecast/summary`, `GET /api/forecast/service/{service_name}`, `GET /api/forecast/trends`, `GET /api/forecast/alert-thresholds`, `GET /api/forecast/debug`

API expects `GCP_PROJECT_ID` and `GCP_BILLING_DATASET` (env or `/api/config`). Dashboard and forecast data are cached (5 and 15 minutes).

## AI providers

Set one of:

- `GROQ_API_KEY` (and optional `GROQ_MODEL` / `AI_MODEL`)
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

Use `AI_PROVIDER=groq|openai|anthropic` and `AI_MODEL` to choose provider and model. Interactive config: `xpol config ai --interactive` (if available in your build).

## Project structure

```
xpol/
├── api/                 # FastAPI app and route modules
│   ├── main.py
│   ├── config.py        # API config and dashboard/forecast caching
│   ├── routes/          # dashboard, costs, audits, recommendations, reports, ai, forecast, config
│   └── serializers.py
├── cli/
│   ├── main.py          # Click entrypoint (xpol)
│   ├── commands/        # dashboard, report, audit, forecast, trend, api, run
│   ├── ai/              # AI command group
│   ├── config/          # ConfigManager, setup
│   ├── interactive/     # Interactive menu and workflows
│   └── utils/           # display, formatting, progress
├── core/
│   └── dashboard_runner.py   # Orchestrates cost processor, auditors, forecast, budget
├── clients/
│   └── gcp.py           # GCPClient (BigQuery, Cloud Run, Functions, Compute, SQL, Monitoring)
├── services/
│   ├── billing/         # CostProcessor, BQSpendService
│   ├── forecast/        # ForecastService (Prophet)
│   ├── llm/             # LLM service and providers (Groq, OpenAI, Anthropic)
│   ├── rag/             # RAG service and vector store
│   ├── budget/          # BudgetService
│   └── project/         # ProjectManager
├── auditors/            # CloudRun, CloudFunctions, Compute, CloudSQL, Storage
├── utils/
│   ├── reports/         # ReportGenerator (PDF)
│   ├── visualizations/  # DashboardVisualizer, ChartGenerator
│   └── helpers.py
└── types.py             # DashboardData, AuditResult, ForecastData, etc.
```

## Documentation

- [Installation & setup](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Architecture & system design](docs/architecture.md)
- [CLI reference](docs/cli-reference.md)
- [API reference](docs/api-reference.md)

## License

MIT (see project metadata).
