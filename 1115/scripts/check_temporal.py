"""Run the immutable fixture through a real local Temporal server and worker."""

import asyncio
import os
import tempfile
import uuid
from pathlib import Path

from temporalio.client import Client
from temporalio.worker import Worker

from app import activities, storage
from app.converter import data_converter
from app.fixtures import fixture_company
from app.workflows import ResearchCompanyWorkflow, SelfLearningWorkflow

ADDRESS = "127.0.0.1:7329"


async def connect_with_retry() -> Client:
    for _ in range(80):
        try:
            return await Client.connect(ADDRESS, data_converter=data_converter)
        except RuntimeError:
            await asyncio.sleep(0.25)
    raise RuntimeError("Temporal development server did not become ready")


async def main() -> None:
    temporal_cli = os.environ.get("TEMPORAL_CLI", "temporal")
    with tempfile.TemporaryDirectory(prefix="1115-temporal-") as directory:
        storage.DATA_DIR = Path(directory) / "data"
        activities.update_window_state.__globals__["RUNS_DIR"] = (
            storage.DATA_DIR / "runs"
        )
        server = await asyncio.create_subprocess_exec(
            temporal_cli,
            "server",
            "start-dev",
            "--headless",
            "--port",
            "7329",
            "--db-filename",
            str(Path(directory) / "temporal.db"),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            client = await connect_with_retry()
            task_queue = f"fixture-check-{uuid.uuid4()}"
            worker = Worker(
                client,
                task_queue=task_queue,
                workflows=[ResearchCompanyWorkflow, SelfLearningWorkflow],
                activities=[
                    activities.load_policy,
                    activities.fetch_company_data_from_linkup,
                    activities.browse_and_extract_pages,
                    activities.build_snapshot_with_claude,
                    activities.attach_freepik_visual,
                    activities.write_snapshot_to_memory,
                    activities.log_run_metrics,
                    activities.fetch_recent_metrics_from_memory,
                    activities.propose_new_policy_with_claude,
                    activities.save_new_policy,
                ],
            )
            async with worker:
                snapshot_id = await client.execute_workflow(
                    ResearchCompanyWorkflow.run,
                    fixture_company(),
                    id=f"fixture-{uuid.uuid4()}",
                    task_queue=task_queue,
                )
            snapshot = storage.read_json(f"snapshots/{snapshot_id}.json")
            metrics = storage.read_json(f"metrics/{snapshot_id}.json")
            assert snapshot and snapshot["mode"] == "fixture"
            assert len(snapshot["linkup_results"]) == 3
            assert len(snapshot["pages"]) == 3
            assert metrics and metrics["mode"] == "fixture"
            assert metrics["num_pages_visited"] == 3
            print(
                "REAL_TEMPORAL_FIXTURE_OK",
                f"snapshot={snapshot_id}",
                "links=3 pages=3 providers=0",
            )
        finally:
            server.terminate()
            await server.wait()


if __name__ == "__main__":
    asyncio.run(main())
