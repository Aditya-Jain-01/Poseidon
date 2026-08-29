"""Summarizer Agent — distills episodic conversation logs into persistent semantic & procedural memories.

Sprint 2 (Person C — Stage 5):
- Evaluates unconsolidated episodic memory events.
- Extracts durable semantic facts (user profile, preferences, relationships, constraints).
- Identifies repeatable procedural skills / playbooks.
- Writes facts to SemanticStore and skills to ProceduralStore.
- Marks processed episodic events as consolidated.
"""

import json
import re
from typing import Any
from openai import AsyncOpenAI

from app.config import settings
from app.memory.semantic_store import semantic_store
from app.memory.procedural_store import procedural_store
from app.memory.episodic_store import episodic_store


SUMMARIZER_SYSTEM_PROMPT = """You are the Memory Consolidation & Synthesis Subsystem for the Poseidon Personal AI Agent.

Your job is to analyze recent conversational exchanges and extract:
1. Durable Semantic Facts (facts about the user, their preferences, projects, relationships, constraints, or environment).
2. Procedural Skills (explicit step-by-step instructions or playbooks taught or established in conversation).

Guidelines:
- Ignore conversational filler, greetings, and ephemeral questions (e.g., "What is the capital of France?").
- Focus on lasting context (e.g., "Alex works on distributed systems", "User prefers dark mode", "Deployment requires building frontend first").
- Categorize each semantic fact into one of: 'preference', 'profile', 'relationship', 'general'.
- Ensure each fact is a clear, self-contained statement.
- Only output procedural skills if a clear, repeatable, multi-step playbook was taught or established.

You MUST reply ONLY with a valid JSON object matching this schema:
{
  "facts": [
    {
      "fact": "Clear description of the fact",
      "category": "preference" | "profile" | "relationship" | "general"
    }
  ],
  "skills": [
    {
      "name": "short_skill_name",
      "description": "Brief description of when and what this skill does",
      "triggers": ["trigger phrase 1", "trigger phrase 2"],
      "content": "Step-by-step markdown instructions for executing this skill"
    }
  ]
}
"""


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.poseidon_base_url,
    )


def _format_conversation(events: list[dict[str, Any]]) -> str:
    """Format raw episodic events into a chronological conversation transcript."""
    lines = []
    for ev in events:
        role = ev.get("role", "user")
        content = ev.get("content", "").strip()
        ts = ev.get("created_at", "")
        run_id = ev.get("run_id", "")
        prefix = f"[{ts}] {role.upper()}"
        if run_id:
            prefix += f" (run:{run_id[:8]})"
        lines.append(f"{prefix}: {content}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict[str, Any]:
    """Robustly extract and parse JSON from the model's response."""
    text = text.strip()
    if not text:
        return {"facts": [], "skills": []}

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try finding json block inside markdown fences
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding outermost braces
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    return {"facts": [], "skills": []}


async def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Call the LLM to extract semantic facts and procedural skills from episodic events."""
    if not events:
        return {"facts": [], "skills": []}

    conversation_text = _format_conversation(events)
    prompt = (
        f"Analyze the following conversation history and extract durable semantic facts and skills:\n\n"
        f"--- CONVERSATION START ---\n"
        f"{conversation_text}\n"
        f"--- CONVERSATION END ---\n\n"
        f"Output your JSON response below:"
    )

    client = _get_client()

    try:
        response = await client.chat.completions.create(
            model=settings.poseidon_model,
            messages=[
                {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"} if "openai" in settings.poseidon_base_url else None,
        )
        content = response.choices[0].message.content or ""
        return _extract_json(content)
    except Exception as e:
        print(f"[SummarizerAgent] Error calling LLM: {e}")
        return {"facts": [], "skills": []}


async def summarize_and_consolidate(
    user_id: str,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Distill events, persist extracted facts & skills, and mark events as consolidated.

    Returns summary details including added counts and event IDs.
    """
    if not events:
        return {
            "status": "empty",
            "events_processed": 0,
            "facts_added": 0,
            "skills_added": 0,
            "facts": [],
            "skills": [],
        }

    # 1. Run LLM summarization
    summary = await summarize_events(events)
    extracted_facts = summary.get("facts", [])
    extracted_skills = summary.get("skills", [])

    # 2. Persist semantic facts
    added_fact_ids = []
    latest_run_id = next((e.get("run_id") for e in reversed(events) if e.get("run_id")), None)

    for item in extracted_facts:
        if isinstance(item, dict) and item.get("fact"):
            fact_text = item["fact"].strip()
            category = item.get("category", "general")
            if category not in ["preference", "profile", "relationship", "general"]:
                category = "general"
            fact_id = semantic_store.add_fact(
                user_id=user_id,
                fact=fact_text,
                category=category,
                source_run_id=latest_run_id,
            )
            added_fact_ids.append(fact_id)

    # 3. Persist procedural skills if any
    added_skill_names = []
    for skill_item in extracted_skills:
        if isinstance(skill_item, dict) and skill_item.get("name") and skill_item.get("content"):
            name = skill_item["name"].strip()
            desc = skill_item.get("description", "")
            triggers = skill_item.get("triggers", [name])
            if isinstance(triggers, str):
                triggers = [triggers]
            content = skill_item["content"].strip()
            procedural_store.create_skill(
                name=name,
                description=desc,
                triggers=triggers,
                content=content,
            )
            added_skill_names.append(name)

    # 4. Mark episodic events as consolidated
    event_ids = [e["id"] for e in events if "id" in e]
    if event_ids:
        episodic_store.mark_consolidated(event_ids=event_ids)

    return {
        "status": "success",
        "events_processed": len(events),
        "facts_added": len(added_fact_ids),
        "skills_added": len(added_skill_names),
        "fact_ids": added_fact_ids,
        "skills": added_skill_names,
    }
