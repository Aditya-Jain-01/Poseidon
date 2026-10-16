"""Tests for Telegram Gateway Adapter (Dual-mode, normalization, and authorization)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.gateway.telegram_adapter import process_telegram_update, is_user_allowed


client = TestClient(app, client=('127.0.0.1', 50000))


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
                assert event_arg.user_id == "local_owner"
                assert event_arg.conversation_key.channel_account_id == "telegram_12345"


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


def test_telegram_webhook_rejects_requests_when_secret_is_unset():
    with patch.object(settings, "telegram_webhook_secret", ""):
        response = client.post(
            "/gateway/telegram/webhook",
            json={"update_id": 1, "message": {"text": "hi", "from": {"id": 1}, "chat": {"id": 1}}},
        )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_failed_telegram_reply_keeps_update_retryable():
    from app.db.connection import connection

    update = {"update_id": 987654, "message": {"message_id": 1, "from": {"id": 12345},
                                              "chat": {"id": 12345}, "text": "hello"}}
    with patch.object(settings, "telegram_allowed_user_ids", "12345"):
        with patch("app.gateway.telegram_adapter.run_agent", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = {"reply": "hello back"}
            with patch("app.gateway.telegram_adapter.send_telegram_reply", new_callable=AsyncMock) as mock_reply:
                mock_reply.return_value = False
                with pytest.raises(RuntimeError, match="delivery failed"):
                    await process_telegram_update(update, bot_token="fake_token")
                mock_reply.return_value = True
                retried = await process_telegram_update(update, bot_token="fake_token")
                assert retried["reply"] == "hello back"
                mock_run.assert_awaited_once()

    with connection(settings.poseidon_db_path) as conn:
        row = conn.execute("SELECT status FROM telegram_updates WHERE update_id=?", (987654,)).fetchone()
    assert row["status"] == "completed"


@pytest.mark.asyncio
async def test_poller_keeps_offset_when_update_processing_fails():
    from app.gateway.telegram_adapter import TelegramLongPoller

    poller = TelegramLongPoller(bot_token="fake_token")
    poller.offset = 987000
    poller._running = True
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"result": [{"update_id": 987000, "message": {"text": "hello"}}]}
    transport = AsyncMock()
    transport.get.return_value = response
    transport_context = AsyncMock()
    transport_context.__aenter__.return_value = transport

    async def stop_after_failure(_seconds):
        poller._running = False

    with patch("app.gateway.telegram_adapter.httpx.AsyncClient", return_value=transport_context), \
         patch("app.gateway.telegram_adapter.process_telegram_update", new_callable=AsyncMock) as process, \
         patch("app.gateway.telegram_adapter.persist_offset") as persist, \
         patch("app.gateway.telegram_adapter.asyncio.sleep", side_effect=stop_after_failure):
        process.side_effect = RuntimeError("delivery failed")
        await poller._poll_loop()

    assert poller.offset == 987000
    process.assert_awaited_once()
    persist.assert_not_called()


@pytest.mark.asyncio
async def test_poller_moves_past_update_after_retry_limit():
    from app.gateway.telegram_adapter import TelegramLongPoller

    poller = TelegramLongPoller(bot_token="fake_token")
    poller.offset = 987000
    poller._running = True
    response = MagicMock(status_code=200)
    response.json.return_value = {"result": [{"update_id": 987000, "message": {"text": "hello"}}]}
    transport = AsyncMock()
    transport.get.return_value = response
    transport_context = AsyncMock()
    transport_context.__aenter__.return_value = transport

    def persist_and_stop(_offset):
        poller._running = False

    with patch("app.gateway.telegram_adapter.httpx.AsyncClient", return_value=transport_context), \
         patch("app.gateway.telegram_adapter.process_telegram_update", new_callable=AsyncMock) as process, \
         patch("app.gateway.telegram_adapter.update_attempt_count", return_value=5), \
         patch("app.gateway.telegram_adapter.persist_offset", side_effect=persist_and_stop) as persist:
        process.side_effect = RuntimeError("delivery failed")
        await poller._poll_loop()

    assert poller.offset == 987001
    persist.assert_called_once_with(987001)


@pytest.mark.asyncio
async def test_poller_keeps_update_pending_when_outbound_limit_is_reached():
    from app.gateway.telegram_adapter import TelegramLongPoller
    from app.security.guardrails import GuardrailRateLimitError

    poller = TelegramLongPoller(bot_token='fake_token')
    poller.offset = 987000
    poller._running = True
    response = MagicMock(status_code=200)
    response.json.return_value = {'result': [{'update_id': 987000, 'message': {'text': 'hello'}}]}
    transport = AsyncMock()
    transport.get.return_value = response
    transport_context = AsyncMock()
    transport_context.__aenter__.return_value = transport

    async def stop_after_wait(_seconds):
        poller._running = False

    with patch('app.gateway.telegram_adapter.httpx.AsyncClient', return_value=transport_context), \
         patch('app.gateway.telegram_adapter.process_telegram_update', new_callable=AsyncMock) as process, \
         patch('app.gateway.telegram_adapter.persist_offset') as persist, \
         patch('app.gateway.telegram_adapter.asyncio.sleep', side_effect=stop_after_wait):
        process.side_effect = GuardrailRateLimitError('send limit')
        await poller._poll_loop()

    assert poller.offset == 987000
    persist.assert_not_called()


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
        assert oct_conf["has_api_key"] is True
        assert "api_key" not in oct_conf

