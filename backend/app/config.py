"""Poseidon configuration — loads from .env and environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # LLM provider & Multi-Agent keys
    openrouter_api_key: str = Field(default="", description="OpenRouter API key")
    kraken_api_key: str = Field(default="", description="Kraken / OpenAI subscription API key")
    poseidon_model: str = Field("google/gemma-4-31b-it:free", description="Default fallback model identifier")
    poseidon_base_url: str = Field("https://openrouter.ai/api/v1", description="Default fallback OpenAI-compatible base URL")

    # Server
    poseidon_host: str = Field("127.0.0.1")
    poseidon_port: int = Field(8000)

    # Guardrails (enforced in Sprint 3, configured now)
    poseidon_max_iterations: int = Field(5)
    poseidon_max_tool_calls: int = Field(5)
    poseidon_max_approval_requests_per_hour: int = Field(5)
    poseidon_outbound_msg_rate_limit: int = Field(20)
    poseidon_cronjob_approval_timeout_hours: int = Field(12)

    # Memory & Agents
    poseidon_consolidation_threshold: int = Field(30)
    poseidon_db_path: Path = Field(default=_PROJECT_ROOT / "memory-store" / "state.db")
    agents_dir: Path = Field(default=_PROJECT_ROOT / "memory-store" / "agents")
    llm_config_path: Path = Field(default=_PROJECT_ROOT / "memory-store" / "llm_config.json")

    # Embeddings (local sentence-transformers model for vector RAG)
    poseidon_embedding_model: str = Field("all-MiniLM-L6-v2", description="HuggingFace sentence-transformers model name")
    poseidon_embedding_dim: int = Field(384, description="Embedding vector dimension (must match the chosen model)")

    model_config = {
        "env_file": str(_PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def load_guardrails_doc() -> str:
    """Load GUARDRAILS.md from the project root. Returns empty string if missing."""
    path = _PROJECT_ROOT / "GUARDRAILS.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# Singleton — import this from anywhere
settings = Settings()
guardrails_doc = load_guardrails_doc()
