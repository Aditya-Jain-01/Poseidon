"""Trusted transport identity for the single-owner application."""
import hmac
import ipaddress
from fastapi import HTTPException, Request
from app.config import settings
from app.models import ActorContext


def is_loopback(host):
    if host == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_network_config():
    origins = settings.poseidon_cors_origins
    if '*' in origins:
        raise RuntimeError('Explicit CORS origins are required; wildcard CORS is unsupported')
    if not is_loopback(settings.poseidon_host):
        if not settings.poseidon_api_token or not origins:
            raise RuntimeError('Non-loopback binding requires POSEIDON_API_TOKEN and explicit CORS origins')


def resolve_actor(request: Request):
    host = request.client.host if request.client else ''
    if is_loopback(settings.poseidon_host) and is_loopback(host):
        return ActorContext(owner_id='local_owner', is_operator=True)
    supplied = request.headers.get('Authorization', '')
    expected = settings.poseidon_api_token
    if not expected or not hmac.compare_digest(supplied, f'Bearer {expected}'):
        raise HTTPException(status_code=401, detail='Operator authentication required')
    return ActorContext(owner_id='local_owner', is_operator=True)


def telegram_actor(sender_id):
    allowed = {s.strip() for s in settings.telegram_allowed_user_ids.split(',') if s.strip()}
    if str(sender_id) not in allowed:
        raise ValueError('Unauthorized Telegram sender')
    return ActorContext(owner_id='local_owner', is_operator=True)
