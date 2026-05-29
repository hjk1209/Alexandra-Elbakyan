from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from .models import LoginAttempt, SecurityEvent


def clean_plain_text(value):
    return ' '.join(strip_tags(value or '').split())


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if getattr(settings, 'RAIZ_TRUST_X_FORWARDED_FOR', False) and forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')[:255]


def record_login_attempt(request, username, success, user=None):
    LoginAttempt.objects.create(
        user=user,
        username=username,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        was_successful=success,
    )
    event_type = SecurityEvent.EventType.LOGIN_SUCCESS if success else SecurityEvent.EventType.LOGIN_FAILURE
    severity = SecurityEvent.Severity.INFO if success else SecurityEvent.Severity.WARNING
    record_security_event(
        request,
        event_type,
        severity=severity,
        user=user,
        details={'username': username},
    )


def record_security_event(request, event_type, severity=SecurityEvent.Severity.INFO, user=None, details=None):
    SecurityEvent.objects.create(
        user=user,
        event_type=event_type,
        severity=severity,
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request),
        request_path=getattr(request, 'path', '')[:255],
        details=details or {},
    )


def is_login_locked_out(username, ip_address):
    threshold = timezone.now() - timedelta(minutes=settings.LOGIN_LOCK_WINDOW_MINUTES)
    username_failures = LoginAttempt.objects.filter(
        username__iexact=username,
        was_successful=False,
        attempted_at__gte=threshold,
    ).count()
    ip_failures = LoginAttempt.objects.filter(
        ip_address=ip_address,
        was_successful=False,
        attempted_at__gte=threshold,
    ).count()
    return username_failures >= settings.MAX_LOGIN_FAILURES or ip_failures >= settings.MAX_LOGIN_FAILURES


def throttle_request(request, scope, limit, window_seconds):
    actor = str(request.user.pk) if request.user.is_authenticated else get_client_ip(request)
    cache_key = f'throttle:{scope}:{actor}'
    if cache.add(cache_key, 1, timeout=window_seconds):
        return False, 1
    try:
        current = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=window_seconds)
        current = 1
    return current > limit, current


def build_protected_media_token(kind, object_id, action='view'):
    return signing.dumps(
        {
            'kind': kind,
            'object_id': int(object_id),
            'action': action,
        },
        salt='rede-raizes-socialista.protected-media',
        compress=True,
    )


def resolve_protected_media_token(token, max_age_seconds=None):
    max_age = max_age_seconds or settings.PROTECTED_MEDIA_TOKEN_TTL_SECONDS
    return signing.loads(token, salt='rede-raizes-socialista.protected-media', max_age=max_age)


def build_protected_media_url(kind, object_id, action='view'):
    token = build_protected_media_token(kind, object_id, action=action)
    return reverse('protected-media', kwargs={'kind': kind, 'object_id': int(object_id), 'action': action, 'token': token})
