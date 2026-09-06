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


@pytest.mark.asyncio
async def test_telegram_routes_to_poseidon_env_by_default():
    """Verify normal Telegram message routes to Poseidon and resolves to .env provider."""
    from app.llm_providers import llm_provider

    fake_update = {
        "update_id": 2001,
        "message": {
            "message_id": 10,
            "from": {"id": 12345, "first_name": "ValidUser"},
            "chat": {"id": 12345, "type": "private"},
            "text": "What is the status of my tasks?",
        },
    }

    with patch.object(settings, "telegram_allowed_user_ids", "12345"):
        with patch("app.gateway.telegram_adapter.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"reply": "All tasks on schedule.", "active_agent": "poseidon"}
            with patch("app.gateway.telegram_adapter.send_telegram_reply", new_callable=AsyncMock):
                result = await process_telegram_update(fake_update, bot_token="fake_token")
                assert result.get("status") == "processed"
                assert mock_run.called

                # Check agent_id argument passed to run_agent
                _, kwargs = mock_run.call_args
                assert kwargs.get("agent_id") == "poseidon"

    # Verify poseidon provider resolves to .env settings (OpenRouter)
    pos_conf = llm_provider.get_agent_resolved_config("poseidon")
    assert pos_conf["preset"] == "env"
    assert pos_conf["base_url"] == settings.poseidon_base_url
    assert pos_conf["model"] == settings.poseidon_model
    assert pos_conf["has_api_key"] is True


@pytest.mark.asyncio
async def test_telegram_explicit_agent_selection_and_local_provider():
    """Verify explicit agent selection routes correctly, and local agent resolves to Ollama."""
    from app.llm_providers import llm_provider

    # 1. Test explicit @octavious selection
    update_oct = {
        "update_id": 2002,
        "message": {
            "message_id": 11,
            "from": {"id": 12345, "first_name": "ValidUser"},
            "chat": {"id": 12345, "type": "private"},
            "text": "@octavious check local system",
        },
    }

    with patch.object(settings, "telegram_allowed_user_ids", "12345"):
        with patch("app.gateway.telegram_adapter.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"reply": "Local system checked.", "active_agent": "octavious"}
            with patch("app.gateway.telegram_adapter.send_telegram_reply", new_callable=AsyncMock):
                result = await process_telegram_update(update_oct, bot_token="fake_token")
                assert result.get("status") == "processed"
                _, kwargs = mock_run.call_args
                assert kwargs.get("agent_id") == "octavious"

    # 2. Test explicit /agent octavious command
    update_cmd = {
        "update_id": 2003,
        "message": {
            "message_id": 12,
            "from": {"id": 12345, "first_name": "ValidUser"},
            "chat": {"id": 12345, "type": "private"},
            "text": "/agent octavious run diagnostic",
        },
    }

    with patch.object(settings, "telegram_allowed_user_ids", "12345"):
        with patch("app.gateway.telegram_adapter.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"reply": "Diagnostic complete.", "active_agent": "octavious"}
            with patch("app.gateway.telegram_adapter.send_telegram_reply", new_callable=AsyncMock):
                result = await process_telegram_update(update_cmd, bot_token="fake_token")
                assert result.get("status") == "processed"
                _, kwargs = mock_run.call_args
                assert kwargs.get("agent_id") == "octavious"

    # 3. Verify local/Ollama provider resolution still works for octavious or local preset
    with patch.dict(llm_provider._agent_overrides, {"octavious": {"preset": "local"}}):
        oct_conf = llm_provider.get_agent_resolved_config("octavious")
        assert oct_conf["preset"] == "local"
        assert oct_conf["base_url"] == "http://localhost:11434/v1"
        assert oct_conf["model"] == "llama3.2"
        assert oct_conf["api_key"] == "ollama"

