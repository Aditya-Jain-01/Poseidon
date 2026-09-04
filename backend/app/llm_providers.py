"""LLM Provider Manager — Direct .env provider authority.

Resolves all LLM clients, base URLs, models, and API keys directly from
Poseidon's environment configuration (.env). No hidden json file overrides.
"""

from __future__ import annotations

import os
from typing import Any
from openai import AsyncOpenAI

from app.config import settings

<<<<<<< Updated upstream
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

=======
>>>>>>> Stashed changes

class LLMProvider:
    """Manages LLM clients configured directly from environment variables (.env)."""

    def __init__(self) -> None:
        self._clients: dict[str, AsyncOpenAI] = {}

    def _get_api_key(self) -> str:
        """Resolve API key directly from settings (.env) or OS environment."""
        if settings.openrouter_api_key:
            return settings.openrouter_api_key
<<<<<<< Updated upstream
        if env_var_name == "NVIDIA_API_KEY" and settings.nvidia_api_key:
            return settings.nvidia_api_key
        if env_var_name == "KRAKEN_API_KEY" and settings.kraken_api_key:
            return settings.kraken_api_key
        return os.environ.get(env_var_name, "")
=======
        return (
            os.environ.get("OPENROUTER_API_KEY")
            or os.environ.get("GROQ_API_KEY")
            or os.environ.get("KRAKEN_API_KEY")
            or ""
        )
>>>>>>> Stashed changes

    def get_agent_resolved_config(self, agent_id: str = "poseidon") -> dict[str, Any]:
        """Resolve connection parameters purely from .env."""
        api_key = self._get_api_key()
        base_url = settings.poseidon_base_url.rstrip("/")
        model = settings.poseidon_model

<<<<<<< Updated upstream
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
=======
        # Fallback for local ollama if key is not needed
        if "localhost" in base_url or "11434" in base_url:
            api_key = api_key or "ollama"
>>>>>>> Stashed changes

        return {
            "agent_id": agent_id.lower(),
            "preset": "env",
            "base_url": base_url,
            "model": model,
            "api_key": api_key,
            "has_api_key": bool(api_key),
        }

    def get_client(self, agent_id: str = "poseidon") -> AsyncOpenAI:
        """Get or initialize an AsyncOpenAI client configured from .env."""
        conf = self.get_agent_resolved_config(agent_id)
        cache_key = f"{conf['base_url']}::{conf['api_key']}"

        if cache_key not in self._clients:
            self._clients[cache_key] = AsyncOpenAI(
                api_key=conf["api_key"] or "none",
                base_url=conf["base_url"],
            )

        return self._clients[cache_key]

    def get_model(self, agent_id: str = "poseidon") -> str:
        """Get the configured LLM model string from .env."""
        return settings.poseidon_model

    def update_provider(
        self,
        agent_id: str,
        preset: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> dict[str, Any]:
        """Returns the active .env configuration (runtime overrides disabled)."""
        return self.get_agent_resolved_config(agent_id)

    async def check_availability(self, agent_id: str = "poseidon") -> dict[str, Any]:
        """Check whether the configured LLM endpoint from .env is reachable."""
        conf = self.get_agent_resolved_config(agent_id)
        client = self.get_client(agent_id)

        try:
            import asyncio
            await asyncio.wait_for(client.models.list(), timeout=5.0)
            return {
                "agent_id": agent_id,
                "available": True,
                "status": "online",
                "preset": "env",
                "model": conf["model"],
                "base_url": conf["base_url"],
                "message": f"Successfully connected to endpoint ({conf['model']})",
            }
        except Exception as e:
            err_msg = str(e)
            if "Connection refused" in err_msg or "Cannot connect" in err_msg or "All connection attempts failed" in err_msg:
                detail = f"Cannot reach endpoint at {conf['base_url']}. Verify network or local runner."
            elif "401" in err_msg or "Unauthorized" in err_msg or "Invalid API Key" in err_msg:
                detail = "Authentication failed: missing or invalid API key in .env."
            elif "404" in err_msg or "model_not_found" in err_msg:
                detail = f"Model '{conf['model']}' not found at {conf['base_url']}. Check model name in .env."
            else:
                detail = f"Endpoint error: {err_msg[:140]}"

            return {
                "agent_id": agent_id,
                "available": False,
                "status": "offline",
                "preset": "env",
                "model": conf["model"],
                "base_url": conf["base_url"],
                "message": detail,
            }

    def get_all_configs(self) -> dict[str, Any]:
        """Return safe view of .env provider config for UI display."""
        from app.soul import soul_store

        conf = self.get_agent_resolved_config("poseidon")
        agents_data: dict[str, Any] = {}
        for agent in soul_store.load_all_agents():
            aid = agent["id"]
            agents_data[aid] = {
                "agent_id": aid,
                "display_name": agent["display_name"],
                "avatar": agent["avatar"],
                "color": agent["color"],
                "preset": "env",
                "model": conf["model"],
                "base_url": conf["base_url"],
                "has_api_key": conf["has_api_key"],
            }

        return {
            "providers": {
                "env": {
                    "base_url": conf["base_url"],
                    "default_model": conf["model"],
                }
            },
            "agent_overrides": {},
            "agents": agents_data,
        }


# Global singleton
llm_provider = LLMProvider()
