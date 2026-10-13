import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from temporalio import workflow
from app.models import CompanyInput
from app.workflows import ResearchCompanyWorkflow, SelfLearningWorkflow

ACTIVITY_SIGNATURE = inspect.signature(workflow.execute_activity)

class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_research_activity_dispatch_matches_sdk(self):
        calls = []
        results = iter(['policy', ['links'], ['pages'], 'snapshot', 'visual', 'snapshot-id', None])
        async def dispatch(*args, **kwargs):
            ACTIVITY_SIGNATURE.bind(*args, **kwargs)
            calls.append((args, kwargs))
            return next(results)
        company = CompanyInput(name='Acme')
        with patch('app.workflows.workflow.execute_activity', side_effect=dispatch), patch('app.workflows.workflow.info', return_value=SimpleNamespace(workflow_id='research-1')):
            self.assertEqual(await ResearchCompanyWorkflow().run(company), 'snapshot-id')
        self.assertEqual(len(calls), 7)
        self.assertEqual(calls[1][1]['args'], [company, 'policy'])
        self.assertEqual(calls[2][1]['args'], [company, 'policy', ['links'], 'research-1'])
        self.assertEqual(calls[3][1]['args'], [company, 'policy', ['links'], ['pages']])

    async def test_learning_activity_dispatch_matches_sdk(self):
        calls = []
        results = iter([['metrics'], 'policy', 'new-policy', 'v2'])
        async def dispatch(*args, **kwargs):
            ACTIVITY_SIGNATURE.bind(*args, **kwargs)
            calls.append((args, kwargs))
            return next(results)
        with patch('app.workflows.workflow.execute_activity', side_effect=dispatch):
            self.assertEqual(await SelfLearningWorkflow().run(), 'v2')
        self.assertEqual(calls[2][1]['args'], ['policy', ['metrics']])

    async def test_learning_requests_get_unique_ids(self):
        from app.main import start_self_learning
        client = SimpleNamespace(start_workflow=AsyncMock(return_value=SimpleNamespace(id='id', first_execution_run_id='run')))
        with patch('app.main.get_temporal_client', AsyncMock(return_value=client)):
            await start_self_learning()
            await start_self_learning()
        ids = [c.kwargs['id'] for c in client.start_workflow.call_args_list]
        self.assertNotEqual(*ids)
