"""Generic Agent Runner — Executes any agent by ID (Poseidon, or custom).

Sprint 4 (Person A):
- Dynamically binds agent persona from `soul_store`.
- Dispatches LLM calls using per-agent provider clients from `llm_provider`.
- Full OpenAI tool/function-calling capability with response parsing.
- Backwards-compatible interface for LangGraph nodes.
"""

from __future__ import annotations

import json
from typing import Any
from langchain_core.messages import BaseMessage, SystemMessage

from app.soul import soul_store
from app.llm_providers import llm_provider


class AgentResult(dict):
    """Structured response containing content and optional tool calls.

    Subclasses dict for backward compatibility with str() and dict operations.
    """

    @property
    def content(self) -> str:
        return self.get("content") or ""

    @property
    def tool_calls(self) -> list[dict[str, Any]] | None:
        return self.get("tool_calls")

    def __str__(self) -> str:
        return self.content


def _to_openai_messages(messages: list[BaseMessage]) -> list[dict[str, Any]]:
    """Convert LangChain messages to OpenAI SDK dict format, supporting tool messages."""
    result: list[dict[str, Any]] = []

    for msg in messages:
        msg_type = getattr(msg, "type", "user")

        if msg_type == "system":
            result.append({"role": "system", "content": str(msg.content)})
        elif msg_type in ("human", "user"):
            result.append({"role": "user", "content": str(msg.content)})
        elif msg_type in ("ai", "assistant"):
            entry: dict[str, Any] = {"role": "assistant", "content": str(msg.content or "")}
            # Preserve tool calls if message had them
            raw_tool_calls = getattr(msg, "tool_calls", None) or getattr(msg, "additional_kwargs", {}).get("tool_calls")
            if raw_tool_calls:
                entry["tool_calls"] = raw_tool_calls
            result.append(entry)
        elif msg_type == "tool":
            result.append({
                "role": "tool",
                "tool_call_id": getattr(msg, "tool_call_id", getattr(msg, "name", "call")),
                "content": str(msg.content),
            })
        else:
            result.append({"role": "user", "content": str(msg.content)})

    return result


def _inject_agent_soul(agent_id: str, messages: list[BaseMessage]) -> list[BaseMessage]:
    """Ensure system prompt contains agent persona and memory context cleanly."""
    soul_prompt = soul_store.build_system_prompt(agent_id)
    if not messages:
        return [SystemMessage(content=soul_prompt)]

    first = messages[0]
    if getattr(first, "type", "") == "system":
        content = str(first.content)
        # If already hydrated with persona/memory, preserve directly
        if soul_prompt in content:
            return messages

        marker = "=== PERSISTENT MEMORY CONTEXT ==="
        if marker in content:
            _, mem_block = content.split(marker, 1)
            new_system = f"{soul_prompt}\n\n{marker}{mem_block}"
        else:
            new_system = soul_prompt

        return [SystemMessage(content=new_system), *messages[1:]]

    return [SystemMessage(content=soul_prompt), *messages]


async def call(
    agent_id: str | list[BaseMessage] = "poseidon",
    messages: list[BaseMessage] | None = None,
    tools: list[dict[str, Any]] | None = None,
) -> AgentResult:
    """Execute inference for the specified agent.

    Args:
        agent_id: Identifier of the agent (e.g., 'poseidon', or custom).
                  If a list of messages is passed as first argument, defaults to 'poseidon'.
        messages: List of conversation messages.
        tools: Optional list of OpenAI-formatted tool schemas.

    Returns:
        AgentResult with 'content' (str | None) and 'tool_calls' (list | None).
    """
    # Backward compatibility: call(messages)
    if isinstance(agent_id, list):
        messages = agent_id
        agent_id = "poseidon"

    aid = (agent_id or "poseidon").lower()
    raw_messages = messages or []

    # Inject agent soul persona
    context_messages = _inject_agent_soul(aid, raw_messages)
    openai_msgs = _to_openai_messages(context_messages)

    conf = llm_provider.get_agent_resolved_config(aid)
    client = llm_provider.get_client(aid)
    model = conf.get("model") or llm_provider.get_model(aid)
    base_url = conf.get("base_url", "")
    preset = conf.get("preset", "")

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": openai_msgs,
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"

    try:
        response = await client.chat.completions.create(**kwargs)
    except Exception as e:
        err_text = str(e)
        if "Connection" in err_text or "connect" in err_text.lower() or "11434" in err_text:
            if preset == "local" or "11434" in base_url or "localhost" in base_url:
                raise RuntimeError(
                    f"[{aid.capitalize()}] Could not connect to local Ollama server at {base_url}. "
                    "Ensure Ollama is running (`ollama serve`) or switch to Cloud Free in Settings."
                ) from e
            else:
                raise RuntimeError(
                    f"[{aid.capitalize()}] Could not connect to inference endpoint '{base_url}' with model '{model}': {err_text}. "
                    "Check network access or API credentials."
                ) from e
        raise RuntimeError(f"[{aid.capitalize()}] Inference failed with model '{model}': {err_text}") from e

    choice = response.choices[0]
    msg = choice.message
    content = msg.content

    parsed_tool_calls: list[dict[str, Any]] | None = None
    if msg.tool_calls:
        parsed_tool_calls = []
        for tc in msg.tool_calls:
            args = tc.function.arguments
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    pass
            parsed_tool_calls.append({
                "id": tc.id,
                "name": tc.function.name,
                "arguments": args,
            })

    return AgentResult({
        "content": content.strip() if content else None,
        "tool_calls": parsed_tool_calls,
        "agent_id": aid,
        "model": model,
    })
