"""Unit tests for LLMProvider and QA Agent runner (Sprint 4 — Person A)."""

import gc
import json
import tempfile
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from langchain_core.messages import HumanMessage, SystemMessage

from app.llm_providers import LLMProvider, DEFAULT_PROVIDERS, DEFAULT_AGENT_OVERRIDES
from app.agents.qa_agent import call, AgentResult, _to_openai_messages


class TestLLMProviders(unittest.TestCase):
    """Test suite for per-agent LLM providers and the generic agent runner."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.test_cfg_path = Path(self.tmpdir.name) / "llm_config.json"

        # Write test config
        test_payload = {
            "providers": DEFAULT_PROVIDERS,
            "agent_overrides": {
                "octavious": {"preset": "local"},
                "nereus": {"preset": "cloud_free"},
                "kraken": {"preset": "cloud_free"},
            }
        }
        self.test_cfg_path.write_text(json.dumps(test_payload), encoding="utf-8")

        self.provider = LLMProvider()
        self.provider._config_path = self.test_cfg_path
        self.provider.load_config()

    def tearDown(self):
        del self.provider
        gc.collect()
        self.tmpdir.cleanup()

    def test_resolve_default_agent_configs(self):
        """Verify resolved provider endpoints match expectations."""
        oct_conf = self.provider.get_agent_resolved_config("octavious")
        self.assertEqual(oct_conf["preset"], "local")
        self.assertEqual(oct_conf["base_url"], "http://localhost:11434/v1")
        self.assertEqual(oct_conf["model"], "llama3.2")

        nereus_conf = self.provider.get_agent_resolved_config("nereus")
        self.assertEqual(nereus_conf["preset"], "cloud_free")
        self.assertEqual(nereus_conf["base_url"], "https://integrate.api.nvidia.com/v1")
        self.assertEqual(nereus_conf["model"], "nvidia/nemotron-3-ultra-550b-a55b")

    def test_update_agent_provider(self):
        """Verify dynamically reassigning an agent's provider."""
        updated = self.provider.update_provider(
            "octavious",
            preset="cloud_free",
            model="custom-gemma-model",
        )
        self.assertEqual(updated["preset"], "cloud_free")
        self.assertEqual(updated["model"], "custom-gemma-model")

        # Verify persisted to disk
        reloaded = LLMProvider()
        reloaded._config_path = self.test_cfg_path
        reloaded.load_config()
        conf = reloaded.get_agent_resolved_config("octavious")
        self.assertEqual(conf["preset"], "cloud_free")
        self.assertEqual(conf["model"], "custom-gemma-model")

    def test_to_openai_messages_conversion(self):
        """Verify conversion of LangChain messages to OpenAI SDK dict format."""
        messages = [
            SystemMessage(content="System instruction"),
            HumanMessage(content="User query"),
        ]
        converted = _to_openai_messages(messages)
        self.assertEqual(len(converted), 2)
        self.assertEqual(converted[0]["role"], "system")
        self.assertEqual(converted[0]["content"], "System instruction")
        self.assertEqual(converted[1]["role"], "user")
        self.assertEqual(converted[1]["content"], "User query")

    @patch("app.agents.qa_agent.llm_provider")
    async def _run_qa_call_text(self, mock_llm_provider):
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Greetings from Octavious!"
        mock_choice.message.tool_calls = None
        mock_response = MagicMock(choices=[mock_choice])
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        mock_llm_provider.get_client.return_value = mock_client
        mock_llm_provider.get_model.return_value = "llama3.2"

        result = await call(
            agent_id="octavious",
            messages=[HumanMessage(content="Hello!")],
        )

        self.assertIsInstance(result, AgentResult)
        self.assertEqual(result.content, "Greetings from Octavious!")
        self.assertIsNone(result.tool_calls)
        self.assertEqual(str(result), "Greetings from Octavious!")

    def test_qa_agent_call_returns_text(self):
        """Test agent execution returning regular text response."""
        import asyncio
        asyncio.run(self._run_qa_call_text())

    @patch("app.agents.qa_agent.llm_provider")
    async def _run_qa_call_tool(self, mock_llm_provider):
        mock_client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = ""
        mock_tc = MagicMock()
        mock_tc.id = "call_123"
        mock_tc.function.name = "calendar_read"
        mock_tc.function.arguments = json.dumps({"date": "tomorrow"})
        mock_choice.message.tool_calls = [mock_tc]
        mock_response = MagicMock(choices=[mock_choice])
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        mock_llm_provider.get_client.return_value = mock_client
        mock_llm_provider.get_model.return_value = "llama3.2"

        result = await call(
            agent_id="octavious",
            messages=[HumanMessage(content="Check my calendar")],
            tools=[{"type": "function", "function": {"name": "calendar_read"}}],
        )

        self.assertIsInstance(result, AgentResult)
        self.assertIsNotNone(result.tool_calls)
        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0]["name"], "calendar_read")
        self.assertEqual(result.tool_calls[0]["arguments"], {"date": "tomorrow"})

    def test_qa_agent_call_returns_tool_calls(self):
        """Test agent execution returning parsed tool calls."""
        import asyncio
        asyncio.run(self._run_qa_call_tool())


if __name__ == "__main__":
    unittest.main()
