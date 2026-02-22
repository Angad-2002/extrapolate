# Configuration

Extrapolate can be configured via environment variables, the API config endpoints, or a config file (CLI).

## Environment variables

Used by both the API and the CLI when no config file or API config is provided.

| Variable | Description |
|----------|-------------|
| `GCP_PROJECT_ID` | GCP project ID (required for API and most CLI commands) |
| `GCP_BILLING_DATASET` | BigQuery billing dataset (e.g. `PROJECT_ID.billing_export`) |
| `BIGQUERY_LOCATION` / `GCP_BIGQUERY_LOCATION` | BigQuery location (default `US`) |
| `GCP_REGIONS` | Comma-separated regions for audits (e.g. `us-central1,us-east1`) |
| `AI_PROVIDER` | AI provider: `groq`, `openai`, or `anthropic` |
| `AI_MODEL` / `GROQ_MODEL` | Model ID for the selected provider |
| `GROQ_API_KEY` | API key for Groq |
| `OPENAI_API_KEY` | API key for OpenAI |
| `ANTHROPIC_API_KEY` | API key for Anthropic |

## API configuration

The FastAPI server stores configuration in memory (not persisted).

- **Get current config:** `GET /api/config`  
  Returns: `project_id`, `billing_dataset`, `billing_table_prefix`, `regions`, `bigquery_location`.

- **Set config:** `POST /api/config`  
  Query/body parameters: `project_id`, `billing_dataset`, `billing_table_prefix`, `regions` (list), `bigquery_location`.  
  Changing config clears the dashboard cache.

The API also reads the same environment variables above; config set via `POST /api/config` overrides them for that process.

## Config file (CLI)

Use a config file with `--config-file path/to/file` (e.g. with `xpol run`). Supported formats: **TOML** (`.toml`), **YAML** (`.yml`, `.yaml`), **JSON** (`.json`).

The `ConfigManager` in `xpol.cli.config.manager` loads the file and exposes key–value pairs. Typical keys used by the CLI (e.g. in `run` and interactive flows) include:

- `project_id` — GCP project ID  
- `billing_dataset` — Billing dataset (e.g. `project.billing_export`)  
- `billing_table_prefix` — Table prefix (default in code: `gcp_billing_export_v1`)  
- `location` — BigQuery location  
- `regions` — List of regions to audit  
- `dir` — Output directory for reports  
- `time_range` — Time range in days  
- `months_back` — Months of billing data to consider  
- `report_name` — Base name for report files  
- `report_type` — List: `csv`, `json`, `pdf`, `dashboard`  
- `hide_project_id` — Whether to hide project ID in output  
- `label` / `service` — Filters (exact usage depends on command)

Example (YAML):

```yaml
project-id: my-gcp-project
billing-dataset: my-project.billing_export
billing-table-prefix: gcp_billing_export_v1
location: US
regions:
  - us-central1
  - us-east1
dir: ./reports
time-range: 30
months-back: 2
report-name: xpol-report
report-type:
  - dashboard
  - pdf
```

Example (TOML):

```toml
project_id = "my-gcp-project"
billing_dataset = "my-project.billing_export"
location = "US"
regions = ["us-central1", "us-east1"]
dir = "./reports"
report_name = "xpol-report"
report_type = ["dashboard", "pdf"]
```

## Billing table prefix

The billing table prefix is the prefix of the BigQuery billing export table(s). For a single partitioned table, you can pass the full table name (e.g. `gcp_billing_export_v1_0148A9_A6130F_E0294F`). The default used in the codebase is `gcp_billing_export_v1`.

## Caching (API)

- **Dashboard data:** Cached for 5 minutes (`_cache_ttl_seconds = 300` in `xpol.api.config`). Force refresh with `GET /api/dashboard?refresh=true` or `POST /api/refresh`.
- **Forecast data:** Cached for 15 minutes; force refresh with `GET /api/forecast?refresh=true` (and query params for days/history).
