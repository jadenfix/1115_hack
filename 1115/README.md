# 1115_hack

Backend scaffold for the ResearchCompany Temporal workflows described in `.md`.

## Running locally

```bash
docker-compose up --build
```

Services:
- `temporal`: auto-setup Temporal + UI on http://localhost:8233
- `api`: FastAPI server on http://localhost:8000
- `worker`: Temporal worker with activities/workflows from `.md`
- shared `./data` volume mounts to `/data` for Agent Wall screenshots/state

API:
- `POST /api/run_research` with JSON `{"name": "Acme", "domain": "acme.com"}` to kick off a run
- `POST /api/self_learn` to trigger the policy updater
- `GET /api/run/{workflow_id}/windows` powers the Agent Wall (live 3×3 grid)

UI:
- Open `http://localhost:8000` to run the agent, watch the Agent Wall, and view snapshot tabs.

## Shared durable state

API and worker use `/data` when mounted, or `DATA_DIR` when configured. Local runs fall back to `app/data`. Snapshot writes replace files atomically so polling never reads a partial JSON document. Storage paths cannot escape this root.

Run dependency-free storage checks from `1115/`: `python -m unittest discover -s tests -v`. Full workflow execution still requires a functioning Temporal service and external provider credentials. The Node entry point is an older placeholder and does not run the research application.
