import base64
import hashlib
import hmac
import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def _b64encode(raw_bytes):
    return base64.urlsafe_b64encode(raw_bytes).rstrip(b'=').decode('ascii')


def _b64decode(raw_value):
    padding = '=' * (-len(raw_value) % 4)
    return base64.urlsafe_b64decode(raw_value + padding)


def _json_dumps(payload):
    return json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')


def _sign(message):
    return hmac.new(settings.SECRET_KEY.encode('utf-8'), message, hashlib.sha256).digest()


def _encode(payload):
    header = {'alg': 'HS256', 'typ': 'JWT'}
    header_segment = _b64encode(_json_dumps(header))
    payload_segment = _b64encode(_json_dumps(payload))
    signing_input = f'{header_segment}.{payload_segment}'.encode('ascii')
    signature_segment = _b64encode(_sign(signing_input))
    return f'{header_segment}.{payload_segment}.{signature_segment}'


def _decode(token):
    try:
        header_segment, payload_segment, signature_segment = token.split('.')
    except ValueError as exc:
        raise ValueError('token_malformed') from exc

    signing_input = f'{header_segment}.{payload_segment}'.encode('ascii')
    expected_signature = _b64encode(_sign(signing_input))
    if not hmac.compare_digest(expected_signature, signature_segment):
        raise ValueError('token_signature_invalid')

    payload = json.loads(_b64decode(payload_segment).decode('utf-8'))
    return payload


def build_access_token(user, ttl_minutes=None):
    now = timezone.now()
    ttl = ttl_minutes or settings.JWT_ACCESS_TOKEN_TTL_MINUTES
    payload = {
        'type': 'access',
        'sub': user.pk,
        'username': user.username,
        'login_id': user.login_id,
        'role': user.role,
        'iss': settings.JWT_ISSUER,
        'aud': settings.JWT_AUDIENCE,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(minutes=ttl)).timestamp()),
        'jti': secrets.token_hex(16),
    }
    return _encode(payload), payload


def build_refresh_token(user, ttl_days=None):
    now = timezone.now()
    ttl = ttl_days or settings.JWT_REFRESH_TOKEN_TTL_DAYS
    payload = {
        'type': 'refresh',
        'sub': user.pk,
        'username': user.username,
        'login_id': user.login_id,
        'iss': settings.JWT_ISSUER,
        'aud': settings.JWT_AUDIENCE,
        'iat': int(now.timestamp()),
        'exp': int((now + timedelta(days=ttl)).timestamp()),
        'jti': secrets.token_hex(24),
    }
    return _encode(payload), payload


def verify_token(token, expected_type):
    payload = _decode(token)
    if payload.get('type') != expected_type:
        raise ValueError('token_type_invalid')
    if payload.get('iss') != settings.JWT_ISSUER or payload.get('aud') != settings.JWT_AUDIENCE:
        raise ValueError('token_scope_invalid')
    if int(payload.get('exp', 0)) < int(timezone.now().timestamp()):
        raise ValueError('token_expired')
    return payload
