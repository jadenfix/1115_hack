# 1115_hack

Backend scaffold for the ResearchCompany Temporal workflows described in `.md`.

## Running locally

```bash
cp .env.example .env
docker compose up --build
```

Services:
- `temporal`: Temporal backed by persistent PostgreSQL
- `temporal-ui`: UI on http://localhost:8233
- `api`: FastAPI server on http://localhost:8000
- `worker`: Temporal worker with activities/workflows from `.md`
- shared `./data` volume mounts to `/data` for Agent Wall screenshots/state

API:
- `POST /api/run_research` with JSON `{"name": "Acme", "domain": "acme.com"}` to kick off a run
- `POST /api/self_learn` to trigger the policy updater
- `GET /api/run/{workflow_id}/windows` powers the Agent Wall (live 3×3 grid)

UI:
- Open `http://localhost:8000` to run the agent, watch the Agent Wall, and view snapshot tabs.

## Regression checks

Install `requirements.txt`, then run from the repository root:

```bash
PYTHONPATH=1115 python -m unittest discover -s 1115/tests -v
```

These checks validate activity dispatch against the installed Temporal SDK,
independent workflow IDs, and snapshot visibility across separate processes.
They do not call external providers or require a Temporal server. A live run still
requires a working Temporal service and provider credentials. Both Docker services
set `DATA_DIR=/data` so the worker and API use the same persistent volume; local
Python runs default to `app/data`, or may set `DATA_DIR` explicitly.

## Real local Temporal check

Install the [Temporal CLI](https://github.com/temporalio/cli), then from the `1115` directory:

```bash
PYTHONPATH=. python scripts/check_temporal.py
```

This starts an actual persistent SQLite Temporal development server and default
sandboxed worker, runs both workflows, checks stored snapshots and policy state,
and shuts the server down. Linkup supplies one explicitly labeled fixture URL;
other providers use their credential-free fallbacks. This verifies orchestration
and persistence, not live company research. `TEMPORAL_CLI` can select an executable
and `TEMPORAL_TEST_DB` can select the durable test database.

Compose supplies PostgreSQL and a separate UI rather than assuming auto-setup
includes a database/UI. It waits for database and Temporal health before API/worker
startup. Compose execution needs Docker; it was not available in the audit runtime.
