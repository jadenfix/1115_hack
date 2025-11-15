import asyncio
import logging
from datetime import timedelta
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from temporalio.client import Client

from app import storage
from app.agent_wall import list_window_states
from app.activities import fetch_recent_metrics_from_memory, load_policy
from app.config import settings
from app.models import CompanyInput
from app.workflows import ResearchCompanyWorkflow, SelfLearningWorkflow

logger = logging.getLogger(__name__)

app = FastAPI(title="ResearchCompany Orchestrator")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
if Path("/data").exists():
    app.mount("/runs", StaticFiles(directory="/data"), name="runs")


async def get_temporal_client() -> Client:
    return await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)


@app.on_event("startup")
async def startup_event() -> None:
    # Warm up client lazily to surface misconfiguration early in logs.
    try:
        await get_temporal_client()
    except Exception as exc:
        logger.warning("Temporal connection failed on startup: %s", exc)


@app.get("/", response_class=HTMLResponse)
async def serve_ui(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": settings.frontend_title,
        },
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "temporal_host": settings.temporal_address}


@app.post("/api/run_research")
async def start_research(company: CompanyInput) -> dict:
    try:
        client = await get_temporal_client()
        handle = await client.start_workflow(
            ResearchCompanyWorkflow.run,
            company,
            id=f"research-{company.name}-{id(company)}",
            task_queue=settings.temporal_task_queue,
            execution_timeout=timedelta(seconds=settings.workflow_run_timeout_seconds),
        )
        return {"workflow_id": handle.id, "run_id": handle.first_execution_run_id}
    except Exception as exc:
        logger.error("Failed to start ResearchCompanyWorkflow: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to start workflow") from exc


@app.get("/api/run_status")
async def run_status(workflow_id: str = Query(...)) -> dict:
    try:
        client = await get_temporal_client()
        handle = client.get_workflow_handle(workflow_id=workflow_id)
        info = await handle.describe()
        status = info.status.name if hasattr(info.status, "name") else str(info.status)
        response: Dict[str, Optional[str]] = {"status": status, "snapshot_id": None, "error": None}
        if status == "COMPLETED":
            try:
                response["snapshot_id"] = await handle.result()
            except Exception as exc:
                response["error"] = str(exc)
        return response
    except Exception as exc:
        logger.error("Failed to fetch run status: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to fetch status") from exc


@app.get("/api/snapshot/{snapshot_id}")
async def get_snapshot(snapshot_id: str) -> dict:
    local = storage.read_json(f"snapshots/{snapshot_id}.json")
    if local:
        return local
    raise HTTPException(status_code=404, detail="Snapshot not found yet")


@app.get("/api/run/{run_id}/windows")
async def get_run_windows(run_id: str) -> dict:
    windows = list_window_states(run_id)
    return {"items": [w.model_dump() for w in windows]}


@app.get("/api/history")
async def history(limit: int = 20) -> dict:
    metrics = storage.list_json("metrics")
    return {"items": metrics[:limit]}


@app.get("/api/policy")
async def current_policy() -> dict:
    try:
        policy = await load_policy()
        return policy.model_dump()
    except Exception as exc:
        logger.error("Failed to load policy: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to load policy") from exc


@app.get("/api/policy/versions")
async def policy_versions() -> dict:
    versions = storage.list_json("policy")
    return {"items": versions}


@app.post("/api/self_learn")
async def start_self_learning() -> dict:
    try:
        client = await get_temporal_client()
        handle = await client.start_workflow(
            SelfLearningWorkflow.run,
            id=f"self-learn-{id(asyncio)}",
            task_queue=settings.temporal_task_queue,
            execution_timeout=timedelta(seconds=120),
        )
        return {"workflow_id": handle.id, "run_id": handle.first_execution_run_id}
    except Exception as exc:
        logger.error("Failed to start SelfLearningWorkflow: %s", exc)
        raise HTTPException(status_code=500, detail="Unable to start self-learning workflow") from exc
