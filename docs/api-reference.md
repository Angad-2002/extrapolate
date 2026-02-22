# API reference

The xpol API is a **FastAPI** application. Start it with:

```bash
uv run xpol api --port 8000
```

Interactive docs: **http://localhost:8000/docs** (Swagger UI).  
Configuration must be set (env vars or `POST /api/config`) for dashboard, costs, audits, forecast, and reports to work.

---

## Root and health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Name, version, status, link to `/docs` |
| GET | `/api/health` | Health check; `status`, `timestamp`, `configured` |

---

## Configuration

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config` | Current in-memory config (project_id, billing_dataset, etc.) |
| POST | `/api/config` | Set config (query/body: project_id, billing_dataset, billing_table_prefix, regions, bigquery_location). Clears dashboard cache. |

---

## Dashboard

Data is cached for 5 minutes. Use `?refresh=true` or `POST /api/refresh` to force refresh.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/dashboard` | Full dashboard (project_id, billing_month, costs, audit_results, recommendations). Query: `refresh` (bool) |
| GET | `/api/summary` | Cost summary (current_month, last_month, ytd, change_pct, resources_active, potential_savings) |
| POST | `/api/refresh` | Force refresh dashboard cache |
| GET | `/api/resources/summary` | Aggregated resources (total, running, idle, untagged) |

---

## Costs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/costs/services` | Costs by service (array of `{name, value}` sorted by value desc) |
| GET | `/api/costs/trend` | Cost trend (e.g. 6 months); format may use placeholder months when historical data is limited |

---

## Audits

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/audits` | All audit results (keyed by audit type) |
| GET | `/api/audits/{audit_type}` | One audit type. Query: `refresh` (bool) to run that audit on demand |

Audit types align with auditors: e.g. cloud_run, cloud_functions, compute, cloud_sql, storage.

---

## Recommendations

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/recommendations` | Optimization recommendations. Query: `priority`, `resource_type`, `limit` |

---

## Reports

Reports are stored under the `reports` directory (relative to the xpol package root). Paths are validated to prevent traversal.

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/reports/generate` | Generate PDF report. Query: `format` (default `pdf`). Returns filename, size, download_url |
| GET | `/api/reports` | List reports (filename, size, created_at, download_url) |
| GET | `/api/reports/{filename}/download` | Download report PDF |
| DELETE | `/api/reports/{filename}` | Delete report file |

---

## AI

All POST endpoints require a configured AI provider (Groq, OpenAI, or Anthropic) via env vars and optional `AI_PROVIDER` / `AI_MODEL`. If not configured, endpoints return 503 or indicate “not configured”.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/ai/status` | Whether AI is enabled; provider, model, message |
| GET | `/api/ai/models` | Available models (id, name, description, context_window, recommended); current_model, default_model |
| POST | `/api/ai/models/set` | Set model for session. Query: `model_id` |
| POST | `/api/ai/analyze` | Full dashboard AI analysis. Query: `refresh` (bool) |
| POST | `/api/ai/explain-spike` | Explain cost change vs last month |
| POST | `/api/ai/executive-summary` | Executive summary |
| POST | `/api/ai/ask` | Natural language question. Query: `question` |
| POST | `/api/ai/prioritize-recommendations` | Prioritize optimization recommendations |
| POST | `/api/ai/suggest-budgets` | Budget alert suggestions |
| POST | `/api/ai/analyze-utilization` | Resource utilization analysis |

---

## Forecast

Forecast uses `ForecastService` (Prophet). Some responses are cached (e.g. 15 minutes for full forecast).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/forecast` | Cost forecast. Query: `days` (default 90), `historical_days` (default 180), `refresh` (bool) |
| GET | `/api/forecast/summary` | Summary (e.g. predicted_cost_next_30d, current_month_cost, trend, confidence). Query: `days` (default 30) |
| GET | `/api/forecast/service/{service_name}` | Forecast for one service. Query: `days`, `historical_days` |
| GET | `/api/forecast/trends` | Trends for top services (current cost, predicted 30d, trend, confidence) |
| GET | `/api/forecast/alert-thresholds` | Recommended alert thresholds (conservative, warning, critical) from forecast |
| GET | `/api/forecast/debug` | Debug: config, date range, sample of historical data and row count |

---

## CORS

The app allows origins: `http://localhost:3000`, `http://localhost:3001`, `http://127.0.0.1:3000`, `http://127.0.0.1:3001`, with credentials, all methods and headers.

## Errors

Endpoints return standard HTTP status codes. On failure, the body usually includes a `detail` string (e.g. from `HTTPException`). Configuration errors (missing project_id or billing_dataset) surface as 500 with a message or via `GET /api/health` (`configured: false`).
