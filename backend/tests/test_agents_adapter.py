"""Integration tests for Agents & Trajectory API endpoints (Sprint 4 — Person C)."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.soul import SoulStore
import app.gateway.agents_adapter as agents_adapter_module
from app.orchestration.trajectory import trajectory_store


class TestAgentsAdapterAPI(unittest.TestCase):
    """Test suite for agent management, LLM settings, and trajectory REST endpoints."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.agents_dir = Path(self.tmpdir.name) / "agents"
        self.agents_dir.mkdir(parents=True, exist_ok=True)

        # Seed prebuilt souls
        for pid, name in [("poseidon", "Poseidon"), ("nereus", "Nereus"), ("kraken", "Kraken")]:
            soul_file = self.agents_dir / f"{pid}.soul.md"
            soul_file.write_text(
                f"---\ndisplay_name: {name}\navatar: {name[0]}\nrole: Test Role\nis_prebuilt: true\n---\n# {name}\n\nPersona",
                encoding="utf-8",
            )

        self.soul_store = SoulStore()
        # Patch soul_store in agents_adapter
        self._orig_soul = agents_adapter_module.soul_store
        agents_adapter_module.soul_store = self.soul_store

        self._patcher = patch("app.soul._get_agents_dir", return_value=self.agents_dir)
        self._patcher.start()

        self.client = TestClient(app)

    def tearDown(self):
        self._patcher.stop()
        agents_adapter_module.soul_store = self._orig_soul
        self.tmpdir.cleanup()

    def test_list_agents(self):
        res = self.client.get("/agents")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data), 3)
        ids = [a["id"] for a in data]
        self.assertIn("poseidon", ids)
        self.assertIn("nereus", ids)
        self.assertIn("kraken", ids)

    def test_get_agent_success_and_404(self):
        res = self.client.get("/agents/poseidon")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["display_name"], "Poseidon")

        res404 = self.client.get("/agents/nonexistent_agent")
        self.assertEqual(res404.status_code, 404)

    def test_create_and_delete_custom_agent(self):
        payload = {
            "display_name": "Proteus",
            "avatar": "P",
            "color": "#a855f7",
            "role": "Shape Shifter",
            "description": "Flexible helper",
            "personality": "# Proteus\n\nYou adapt.",
            "model_preset": "cloud_free",
            "tools": ["notes_reminders_read"],
            "routing_signals": ["adapt", "shape"],
        }
        res = self.client.post("/agents", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["id"], "proteus")
        self.assertFalse(data["is_prebuilt"])

        # Update custom agent
        update_res = self.client.put("/agents/proteus", json={"role": "Senior Shape Shifter"})
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["role"], "Senior Shape Shifter")

        # Deleting prebuilt should fail with 400
        del_prebuilt = self.client.delete("/agents/poseidon")
        self.assertEqual(del_prebuilt.status_code, 400)

        # Deleting custom should succeed
        del_res = self.client.delete("/agents/proteus")
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(del_res.json()["status"], "deleted")

    def test_llm_settings_endpoints(self):
        res = self.client.get("/settings/llm")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("providers", data)
        self.assertIn("agents", data)

        # Update an agent's provider
        put_res = self.client.put("/settings/llm/poseidon", json={"preset": "local"})
        self.assertEqual(put_res.status_code, 200)
        self.assertEqual(put_res.json()["preset"], "local")

    def test_trajectory_endpoint(self):
        run_id = "test-run-123"
        trajectory_store.record(run_id, "route", agent_id="poseidon")
        trajectory_store.record(run_id, "agent", agent_id="poseidon", tool_calls=0)

        res = self.client.get(f"/runs/{run_id}/trajectory")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["run_id"], run_id)
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["steps"][0]["step_type"], "route")
        self.assertEqual(data["steps"][1]["step_type"], "agent")
