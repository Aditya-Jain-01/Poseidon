"""LLM Provider Manager — Multi-provider client abstraction with per-agent assignment.

Sprint 4 (Person A):
- Supports Local (Ollama), Cloud Free (OpenRouter), Cloud Paid (OpenAI/Codex), and Custom endpoints.
- Allows any agent to be assigned to any provider dynamically without hardcoded locks.
- Persists user preferences to `memory-store/llm_config.json`.
- Provides connection health verification.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from openai import AsyncOpenAI

from app.config import settings

DEFAULT_PROVIDERS: dict[str, dict[str, Any]] = {
    "local": {
      "base_url": "http://localhost:11434/v1",
      "api_key": "ollama",
      "default_model": "llama3.2"
    },
    "cloud_free": {
      "base_url": "https://integrate.api.nvidia.com/v1",
      "api_key_env": "NVIDIA_API_KEY",
      "default_model": "nvidia/nemotron-3-ultra-550b-a55b"
    },
    "cloud_paid": {
      "base_url": "https://api.openai.com/v1",
      "api_key_env": "KRAKEN_API_KEY",
      "default_model": "gpt-5.4-medium"
    },
    "custom": {
      "base_url": "https://integrate.api.nvidia.com/v1",
      "api_key": "",
      "default_model": "nvidia/nemotron-3-ultra-550b-a55b"
    }
}

DEFAULT_AGENT_OVERRIDES: dict[str, dict[str, Any]] = {
    "octavious": {"preset": "local"},
    "nereus": {"preset": "cloud_free"},
    "kraken": {"preset": "cloud_free"},
}


class LLMProvider:
    """Manages multi-provider LLM clients and per-agent configuration."""

    def __init__(self) -> None:
        self._config_path: Path = Path(settings.llm_config_path)
        self._clients: dict[str, AsyncOpenAI] = {}
        self._providers: dict[str, dict[str, Any]] = {}
        self._agent_overrides: dict[str, dict[str, Any]] = {}
        self.load_config()

    def _get_env_key(self, env_var_name: str) -> str:
        """Resolve an API key from settings or OS environment."""
        if not env_var_name:
            return ""
        if env_var_name == "OPENROUTER_API_KEY" and settings.openrouter_api_key:
            return settings.openrouter_api_key
        if env_var_name == "NVIDIA_API_KEY" and settings.nvidia_api_key:
            return settings.nvidia_api_key
        if env_var_name == "KRAKEN_API_KEY" and settings.kraken_api_key:
            return settings.kraken_api_key
        return os.environ.get(env_var_name, "")

    def load_config(self) -> None:
        """Load configuration from disk, creating default if absent."""
        if self._config_path.exists():
            try:
                raw = json.loads(self._config_path.read_text(encoding="utf-8"))
                self._providers = raw.get("providers", DEFAULT_PROVIDERS)
                self._agent_overrides = raw.get("agent_overrides", DEFAULT_AGENT_OVERRIDES)
                return
            except Exception as e:
                print(f"[LLMProvider] Error reading {self._config_path}: {e}. Falling back to defaults.")

        self._providers = {k: dict(v) for k, v in DEFAULT_PROVIDERS.items()}
        self._agent_overrides = {k: dict(v) for k, v in DEFAULT_AGENT_OVERRIDES.items()}
        self.save_config()

    def save_config(self) -> None:
        """Write current LLM configuration to disk."""
        try:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "providers": self._providers,
                "agent_overrides": self._agent_overrides,
            }
            self._config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[LLMProvider] Error saving {self._config_path}: {e}")

    def get_agent_resolved_config(self, agent_id: str) -> dict[str, Any]:
        """Resolve full connection parameters for an agent."""
        override = self._agent_overrides.get(agent_id.lower(), {})
        preset = override.get("preset")

        # Fallback to soul.md default preset if not explicitly overridden
        if not preset:
            from app.soul import soul_store
            agent = soul_store.get_agent(agent_id)
            preset = agent.get("model_preset", "cloud_free") if agent else "cloud_free"

        provider_def = self._providers.get(preset, self._providers.get("cloud_free", {}))

        base_url = override.get("base_url") or provider_def.get("base_url") or settings.poseidon_base_url
        model = override.get("model") or provider_def.get("default_model") or settings.poseidon_model

        # Determine API key
        api_key = override.get("api_key")
        if not api_key:
            env_var = provider_def.get("api_key_env", "")
            if env_var:
                api_key = self._get_env_key(env_var)
            else:
                api_key = provider_def.get("api_key", "")

        # Fallback for local ollama
        if preset == "local" and not api_key:
            api_key = "ollama"

        return {
            "agent_id": agent_id.lower(),
            "preset": preset,
            "base_url": base_url.rstrip("/"),
            "model": model,
            "api_key": api_key,
            "has_api_key": bool(api_key),
        }

    def get_client(self, agent_id: str) -> AsyncOpenAI:
        """Get or initialize an AsyncOpenAI client configured for the agent."""
        conf = self.get_agent_resolved_config(agent_id)
        cache_key = f"{conf['base_url']}::{conf['api_key']}"

        if cache_key not in self._clients:
            self._clients[cache_key] = AsyncOpenAI(
                api_key=conf["api_key"] or "none",
                base_url=conf["base_url"],
            )

        return self._clients[cache_key]

    def get_model(self, agent_id: str) -> str:
        """Get the configured LLM model string for an agent."""
        conf = self.get_agent_resolved_config(agent_id)
        return conf["model"]

    def update_provider(
        self,
        agent_id: str,
        preset: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Update provider assignment and overrides for an agent."""
        aid = agent_id.lower()
        if aid not in self._agent_overrides:
            self._agent_overrides[aid] = {}

        if preset is not None:
            self._agent_overrides[aid]["preset"] = preset
        if base_url is not None:
            self._agent_overrides[aid]["base_url"] = base_url.rstrip("/")
        if api_key is not None:
            self._agent_overrides[aid]["api_key"] = api_key
        if model is not None:
            self._agent_overrides[aid]["model"] = model

        self.save_config()
        return self.get_agent_resolved_config(aid)

    async def check_availability(self, agent_id: str) -> dict[str, Any]:
        """Check whether the agent's configured LLM provider endpoint is reachable."""
        conf = self.get_agent_resolved_config(agent_id)
        client = self.get_client(agent_id)

        try:
            # Quick timeout check using models.list
            import asyncio
            await asyncio.wait_for(client.models.list(), timeout=4.0)
            return {
                "agent_id": agent_id,
                "available": True,
                "status": "online",
                "preset": conf["preset"],
                "model": conf["model"],
                "base_url": conf["base_url"],
                "message": f"Successfully connected to {conf['preset']} provider ({conf['model']})",
            }
        except Exception as e:
            err_msg = str(e)
            if "Connection refused" in err_msg or "Cannot connect" in err_msg or "All connection attempts failed" in err_msg:
                detail = f"Cannot reach endpoint at {conf['base_url']}. If using Ollama, ensure it is running."
            elif "401" in err_msg or "Unauthorized" in err_msg or "Invalid API Key" in err_msg:
                detail = "Authentication failed: missing or invalid API key."
            else:
                detail = f"Endpoint responded with error: {err_msg[:120]}"

            return {
                "agent_id": agent_id,
                "available": False,
                "status": "offline",
                "preset": conf["preset"],
                "model": conf["model"],
                "base_url": conf["base_url"],
                "message": detail,
            }

    def get_all_configs(self) -> dict[str, Any]:
        """Return safe view of all provider configs for UI display."""
        from app.soul import soul_store

        agents_data: dict[str, Any] = {}
        for agent in soul_store.load_all_agents():
            aid = agent["id"]
            conf = self.get_agent_resolved_config(aid)
            agents_data[aid] = {
                "agent_id": aid,
                "display_name": agent["display_name"],
                "avatar": agent["avatar"],
                "color": agent["color"],
                "preset": conf["preset"],
                "model": conf["model"],
                "base_url": conf["base_url"],
                "has_api_key": conf["has_api_key"],
            }

        return {
            "providers": self._providers,
            "agent_overrides": self._agent_overrides,
            "agents": agents_data,
        }


# Global singleton
llm_provider = LLMProvider()
