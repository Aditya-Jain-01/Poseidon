"""Tests for Telegram Gateway Adapter (Dual-mode, normalization, and authorization)."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.gateway.telegram_adapter import process_telegram_update, is_user_allowed


client = TestClient(app)


def test_telegram_user_allowlist():
    with patch.object(settings, "telegram_allowed_user_ids", "111,222,333"):
        assert is_user_allowed(111) is True
        assert is_user_allowed("222") is True
        assert is_user_allowed(999) is False


@pytest.mark.asyncio
async def test_telegram_process_update_unauthorized():
    fake_update = {
        "update_id": 1001,
        "message": {
            "message_id": 1,
            "from": {"id": 99999, "first_name": "Attacker"},
            "chat": {"id": 99999, "type": "private"},
            "text": "Hello bot",
        },
    }

    with patch.object(settings, "telegram_allowed_user_ids", "12345"):
        result = await process_telegram_update(fake_update)
        assert result.get("status") == "rejected"
        assert "Unauthorized" in result.get("reason", "")


@pytest.mark.asyncio
async def test_telegram_process_update_authorized():
    fake_update = {
        "update_id": 1002,
        "message": {
            "message_id": 2,
            "from": {"id": 12345, "first_name": "ValidUser"},
            "chat": {"id": 12345, "type": "private"},
            "text": "What time is it?",
        },
    }

    with patch.object(settings, "telegram_allowed_user_ids", "12345"):
        with patch("app.gateway.telegram_adapter.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {
                "reply": "It is afternoon.",
                "run_id": "run_tg_001",
            }
            with patch("app.gateway.telegram_adapter.send_telegram_reply", new_callable=AsyncMock) as mock_reply:
                mock_reply.return_value = True

                result = await process_telegram_update(fake_update, bot_token="fake_token")
                assert result.get("status") == "processed"
                assert result.get("reply") == "It is afternoon."
                assert mock_run.called
                event_arg = mock_run.call_args[0][0]
                assert event_arg.channel == "telegram"
                assert event_arg.user_id == "telegram_12345"


def test_telegram_webhook_secret_header_verification():
    with patch.object(settings, "telegram_webhook_secret", "super_secret_token"):
        # Without secret header -> 403
        resp = client.post(
            "/gateway/telegram/webhook",
            json={"update_id": 1, "message": {"text": "hi", "from": {"id": 1}, "chat": {"id": 1}}},
        )
        assert resp.status_code == 403

        # With valid secret header -> accepted
        with patch("app.gateway.telegram_adapter.process_telegram_update", new_callable=AsyncMock) as mock_proc:
            mock_proc.return_value = {"status": "processed"}
            resp_valid = client.post(
                "/gateway/telegram/webhook",
                json={"update_id": 1, "message": {"text": "hi", "from": {"id": 1}, "chat": {"id": 1}}},
                headers={"X-Telegram-Bot-Api-Secret-Token": "super_secret_token"},
            )
            assert resp_valid.status_code == 200
