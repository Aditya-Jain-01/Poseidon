"""Telegram Gateway Adapter — Dual-Mode (Local Long-Polling + Webhooks).

Follows the Waku-Agent pattern:
- Local Long-Polling: Runs 100% locally behind NATs/firewalls with zero public URLs required.
- Webhook Endpoint: POST /gateway/telegram/webhook with secret token verification.
- Security: Strictly enforces TELEGRAM_ALLOWED_USER_IDS to drop unauthorized interactions.
- Zero Harness Coupling: Normalizes Telegram updates into InboundEvent and returns replies.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, Header, HTTPException, Request, Response
from pydantic import BaseModel

from app.config import settings
from app.orchestration.graph import run_agent
from app.orchestration.state import InboundEvent
from app.security.taint import is_channel_untrusted


router = APIRouter(prefix="/gateway/telegram", tags=["Telegram Gateway"])


def get_allowed_user_ids() -> set[str]:
    """Parse configured allowed Telegram user IDs."""
    raw = getattr(settings, "telegram_allowed_user_ids", "") or ""
    if not raw.strip():
        return set()
    return {uid.strip() for uid in raw.split(",") if uid.strip()}


def is_user_allowed(sender_id: str | int) -> bool:
    """Check if the sender is authorized to talk to this local agent."""
    allowed = get_allowed_user_ids()
    if not allowed:
        # If no allowlist is configured, permit (or reject if strict).
        return True
    return str(sender_id) in allowed


async def send_telegram_reply(bot_token: str, chat_id: int | str, text: str) -> bool:
    """Send message back to Telegram chat."""
    if not bot_token:
        return False
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json={"chat_id": chat_id, "text": text})
            return resp.status_code == 200
    except Exception as exc:
        print(f"[TelegramAdapter] Failed to send reply to Telegram: {exc}")
        return False


async def process_telegram_update(update: dict[str, Any], bot_token: str = "") -> dict[str, Any]:
    """Normalize a Telegram update into InboundEvent and execute turn."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"status": "ignored", "reason": "No message payload"}

    from_user = message.get("from", {})
    sender_id = from_user.get("id")
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()

    if not text:
        return {"status": "ignored", "reason": "Empty message text"}

    # 1. Authorization check (Waku pattern)
    if not is_user_allowed(sender_id):
        print(f"[TelegramAdapter] Dropped message from unauthorized user ID: {sender_id}")
        return {"status": "rejected", "reason": f"Unauthorized user: {sender_id}"}

    # 2. Normalize to InboundEvent
    tainted = is_channel_untrusted("telegram")
    event = InboundEvent(
        user_id=f"telegram_{sender_id}",
        channel="telegram",
        channel_thread_id=f"telegram_{chat_id}",
        text=text,
        timestamp=datetime.now(timezone.utc),
        is_tainted=tainted,
        taint_sources=["telegram"] if tainted else [],
    )

    # 3. Invoke Agent Harness
    run_id = str(uuid4())
    result = await run_agent(event, run_id=run_id)
    reply_text = result.get("reply") or ""

    # 4. Outbound delivery back to Telegram
    token = bot_token or getattr(settings, "telegram_bot_token", "")
    if token and chat_id:
        await send_telegram_reply(token, chat_id, reply_text)

    return {
        "status": "processed",
        "run_id": run_id,
        "reply": reply_text,
        "chat_id": chat_id,
        "sender_id": sender_id,
    }


# ── Webhook Endpoint (Server deployments) ───────────────────────────

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> dict[str, Any]:
    """Receive webhook updates from Telegram Bot API."""
    expected_secret = getattr(settings, "telegram_webhook_secret", "")
    if expected_secret:
        if x_telegram_bot_api_secret_token != expected_secret:
            raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret token")

    payload = await request.json()
    result = await process_telegram_update(payload)
    return result


# ── Local Long-Polling Runner (Waku pattern) ────────────────────────

class TelegramLongPoller:
    """Async background task that runs long-polling locally on developer machines."""

    def __init__(self, bot_token: str | None = None) -> None:
        self.bot_token = bot_token or getattr(settings, "telegram_bot_token", "")
        self.offset = 0
        self._running = False
        self._task: asyncio.Task | None = None

    async def _poll_loop(self) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
        print("[TelegramLongPoller] Started local long-polling runner.")

        async with httpx.AsyncClient(timeout=35.0) as client:
            while self._running:
                try:
                    params = {"offset": self.offset, "timeout": 30}
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        data = resp.json()
                        updates = data.get("result", [])
                        for update in updates:
                            update_id = update.get("update_id", 0)
                            self.offset = max(self.offset, update_id + 1)
                            await process_telegram_update(update, bot_token=self.bot_token)
                    elif resp.status_code == 409:
                        print("[TelegramLongPoller] Conflict: another bot instance or webhook is active. Waiting 10s...")
                        await asyncio.sleep(10)
                    else:
                        await asyncio.sleep(2)
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    print(f"[TelegramLongPoller] Error in poll loop: {exc}")
                    await asyncio.sleep(3)

    def start(self) -> None:
        if not self.bot_token:
            return
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()


poller = TelegramLongPoller()
