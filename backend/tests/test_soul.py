"""Unit tests for SoulStore and drop-in *.soul.md agent system (Sprint 4 — Person A)."""

import gc
import tempfile
import unittest
from pathlib import Path

from app.soul import SoulStore, _parse_frontmatter, _dump_frontmatter, PREBUILT_IDS, MAX_CUSTOM_AGENTS
import app.soul as soul_module


class TestSoulStore(unittest.TestCase):
    """Test suite for drop-in agent souls and lifecycle management."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.test_agents_dir = Path(self.tmpdir.name) / "agents"
        self.test_agents_dir.mkdir(parents=True, exist_ok=True)

        # Seed prebuilt agents in test dir
        (self.test_agents_dir / "octavious.soul.md").write_text(
            "---\ndisplay_name: Octavious\navatar: O\ncolor: \"#39ff14\"\nrole: Personal assistant\n"
            "model_preset: local\ntools:\n  - crm_read\n  - crm_write\nrouting_signals:\n  - default\n  - remind\n"
            "is_prebuilt: true\n---\n# Octavious Persona\n\nWarm and concise right hand.",
            encoding="utf-8",
        )
        (self.test_agents_dir / "nereus.soul.md").write_text(
            "---\ndisplay_name: Nereus\navatar: N\ncolor: \"#00bfff\"\nrole: Research agent\n"
            "model_preset: cloud_free\ntools:\n  - notes_reminders_create\nrouting_signals:\n  - research\n"
            "is_prebuilt: true\n---\n# Nereus Persona\n\nDeep-dive research oracle.",
            encoding="utf-8",
        )
        (self.test_agents_dir / "kraken.soul.md").write_text(
            "---\ndisplay_name: Kraken\navatar: K\ncolor: \"#ff4500\"\nrole: POC builder\n"
            "model_preset: cloud_free\ntools: []\nrouting_signals:\n  - write code\n"
            "is_prebuilt: true\n---\n# Kraken Persona\n\nRelentless code builder.",
            encoding="utf-8",
        )

        self._orig_agents_dir_fn = soul_module._get_agents_dir
        soul_module._get_agents_dir = lambda: self.test_agents_dir

        self.store = SoulStore()
        self.store.reload()

    def tearDown(self):
        soul_module._get_agents_dir = self._orig_agents_dir_fn
        del self.store
        gc.collect()
        self.tmpdir.cleanup()

    def test_load_all_prebuilt_agents(self):
        """Verify prebuilt agents load in order with correct metadata."""
        agents = self.store.load_all_agents()
        self.assertGreaterEqual(len(agents), 3)

        agent_ids = [a["id"] for a in agents[:3]]
        self.assertEqual(agent_ids, ["octavious", "nereus", "kraken"])

        octavious = self.store.get_agent("octavious")
        self.assertIsNotNone(octavious)
        self.assertEqual(octavious["display_name"], "Octavious")
        self.assertEqual(octavious["model_preset"], "local")
        self.assertIn("crm_read", octavious["tools"])
        self.assertTrue(octavious["is_prebuilt"])

    def test_routing_signals_aggregation(self):
        """Verify signals are aggregated across all agents."""
        signals = self.store.get_routing_signals()
        self.assertEqual(signals.get("default"), "octavious")
        self.assertEqual(signals.get("remind"), "octavious")
        self.assertEqual(signals.get("research"), "nereus")
        self.assertEqual(signals.get("write code"), "kraken")

    def test_create_and_delete_custom_agent(self):
        """Verify creation, retrieval, and deletion of custom agents."""
        config = {
            "id": "triton",
            "display_name": "Triton",
            "avatar": "T",
            "color": "#38bdf8",
            "role": "Messenger Agent",
            "description": "Broadcasts marine notifications",
            "model_preset": "cloud_free",
            "tools": ["notes_reminders_read"],
            "routing_signals": ["broadcast", "notify"],
            "personality": "# Triton\n\nMessenger of the depths.",
        }

        created = self.store.create_agent(config)
        self.assertEqual(created["id"], "triton")
        self.assertFalse(created["is_prebuilt"])
        self.assertTrue((self.test_agents_dir / "triton.soul.md").exists())

        # Verify retrieval
        agent = self.store.get_agent("triton")
        self.assertIsNotNone(agent)
        self.assertEqual(agent["role"], "Messenger Agent")

        # Verify deletion
        success = self.store.delete_agent("triton")
        self.assertTrue(success)
        self.assertIsNone(self.store.get_agent("triton"))
        self.assertFalse((self.test_agents_dir / "triton.soul.md").exists())

    def test_custom_agent_limit_enforced(self):
        """Ensure maximum of 2 custom agents is strictly enforced."""
        self.store.create_agent({"id": "custom1", "display_name": "Custom 1"})
        self.store.create_agent({"id": "custom2", "display_name": "Custom 2"})

        with self.assertRaises(ValueError) as ctx:
            self.store.create_agent({"id": "custom3", "display_name": "Custom 3"})

        self.assertIn("Maximum limit", str(ctx.exception))

    def test_prevent_prebuilt_deletion(self):
        """Ensure prebuilt agents cannot be deleted."""
        with self.assertRaises(ValueError) as ctx:
            self.store.delete_agent("octavious")

        self.assertIn("Cannot delete prebuilt agent", str(ctx.exception))

    def test_update_agent(self):
        """Ensure updates modify the soul file while preserving prebuilt flag."""
        updated = self.store.update_agent(
            "octavious",
            {"description": "Updated assistant description", "model_preset": "cloud_free"},
        )
        self.assertEqual(updated["description"], "Updated assistant description")
        self.assertEqual(updated["model_preset"], "cloud_free")
        self.assertTrue(updated["is_prebuilt"])

    def test_build_system_prompt(self):
        """Verify prompt generation returns the markdown persona."""
        prompt = self.store.build_system_prompt("nereus")
        self.assertIn("Nereus Persona", prompt)
        self.assertIn("Deep-dive research oracle", prompt)


if __name__ == "__main__":
    unittest.main()
