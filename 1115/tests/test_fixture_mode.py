import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from pydantic import ValidationError

from app import activities, agent_wall, storage
from app.models import CompanyInput


class FixtureModeTests(unittest.IsolatedAsyncioTestCase):
    async def test_fixture_executes_full_local_activity_chain_without_providers(self):
        company = CompanyInput(
            name="Northstar Labs",
            domain="northstar-labs.invalid",
            mode="fixture",
        )
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            provider_mocks = {
                "policy": AsyncMock(side_effect=AssertionError("SmartBuckets called")),
                "search": AsyncMock(side_effect=AssertionError("Linkup called")),
                "browse": AsyncMock(side_effect=AssertionError("Browser Use called")),
                "claude": AsyncMock(side_effect=AssertionError("Anthropic called")),
                "visual": AsyncMock(side_effect=AssertionError("Freepik called")),
                "store": AsyncMock(side_effect=AssertionError("SmartBuckets called")),
            }
            with (
                patch.object(storage, "DATA_DIR", data_dir),
                patch.object(agent_wall, "RUNS_DIR", data_dir / "runs"),
                patch.object(
                    activities.smartbuckets,
                    "fetch_latest_policy",
                    provider_mocks["policy"],
                ),
                patch.object(
                    activities.linkup, "search_company", provider_mocks["search"]
                ),
                patch.object(
                    activities.browser_use, "extract_page", provider_mocks["browse"]
                ),
                patch.object(
                    activities.anthropic_client,
                    "claude_json_call",
                    provider_mocks["claude"],
                ),
                patch.object(
                    activities.freepik, "fetch_visual_asset", provider_mocks["visual"]
                ),
                patch.object(
                    activities.smartbuckets, "store_json", provider_mocks["store"]
                ),
            ):
                policy = await activities.load_policy(company)
                links = await activities.fetch_company_data_from_linkup(company, policy)
                pages = await activities.browse_and_extract_pages(
                    company, policy, links, "fixture-run-1"
                )
                snapshot = await activities.build_snapshot_with_claude(
                    company, policy, links, pages
                )
                snapshot = await activities.attach_freepik_visual(snapshot)
                snapshot_id = await activities.write_snapshot_to_memory(snapshot)
                await activities.log_run_metrics(snapshot)

                self.assertEqual(policy.version, "fixture-v1")
                self.assertEqual(len(links), 3)
                self.assertEqual(len(pages), 3)
                self.assertEqual(snapshot.mode, "fixture")
                self.assertIn("no Linkup", snapshot.fixture_notice)
                self.assertTrue(storage.read_json(f"snapshots/{snapshot_id}.json"))
                metrics = storage.read_json(f"metrics/{snapshot_id}.json")
                self.assertEqual(metrics["mode"], "fixture")
                self.assertEqual(metrics["num_pages_visited"], 3)
                self.assertEqual(len(agent_wall.list_window_states("fixture-run-1")), 3)
                for mock in provider_mocks.values():
                    mock.assert_not_awaited()

    def test_mode_is_closed_to_known_values(self):
        with self.assertRaises(ValidationError):
            CompanyInput(name="Acme", mode="maybe")


class AgentWallSafetyTests(unittest.TestCase):
    def test_run_identifier_cannot_escape_data_directory(self):
        with self.assertRaises(ValueError):
            agent_wall.list_window_states("../../snapshots")

    def test_browser_renderer_has_no_dynamic_inner_html_sink(self):
        script = (Path(__file__).parents[1] / "app" / "static" / "app.js").read_text()
        self.assertNotIn("innerHTML", script)
        self.assertIn("safeHttpUrl", script)
