from datetime import timedelta
from typing import List

from temporalio import workflow

from app.activities import (
    attach_freepik_visual,
    browse_and_extract_pages,
    build_snapshot_with_claude,
    fetch_company_data_from_linkup,
    fetch_recent_metrics_from_memory,
    load_policy,
    log_run_metrics,
    propose_new_policy_with_claude,
    save_new_policy,
    write_snapshot_to_memory,
)
from app.config import settings
from app.models import CompanyInput


@workflow.defn
class ResearchCompanyWorkflow:
    @workflow.run
    async def run(self, company: CompanyInput) -> str:
        policy = await workflow.execute_activity(
            load_policy, schedule_to_close_timeout=timedelta(seconds=10)
        )
        linkup_results = await workflow.execute_activity(
            fetch_company_data_from_linkup, company, policy, schedule_to_close_timeout=timedelta(seconds=30)
        )
        page_extractions = await workflow.execute_activity(
            browse_and_extract_pages,
            company,
            policy,
            linkup_results,
            workflow.info().workflow_id,
            schedule_to_close_timeout=timedelta(minutes=5),
        )
        snapshot = await workflow.execute_activity(
            build_snapshot_with_claude,
            company,
            policy,
            linkup_results,
            page_extractions,
            schedule_to_close_timeout=timedelta(seconds=90),
        )
        snapshot_with_visual = await workflow.execute_activity(
            attach_freepik_visual, snapshot, schedule_to_close_timeout=timedelta(seconds=20)
        )
        snapshot_id = await workflow.execute_activity(
            write_snapshot_to_memory, snapshot_with_visual, schedule_to_close_timeout=timedelta(seconds=20)
        )
        await workflow.execute_activity(
            log_run_metrics, snapshot_with_visual, schedule_to_close_timeout=timedelta(seconds=10)
        )
        return snapshot_id


@workflow.defn
class SelfLearningWorkflow:
    @workflow.run
    async def run(self) -> str:
        recent_metrics = await workflow.execute_activity(
            fetch_recent_metrics_from_memory, schedule_to_close_timeout=timedelta(seconds=30)
        )
        current_policy = await workflow.execute_activity(
            load_policy, schedule_to_close_timeout=timedelta(seconds=10)
        )
        new_policy = await workflow.execute_activity(
            propose_new_policy_with_claude,
            current_policy,
            recent_metrics,
            schedule_to_close_timeout=timedelta(seconds=90),
        )
        new_version = await workflow.execute_activity(
            save_new_policy, new_policy, schedule_to_close_timeout=timedelta(seconds=15)
        )
        return new_version
