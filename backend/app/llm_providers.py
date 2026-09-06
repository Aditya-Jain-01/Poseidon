"""LLM Provider Manager — Direct .env provider authority with dynamic overrides.

Resolves all LLM clients, base URLs, models, and API keys directly from
Poseidon's environment configuration (.env), supporting per-agent presets
and local Ollama / cloud endpoints.
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
        "default_model": "llama3.2",
    },
    "cloud_free": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env": "NVIDIA_API_KEY",
        "default_model": "nvidia/nemotron-3-ultra-550b-a55b",
    },
    "cloud_paid": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "KRAKEN_API_KEY",
        "default_model": "gpt-5.4-medium",
    },
    "custom": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key": "",
        "default_model": "nvidia/nemotron-3-ultra-550b-a55b",
    },
}

DEFAULT_AGENT_OVERRIDES: dict[str, dict[str, Any]] = {
    "poseidon": {"preset": "env"},
    "octavious": {"preset": "local"},
    "nereus": {"preset": "cloud_free"},
    "kraken": {"preset": "cloud_free"},
}


class LLMProvider:
    """Manages LLM clients configured directly from environment variables (.env)."""

    def __init__(self) -> None:
        self._config_path: Path = Path(settings.llm_config_path)
        self._clients: dict[str, AsyncOpenAI] = {}
        self._providers: dict[str, dict[str, Any]] = {k: dict(v) for k, v in DEFAULT_PROVIDERS.items()}
        self._agent_overrides: dict[str, dict[str, Any]] = {k: dict(v) for k, v in DEFAULT_AGENT_OVERRIDES.items()}
        self.load_config()

    def _get_api_key(self, env_var_name: str | None = None) -> str:
        """Resolve API key directly from settings (.env) or OS environment."""
        if env_var_name:
            if env_var_name == "OPENROUTER_API_KEY" and settings.openrouter_api_key:
                return settings.openrouter_api_key
            if env_var_name == "NVIDIA_API_KEY" and settings.nvidia_api_key:
                return settings.nvidia_api_key
            if env_var_name == "KRAKEN_API_KEY" and settings.kraken_api_key:
                return settings.kraken_api_key
            if env_var_name == "POSEIDON_API_KEY" and getattr(settings, "poseidon_api_key", ""):
                return settings.poseidon_api_key
            return os.environ.get(env_var_name, "")

        if getattr(settings, "poseidon_api_key", ""):
            return settings.poseidon_api_key
        if settings.openrouter_api_key:
            return settings.openrouter_api_key
        if settings.nvidia_api_key:
            return settings.nvidia_api_key
        if settings.kraken_api_key:
            return settings.kraken_api_key
        return (
            os.environ.get("OPENROUTER_API_KEY")
            or os.environ.get("POSEIDON_API_KEY")
            or os.environ.get("GROQ_API_KEY")
            or os.environ.get("KRAKEN_API_KEY")
            or os.environ.get("NVIDIA_API_KEY")
            or ""
        )

    def _get_env_key(self, env_var_name: str) -> str:
        """Resolve an API key by environment variable name."""
        return self._get_api_key(env_var_name)

    def load_config(self) -> None:
        """Load configuration from disk if present."""
        if hasattr(self, "_config_path") and self._config_path.exists():
            try:
                raw = json.loads(self._config_path.read_text(encoding="utf-8"))
                if "providers" in raw and isinstance(raw["providers"], dict):
                    self._providers.update(raw["providers"])
                if "agent_overrides" in raw and isinstance(raw["agent_overrides"], dict):
                    self._agent_overrides.update(raw["agent_overrides"])
            except Exception as e:
                print(f"[LLMProvider] Error reading {self._config_path}: {e}. Falling back to defaults.")

    def save_config(self) -> None:
        """Write current LLM configuration to disk."""
        try:
            if hasattr(self, "_config_path") and self._config_path:
                self._config_path.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    "providers": self._providers,
                    "agent_overrides": self._agent_overrides,
                }
                self._config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[LLMProvider] Error saving {self._config_path}: {e}")

    def get_agent_resolved_config(self, agent_id: str = "poseidon") -> dict[str, Any]:
        """Resolve full connection parameters for an agent from .env or overrides."""
        aid = agent_id.lower()
        override = self._agent_overrides.get(aid, {})
        preset = override.get("preset")

        # Fallback to soul.md default preset if not explicitly overridden
        if not preset and aid != "poseidon":
            from app.soul import soul_store
            agent = soul_store.get_agent(aid)
            if agent:
                preset = agent.get("model_preset")

        provider_def = self._providers.get(preset, {}) if preset and preset != "env" else {}

        base_url = (
            override.get("base_url")
            or provider_def.get("base_url")
            or settings.poseidon_base_url
        ).rstrip("/")

        model = (
            override.get("model")
            or provider_def.get("default_model")
            or settings.poseidon_model
        )

        # Determine API key
        api_key = override.get("api_key")
        if not api_key:
            env_var = provider_def.get("api_key_env", "")
            if env_var:
                api_key = self._get_api_key(env_var)
            else:
                api_key = provider_def.get("api_key") or self._get_api_key()

        # Fallback for local ollama if key is not needed
        if preset == "local" or "localhost" in base_url or "11434" in base_url:
            api_key = api_key or "ollama"

        return {
            "agent_id": aid,
            "preset": preset or "env",
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
        """Get the configured LLM model string from .env or override."""
        conf = self.get_agent_resolved_config(agent_id)
        return conf.get("model") or settings.poseidon_model

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

    async def check_availability(self, agent_id: str = "poseidon") -> dict[str, Any]:
        """Check whether the configured LLM endpoint is reachable."""
        conf = self.get_agent_resolved_config(agent_id)
        client = self.get_client(agent_id)

        try:
            import asyncio
            await asyncio.wait_for(client.models.list(), timeout=5.0)
            return {
                "agent_id": agent_id,
                "available": True,
                "status": "online",
                "preset": conf["preset"],
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
                "preset": conf["preset"],
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
            agent_conf = self.get_agent_resolved_config(aid)
            agents_data[aid] = {
                "agent_id": aid,
                "display_name": agent["display_name"],
                "avatar": agent["avatar"],
                "color": agent["color"],
                "preset": agent_conf["preset"],
                "model": agent_conf["model"],
                "base_url": agent_conf["base_url"],
                "has_api_key": agent_conf["has_api_key"],
            }

        providers_dict = {
            "env": {
                "base_url": conf["base_url"],
                "default_model": conf["model"],
            }
        }
        providers_dict.update(self._providers)

        return {
            "providers": providers_dict,
            "agent_overrides": self._agent_overrides,
            "agents": agents_data,
        }


# Global singleton
llm_provider = LLMProvider()
