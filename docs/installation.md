# Installation

## Requirements

- **Python:** 3.9 or higher (below 3.14 per `pyproject.toml`)
- **GCP:** A Google Cloud project with billing enabled and BigQuery billing export set up
- **Auth:** Application Default Credentials (e.g. `gcloud auth application-default login`)

## Install from source (recommended: uv)

Using [uv](https://github.com/astral-sh/uv) keeps dependencies and the environment in sync with the lockfile:

```bash
cd extrapolate
uv sync
```

Run the CLI with:

```bash
uv run xpol --help
```

Always use `uv run xpol` (or `uv run python -m xpol.cli.main`) so the correct environment and dependencies are used.

## Install with pip

From the `extrapolate` directory:

```bash
pip install -e .
```

Then run:

```bash
xpol --help
```

## GCP setup

1. **Enable APIs** (as needed for the features you use):

   - Billing: `cloudbilling.googleapis.com`
   - BigQuery: `bigquery.googleapis.com`
   - Cloud Run: `run.googleapis.com`
   - Cloud Functions: `cloudfunctions.googleapis.com`
   - Compute: `compute.googleapis.com`
   - Cloud SQL: `sqladmin.googleapis.com`
   - Resource Manager: `cloudresourcemanager.googleapis.com`
   - Monitoring: `monitoring.googleapis.com`

2. **BigQuery billing export**

   - In GCP Console: Billing → Billing export → BigQuery export.
   - Note the dataset (e.g. `billing_export`). The full dataset ID is usually `PROJECT_ID.billing_export`.
   - Wait for data to appear (often up to 24 hours).

3. **Authentication**

   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```

4. **Environment (for API and full flows)**

   - `GCP_PROJECT_ID` — GCP project ID.
   - `GCP_BILLING_DATASET` — Billing dataset (e.g. `YOUR_PROJECT.billing_export`).
   - Optional: `BIGQUERY_LOCATION` or `GCP_BIGQUERY_LOCATION` (default `US`).
   - Optional: `GCP_REGIONS` — comma-separated regions for audits (e.g. `us-central1,us-east1`).

## Verifying the install

- **CLI:** `uv run xpol --help` and `uv run xpol audit --help`.
- **API:** `uv run xpol api --port 8000`, then open `http://localhost:8000/docs` and call `GET /api/health`. Configure `GCP_PROJECT_ID` and `GCP_BILLING_DATASET` (env or `POST /api/config`) before using dashboard/forecast/audit endpoints.
