import unittest
from datetime import datetime, timezone
from app.converter import data_converter
from app.models import CompanyInput, CompanySnapshot, LinkupResult

class ConverterTests(unittest.IsolatedAsyncioTestCase):
    async def test_snapshot_roundtrips_typed_datetime_and_urls(self):
        snapshot = CompanySnapshot(snapshot_id='one', company=CompanyInput(name='Acme'),
            created_at=datetime.now(timezone.utc), policy_version='v1',
            linkup_results=[LinkupResult(title='Example',url='https://example.org/about',snippet='Fixture',source='fixture')],
            pages=[], brief_md='Fixture', outreach_message='Fixture')
        encoded = await data_converter.encode([snapshot])
        decoded = await data_converter.decode(encoded, [CompanySnapshot])
        self.assertEqual(decoded[0], snapshot)
