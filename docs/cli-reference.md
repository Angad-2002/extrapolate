# CLI reference

Entry point: **`xpol`** (or `uv run xpol` when using uv).

Global options (on the main group):

- `--config-file PATH` — Path to config file (TOML, YAML, or JSON).
- `-v` / `--verbose` — Increase verbosity (repeat for more).
- `--debug` — Enable debug logging.
- `--trace` — Most verbose (including third-party libs).

## Commands

### `xpol audit`

Run cost optimization audits (single or multi-project). Uses `DashboardRunner` and prints results via `DashboardVisualizer`.

**Options:**

- `--project-id` — GCP project ID (defaults to gcloud/config if not set).
- `--billing-table-prefix` — Default: `gcp_billing_export_v1`.
- `--location` — BigQuery location (default: `US`).
- `--billing-dataset` — Billing dataset (default: `{project_id}.billing_export`).
- `--regions` — Comma-separated regions (e.g. `us-central1,us-east1`).
- `--hide-project-id` — Hide project ID in output.
- `--projects` — Comma-separated project IDs for multi-project audit.
- `--all` — Audit all accessible projects.
- `--combine` — Combine projects by billing account (use with `--projects` or `--all`).

**Examples:**

```bash
xpol audit --project-id my-project
xpol audit --project-id my-project --billing-dataset my-project.billing_export --regions us-central1,us-east1
xpol audit --projects proj1,proj2,proj3
xpol audit --all --combine
```

### `xpol dashboard`

Generate an interactive cost analysis dashboard in the terminal. Uses `BaseCommand` (project-id, billing-table-prefix, location).

### `xpol report`

Generate cost analysis reports. Options include `--report-name`, `--report-type` (csv, json, pdf, dashboard; multiple allowed), `--dir`, plus base options.

### `xpol forecast`

Generate cost forecasts. Uses `BaseCommand` plus forecast-specific options (e.g. forecast days, history days) where implemented.

### `xpol trend`

Cost trend analysis. Uses `BaseCommand` plus time range, months back, labels, services.

### `xpol api`

Start the FastAPI server.

**Options:**

- `--port` — Port (default: 8000).

### `xpol run`

Run full FinOps workflow from a config file. Reads `config_data` from context (from `--config-file`) and overrides with CLI args. Options: `--report-name`, `--report-type`, `--dir`, `--time-range`, `--months-back`, `--label`, `--service`, `--hide-project-id`, plus base options.

### `xpol setup`

Show setup instructions. With `--interactive` / `-i`, starts the interactive menu (`InteractiveMenu`).

### `xpol ai` (group)

AI-powered subcommands. Subcommands are defined in `xpol.cli.ai.commands` and include (as implemented):

- **analyze** — Generate AI analysis of dashboard data.
- **ask** — Ask a natural language question about costs.
- **summary** — Executive summary.
- **explain-spike** — Explain cost changes.
- **prioritize** — Prioritize recommendations.
- **budget-suggestions** — Budget alert suggestions.
- **utilization** — Resource utilization analysis.
- **chat** — Chat command (see `xpol.cli.commands.chat`).

AI commands use `LLMService` and respect `AI_PROVIDER`, API keys, and `AI_MODEL`.

### Base options (multiple commands)

From `BaseCommand.common_options`:

- `--project-id` — GCP project ID.
- `--billing-table-prefix` — Default: `gcp_billing_export_v1`.
- `--location` — BigQuery location (default: `US`).

## Exit codes

Defined in `xpol.cli.constants`: `EX_OK`, `EX_GENERAL`, `EX_USAGE`, `EX_CONFIG`, `EX_GCP_AUTH`, `EX_GCP_PERMISSION`, `EX_GCP_NOT_FOUND`, `EX_BIGQUERY`, `EX_MONITORING`. Used by the CLI for success/failure and error categorization.

## Config file

When `--config-file` is passed, the file is loaded at startup and stored in the Click context as `config_data`. Commands like `run` and interactive workflows use it to fill project_id, billing_dataset, dir, report_type, etc. Supported extensions: `.toml`, `.yml`, `.yaml`, `.json`.
