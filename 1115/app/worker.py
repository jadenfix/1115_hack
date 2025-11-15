import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from app import activities
from app.config import settings
from app.workflows import ResearchCompanyWorkflow, SelfLearningWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_worker() -> None:
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    executor = ThreadPoolExecutor(max_workers=settings.worker_max_concurrency)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
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
        activity_executor=executor,
    )
    logger.info(
        "Worker started on queue '%s' with max %s activities",
        settings.temporal_task_queue,
        settings.worker_max_concurrency,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
