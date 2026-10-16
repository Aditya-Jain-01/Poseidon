import json
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient


def test_chat_ignores_forged_identity_and_channel(monkeypatch):
    from app.main import app
    import app.gateway.web_adapter as adapter
    captured = []
    async def fake_run(event, run_id, agent_id):
        captured.append(event)
        return {'reply': 'ok', 'run_id': run_id, 'thread_id': event.channel_thread_id,
                'conversation_key': event.conversation_key.model_dump()}
    monkeypatch.setattr(adapter, 'run_agent', fake_run)
    client = TestClient(app, client=('127.0.0.1', 50000))
    result = client.post('/chat', json={'text': 'hello', 'user_id': 'attacker', 'channel': 'telegram', 'thread_id': 'session-a'}, headers={'X-Poseidon-User': 'attacker'})
    assert result.status_code == 200
    assert captured[0].actor.owner_id == 'local_owner'
    assert captured[0].channel == 'web'
    assert captured[0].channel_thread_id == 'session-a'


def test_chat_uses_text_agent_selection(monkeypatch):
    from app.main import app
    import app.gateway.web_adapter as adapter

    selected = []
    async def fake_run(event, run_id, agent_id):
        selected.append(agent_id)
        return {'reply': 'ok', 'run_id': run_id, 'thread_id': event.channel_thread_id,
                'conversation_key': event.conversation_key.model_dump()}

    monkeypatch.setattr(adapter, 'run_agent', fake_run)
    response = TestClient(app, client=('127.0.0.1', 50000)).post('/chat', json={'text': '@octavious hello'})

    assert response.status_code == 200
    assert selected == ['octavious']


def test_memory_query_identity_has_no_authority():
    from app.main import app
    from app.memory.semantic_store import semantic_store
    semantic_store.add_fact('local_owner', 'Owner fact')
    semantic_store.add_fact('attacker', 'Other fact')
    response = TestClient(app, client=('127.0.0.1', 50000)).get('/memory/semantic?user_id=attacker')
    assert response.status_code == 200
    assert response.json()['user_id'] == 'local_owner'
    assert [f['fact'] for f in response.json()['facts']] == ['Owner fact']


def test_remote_requests_require_token_and_ignore_user_header(monkeypatch):
    from app.main import app
    from app.config import settings
    monkeypatch.setattr(settings, 'poseidon_api_token', 'operator-token')
    client = TestClient(app, client=('192.0.2.10', 50000))
    assert client.get('/settings/llm', headers={'X-Poseidon-User': 'local_owner'}).status_code == 401
    assert client.get('/settings/llm', headers={'Authorization': 'Bearer operator-token'}).status_code == 200


def test_unsafe_bind_and_cors_rejected(monkeypatch):
    from app.config import settings
    from app.security.identity import validate_network_config
    monkeypatch.setattr(settings, 'poseidon_host', '0.0.0.0')
    monkeypatch.setattr(settings, 'poseidon_api_token', '')
    with pytest.raises(RuntimeError, match='Non-loopback'):
        validate_network_config()
    monkeypatch.setattr(settings, 'poseidon_api_token', 'operator-token')
    monkeypatch.setattr(settings, 'poseidon_cors_origins', ['*'])
    with pytest.raises(RuntimeError, match='wildcard'):
        validate_network_config()
    monkeypatch.setattr(settings, 'poseidon_cors_origins', ['http://localhost:5173'])
    validate_network_config()


def test_telegram_empty_allowlist_rejects_and_verified_sender_maps_owner(monkeypatch):
    from app.config import settings
    from app.security.identity import telegram_actor
    from app.gateway.telegram_adapter import is_user_allowed
    monkeypatch.setattr(settings, 'telegram_allowed_user_ids', '')
    assert not is_user_allowed(123)
    with pytest.raises(ValueError, match='Unauthorized'):
        telegram_actor(123)
    monkeypatch.setattr(settings, 'telegram_allowed_user_ids', '123')
    assert telegram_actor(123).owner_id == 'local_owner'


def test_secret_canary_absent_from_public_provider_config_and_disk(monkeypatch, tmp_path):
    from app.config import settings
    from app.llm_providers import LLMProvider
    monkeypatch.setattr(settings, 'poseidon_api_key', 'secret-canary-that-must-not-leak')
    provider = LLMProvider()
    provider._config_path = tmp_path / 'llm.json'
    provider._agent_overrides['poseidon']['api_key'] = 'legacy-plaintext-canary'
    provider.save_config()
    public = json.dumps([provider.get_all_configs(), provider.get_agent_resolved_config(), provider.update_provider('poseidon', model='test-model')])
    assert 'secret-canary-that-must-not-leak' not in public
    assert 'legacy-plaintext-canary' not in public
    assert '"api_key"' not in public
    assert 'legacy-plaintext-canary' not in provider._config_path.read_text()
    assert provider.get_agent_resolved_config()['has_api_key']


def test_plaintext_key_api_is_rejected_without_echoing_it():
    from app.main import app
    client = TestClient(app, client=('127.0.0.1', 50000))
    response = client.put('/settings/llm/poseidon', json={'api_key': 'plaintext-canary'})
    assert response.status_code == 422
    assert 'plaintext-canary' not in response.text
