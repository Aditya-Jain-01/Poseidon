"""Poseidon configuration — loads from .env and environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


# Resolved once at import so .env and memory-store paths are relative to the project
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    openrouter_api_key: str = Field(default="", description="OpenRouter API key")
    nvidia_api_key: str = Field(default="", description="NVIDIA NIM API key")
    kraken_api_key: str = Field(default="", description="Kraken / OpenAI subscription API key")
    poseidon_api_key: str = Field(default="", description="Direct Poseidon fallback API key")
    poseidon_model: str = Field("nvidia/nemotron-3-ultra-550b-a55b", description="Default fallback model identifier")
    poseidon_base_url: str = Field("https://integrate.api.nvidia.com/v1", description="Default fallback OpenAI-compatible base URL")

    poseidon_host: str = Field("127.0.0.1")
    poseidon_port: int = Field(8000)

    poseidon_max_iterations: int = Field(5)
    poseidon_max_tool_calls: int = Field(5)
    poseidon_max_approval_requests_per_hour: int = Field(5)
    poseidon_outbound_msg_rate_limit: int = Field(20)
    poseidon_cronjob_approval_timeout_hours: int = Field(12)

    poseidon_note_max_length: int = Field(500, description="Max character length for a single note/reminder.")
    poseidon_note_max_total: int = Field(500, description="Max total notes + reminders in storage.")

    poseidon_operator_pin: str = Field(default="", description="Optional operator PIN for step-up approval verification.")

    telegram_bot_token: str = Field(default="", description="Telegram Bot API Token")
    telegram_allowed_user_ids: str = Field(default="", description="Comma-separated allowed Telegram user IDs")
    telegram_webhook_secret: str = Field(default="", description="Optional secret token for webhook verification")
    telegram_polling_enabled: bool = Field(default=False, description="Enable local long-polling runner if token present")

    # Consolidation triggers the SummarizerAgent after this many new turns
    poseidon_consolidation_threshold: int = Field(30)
    poseidon_db_path: Path = Field(default=_PROJECT_ROOT / "memory-store" / "state.db")
    agents_dir: Path = Field(default=_PROJECT_ROOT / "memory-store" / "agents")
    llm_config_path: Path = Field(default=_PROJECT_ROOT / "memory-store" / "llm_config.json")

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


settings = Settings()
guardrails_doc = load_guardrails_doc()
