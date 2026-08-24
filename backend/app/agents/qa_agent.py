"""LLM Q&A Agent — the brain.

Wraps the LLM call using the openai SDK pointed at OpenRouter (or any
OpenAI-compatible endpoint). Model-agnostic: change POSEIDON_MODEL and
POSEIDON_BASE_URL to switch providers with no code changes.
"""

from openai import AsyncOpenAI
from langchain_core.messages import BaseMessage, AIMessage

from app.config import settings

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.poseidon_base_url,
        )
    return _client


def _to_openai_messages(messages: list[BaseMessage]) -> list[dict]:
    """Convert LangChain messages to the openai SDK's dict format."""
    role_map = {
        "system": "system",
        "human": "user",
        "ai": "assistant",
    }
    result = []
    for msg in messages:
        role = role_map.get(msg.type, "user")
        result.append({"role": role, "content": msg.content})
    return result


async def call(messages: list[BaseMessage]) -> str:
    """Send assembled Working Memory to the LLM and return the reply text."""
    client = _get_client()
    openai_msgs = _to_openai_messages(messages)

    response = await client.chat.completions.create(
        model=settings.poseidon_model,
        messages=openai_msgs,
    )

    content = response.choices[0].message.content or ""
    return content.strip()
