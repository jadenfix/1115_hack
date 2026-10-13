import asyncio, tempfile, os, subprocess, uuid
from temporalio.client import Client
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker
from app import activities
from app.workflows import ResearchCompanyWorkflow,SelfLearningWorkflow
from unittest.mock import AsyncMock, patch
from app.models import CompanyInput, LinkupResult
from app.converter import data_converter
async def main():
 os.makedirs("data",exist_ok=True)
 server=subprocess.Popen([os.environ.get('TEMPORAL_CLI','temporal'),'server','start-dev','--headless','--port','7329','--db-filename',os.environ.get('TEMPORAL_TEST_DB','data/temporal-test.db')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 try:
  client = None
  for _ in range(60):
   if server.poll() is not None:
    raise RuntimeError("Temporal server exited before becoming ready")
   try:
    client=await Client.connect('127.0.0.1:7329',data_converter=data_converter)
    break
   except Exception:
    await asyncio.sleep(.25)
  if client is None:
   raise TimeoutError("Temporal server was not ready within 15 seconds")
  with patch('app.clients.linkup.search_company', AsyncMock(return_value=[LinkupResult(title='Fixture',url='https://example.org/about',snippet='Fixture data',source='fixture')])):
   async with Worker(client,task_queue='web-e2e',workflows=[ResearchCompanyWorkflow,SelfLearningWorkflow],activities=[getattr(activities,n) for n in ['load_policy','fetch_company_data_from_linkup','browse_and_extract_pages','build_snapshot_with_claude','attach_freepik_visual','write_snapshot_to_memory','log_run_metrics','fetch_recent_metrics_from_memory','propose_new_policy_with_claude','save_new_policy']]):
    result=await asyncio.wait_for(client.execute_workflow(ResearchCompanyWorkflow.run,CompanyInput(name='Fixture Acme'),id='web-research-'+str(uuid.uuid4()),task_queue='web-e2e'),timeout=30)
    from app import storage
    saved=storage.read_json(f'snapshots/{result}.json')
    assert saved and len(saved['pages']) == 1
    print('RESEARCH_COMPLETED',result)
    result2=await asyncio.wait_for(client.execute_workflow(SelfLearningWorkflow.run,id='web-learn-'+str(uuid.uuid4()),task_queue='web-e2e'),timeout=30)
    assert storage.read_json('policy/latest.json')['version'] == result2
    print('LEARNING_COMPLETED',result2)
 finally:
  if server.poll() is None:
   server.terminate()
  try:
   server.wait(timeout=10)
  except subprocess.TimeoutExpired:
   server.kill()
   server.wait(timeout=10)
asyncio.run(main())
