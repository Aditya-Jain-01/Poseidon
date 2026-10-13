"""Telegram Gateway Adapter — Dual-Mode (Local Long-Polling + Webhooks).

Follows the Waku-Agent pattern:
- Local Long-Polling: Runs 100% locally behind NATs/firewalls with zero public URLs required.
- Webhook Endpoint: POST /gateway/telegram/webhook with secret token verification.
- Security: Strictly enforces TELEGRAM_ALLOWED_USER_IDS to drop unauthorized interactions.
- Zero Harness Coupling: Normalizes Telegram updates into InboundEvent and returns replies.
- Durability: Tracks delivery state and offsets in SQLite across restarts.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from app.config import settings
from app.db.connection import connection
from app.orchestration.graph import run_agent
from app.orchestration.state import InboundEvent
from app.models import ConversationKey
from app.security.audit import audit_service
from app.security.identity import telegram_actor
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
        return False
    return str(sender_id) in allowed


def get_persisted_offset(db_path: Path | None = None) -> int:
    """Load persisted polling offset from database."""
    path = db_path or settings.poseidon_db_path
    if not path.exists():
        return 0
    try:
        with connection(path) as conn:
            row = conn.execute("SELECT state_json FROM gateway_channel_state WHERE channel = 'telegram'").fetchone()
            if row:
                return json.loads(row[0]).get("offset", 0)
    except Exception:
        pass
    return 0


def persist_offset(offset: int, db_path: Path | None = None) -> None:
    """Persist polling offset to database."""
    path = db_path or settings.poseidon_db_path
    if not path.exists():
        return
    try:
        now_ts = datetime.now(timezone.utc).isoformat()
        with connection(path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO gateway_channel_state (channel, state_json, updated_at) VALUES ('telegram', ?, ?)",
                (json.dumps({"offset": offset}), now_ts),
            )
            conn.commit()
    except Exception:
        pass


def record_update_receipt(update_id: int, run_id: str, payload_hash: str, db_path: Path | None = None) -> str:
    """Record receipt of a Telegram update. Returns current status."""
    path = db_path or settings.poseidon_db_path
    if not path.exists():
        return "received"
    now_ts = datetime.now(timezone.utc).isoformat()
    try:
        with connection(path) as conn:
            row = conn.execute("SELECT status FROM telegram_updates WHERE update_id = ?", (update_id,)).fetchone()
            if row:
                return row[0]
            conn.execute(
                """INSERT INTO telegram_updates 
                (update_id, status, run_id, attempt_count, payload_hash, received_at, updated_at)
                VALUES (?, 'received', ?, 0, ?, ?, ?)""",
                (update_id, run_id, payload_hash, now_ts, now_ts),
            )
            conn.commit()
            return "received"
    except Exception:
        return "received"


def claim_update(update_id: int, db_path: Path | None = None) -> bool:
    """Atomically claim a Telegram update for processing."""
    path = db_path or settings.poseidon_db_path
    if not path.exists():
        return True
    now_ts = datetime.now(timezone.utc).isoformat()
    try:
        with connection(path) as conn:
            cur = conn.execute(
                """UPDATE telegram_updates 
                SET status = 'processing', attempt_count = attempt_count + 1, updated_at = ?
                WHERE update_id = ? AND status IN ('received', 'processing', 'failed')""",
                (now_ts, update_id),
            )
            conn.commit()
            return cur.rowcount > 0
    except Exception:
        return True


def complete_update(update_id: int, db_path: Path | None = None) -> None:
    """Mark Telegram update completed."""
    path = db_path or settings.poseidon_db_path
    if not path.exists():
        return
    now_ts = datetime.now(timezone.utc).isoformat()
    try:
        with connection(path) as conn:
            conn.execute(
                "UPDATE telegram_updates SET status = 'completed', completed_at = ?, updated_at = ? WHERE update_id = ?",
                (now_ts, now_ts, update_id),
            )
            conn.commit()
    except Exception:
        pass


def fail_update(update_id: int, error_msg: str, db_path: Path | None = None) -> None:
    """Mark Telegram update failed."""
    path = db_path or settings.poseidon_db_path
    if not path.exists():
        return
    now_ts = datetime.now(timezone.utc).isoformat()
    try:
        with connection(path) as conn:
            conn.execute(
                "UPDATE telegram_updates SET status = 'failed', last_error = ?, updated_at = ? WHERE update_id = ?",
                (error_msg[:1000], now_ts, update_id),
            )
            conn.commit()
    except Exception:
        pass


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

    if not is_user_allowed(sender_id):
        print(f"[TelegramAdapter] Dropped message from unauthorized user ID: {sender_id}")
        return {"status": "rejected", "reason": f"Unauthorized user: {sender_id}"}

    if chat_id is None or sender_id is None:
        return {"status": "rejected", "reason": "Missing verified Telegram identifiers"}

    update_id = update.get("update_id")
    if update_id is not None:
        run_id = f"telegram_update_{update_id}"
        payload_hash = hashlib.sha256(json.dumps(update, sort_keys=True, default=str).encode()).hexdigest()
        receipt_status = record_update_receipt(update_id, run_id, payload_hash)
        if receipt_status == "completed":
            return {"status": "already_completed", "run_id": run_id}
        claim_update(update_id)
    else:
        run_id = str(uuid4())

    actor = telegram_actor(sender_id)
    key = ConversationKey(
        owner_id=actor.owner_id,
        channel="telegram",
        channel_account_id=f"telegram_{sender_id}",
        thread_id=f"chat_{chat_id}:thread_{message.get('message_thread_id', 'default')}",
    )
    user_id = actor.owner_id
    token = bot_token or getattr(settings, "telegram_bot_token", "")

    audit_service.record_event(
        run_id=run_id,
        owner_id=actor.owner_id,
        channel="telegram",
        direction="inbound",
        event_type="telegram_message",
        status="received",
        payload={"update_id": update_id, "chat_id": chat_id, "sender_id": sender_id, "text": text},
    )

    try:
        from app.orchestration.approval_store import approval_store
        from app.orchestration.graph import resume_approval

        pending = approval_store.get_pending_for_user(user_id, key)
        if pending:
            clean = text.strip().lower()
            pin = getattr(settings, "poseidon_operator_pin", "").strip()

            if clean in {"/deny", "deny", "no", "cancel", "reject", "abort"}:
                res = await resume_approval(pending["id"], "denied", owner_id=actor.owner_id, conversation_key=key)
                reply_text = res.get("reply", "Action denied. No changes were made.")
                if token and chat_id:
                    await send_telegram_reply(token, chat_id, reply_text)
                if update_id is not None:
                    complete_update(update_id)
                audit_service.record_event(
                    run_id=run_id,
                    owner_id=actor.owner_id,
                    channel="telegram",
                    direction="outbound",
                    event_type="telegram_reply",
                    status="completed",
                    payload={"reply": reply_text, "chat_id": chat_id},
                )
                return {"status": "processed", "reply": reply_text, "chat_id": chat_id, "sender_id": sender_id}

            approved = False
            if pin:
                if text.strip() == pin or clean == f"/approve {pin}".lower() or clean == f"approve {pin}".lower():
                    approved = True
                elif clean in {"/approve", "approve", "yes", "confirm", "y", "proceed"}:
                    reply_text = "🔒 Operator PIN required. Reply with your PIN to approve this action, or 'deny' to cancel."
                    if token and chat_id:
                        await send_telegram_reply(token, chat_id, reply_text)
                    if update_id is not None:
                        complete_update(update_id)
                    return {"status": "processed", "reply": reply_text, "chat_id": chat_id, "sender_id": sender_id}
                else:
                    reply_text = f"🔒 Incorrect PIN or invalid response for pending approval '{pending['tool_name']}'. Reply with your operator PIN to approve, or 'deny' to cancel."
                    if token and chat_id:
                        await send_telegram_reply(token, chat_id, reply_text)
                    if update_id is not None:
                        complete_update(update_id)
                    return {"status": "processed", "reply": reply_text, "chat_id": chat_id, "sender_id": sender_id}
            else:
                if clean in {"/approve", "approve", "yes", "confirm", "y", "ok", "proceed"}:
                    approved = True

            if approved:
                res = await resume_approval(pending["id"], "approved", owner_id=actor.owner_id, conversation_key=key)
                reply_text = res.get("reply", "Action approved and executed.")
                if token and chat_id:
                    await send_telegram_reply(token, chat_id, reply_text)
                if update_id is not None:
                    complete_update(update_id)
                audit_service.record_event(
                    run_id=run_id,
                    owner_id=actor.owner_id,
                    channel="telegram",
                    direction="outbound",
                    event_type="telegram_reply",
                    status="completed",
                    payload={"reply": reply_text, "chat_id": chat_id},
                )
                return {"status": "processed", "reply": reply_text, "chat_id": chat_id, "sender_id": sender_id}

        tainted = is_channel_untrusted("telegram")
        event = InboundEvent(
            actor=actor,
            conversation_key=key,
            text=text,
            timestamp=datetime.now(timezone.utc),
            is_tainted=tainted,
            taint_sources=["telegram"] if tainted else [],
        )

        from app.orchestration.router import route_request

        target_agent = route_request(text)
        result = await run_agent(event, run_id=run_id, agent_id=target_agent)
        reply_text = result.get("reply") or ""

        if result.get("approval_request"):
            tool_name = result["approval_request"].get("tool_name", "this action")
            pin = getattr(settings, "poseidon_operator_pin", "").strip()
            auth_hint = "your Operator PIN" if pin else "'yes' or '/approve'"
            reply_text = f"⚠️ Approval Required: {tool_name} requires confirmation.\n\nReply with {auth_hint} to proceed, or 'deny' to cancel."

        if token and chat_id:
            await send_telegram_reply(token, chat_id, reply_text)

        if update_id is not None:
            complete_update(update_id)

        audit_service.record_event(
            run_id=run_id,
            owner_id=actor.owner_id,
            channel="telegram",
            direction="outbound",
            event_type="telegram_reply",
            status="completed",
            payload={"reply": reply_text, "chat_id": chat_id},
        )

        return {
            "status": "processed",
            "run_id": run_id,
            "reply": reply_text,
            "chat_id": chat_id,
            "sender_id": sender_id,
        }
    except Exception as exc:
        if update_id is not None:
            fail_update(update_id, str(exc))
        audit_service.record_event(
            run_id=run_id,
            owner_id=actor.owner_id,
            channel="telegram",
            direction="outbound",
            event_type="telegram_error",
            status="failed",
            payload={"error": str(exc)},
        )
        raise


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> dict[str, Any]:
    """Receive webhook updates from Telegram Bot API."""
    expected_secret = getattr(settings, "telegram_webhook_secret", "").strip()
    if expected_secret:
        if not x_telegram_bot_api_secret_token or x_telegram_bot_api_secret_token != expected_secret:
            raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret token")

    payload = await request.json()
    result = await process_telegram_update(payload)
    return result


class TelegramLongPoller:
    """Async background task that runs long-polling locally on developer machines."""

    def __init__(self, bot_token: str | None = None) -> None:
        self.bot_token = bot_token or getattr(settings, "telegram_bot_token", "")
        self.offset = get_persisted_offset()
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
                            if update_id:
                                # Ensure durable receipt before advancing offset
                                run_id = f"telegram_update_{update_id}"
                                payload_hash = hashlib.sha256(json.dumps(update, sort_keys=True, default=str).encode()).hexdigest()
                                record_update_receipt(update_id, run_id, payload_hash)
                                self.offset = max(self.offset, update_id + 1)
                                persist_offset(self.offset)
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
        self.offset = get_persisted_offset()
        self._task = asyncio.create_task(self._poll_loop())

    def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    async def astop(self) -> None:
        self.stop()
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass


poller = TelegramLongPoller()
