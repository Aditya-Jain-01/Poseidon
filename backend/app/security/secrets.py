"""Redact configured secrets as well as recognizable token patterns."""
import os
import sys
from app.config import settings
from app.security.dlp import DLPScanner


def redact(value):
    secrets = [getattr(settings, key, '') for key in ('poseidon_api_key', 'openrouter_api_key', 'nvidia_api_key', 'kraken_api_key', 'poseidon_api_token', 'telegram_bot_token', 'telegram_webhook_secret')]
    secrets.extend(v for k, v in os.environ.items() if k.endswith(('_API_KEY', '_TOKEN', '_SECRET')))
    # Credential references may use arbitrary environment-variable names.
    module = sys.modules.get('app.llm_providers')
    provider = getattr(module, 'llm_provider', None)
    if provider is not None:
        configs = [*provider._providers.values(), *provider._agent_overrides.values()]
        secrets.extend(os.environ.get(config.get('api_key_env', ''), '') for config in configs)
    if isinstance(value, str):
        for secret in secrets:
            if secret:
                value = value.replace(secret, '[REDACTED_SECRET]')
        return DLPScanner.scan_and_redact(value).sanitized_text
    if isinstance(value, dict):
        return {k: '[REDACTED_SECRET]' if k.lower() in {'api_key', 'authorization', 'token', 'secret'} else redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value
