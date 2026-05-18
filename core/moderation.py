from django.conf import settings


DEFAULT_BLOCKED_TERMS = [
    'spam malicioso',
    'golpe de senha',
    'link de phishing',
]

DEFAULT_SENSITIVE_TERMS = [
    'conteudo adulto',
    'violencia extrema',
]


def blocked_terms():
    configured = getattr(settings, 'RAIZ_BLOCKED_TERMS', [])
    return [term.strip().lower() for term in (configured or DEFAULT_BLOCKED_TERMS) if term.strip()]


def sensitive_terms():
    configured = getattr(settings, 'RAIZ_SENSITIVE_TERMS', [])
    return [term.strip().lower() for term in (configured or DEFAULT_SENSITIVE_TERMS) if term.strip()]


def moderation_findings(text):
    normalized = str(text or '').lower()
    blocked_hits = [term for term in blocked_terms() if term in normalized]
    sensitive_hits = [term for term in sensitive_terms() if term in normalized]
    link_total = normalized.count('http://') + normalized.count('https://')
    repeated_marker = any(token * 4 in normalized for token in ['!!!', '$$', 'kkk', '???'])
    is_spam_like = link_total >= 3 or repeated_marker
    return {
        'blocked_hits': blocked_hits,
        'sensitive_hits': sensitive_hits,
        'is_spam_like': is_spam_like,
        'should_block': bool(blocked_hits or is_spam_like),
        'should_alert': bool(sensitive_hits or blocked_hits or is_spam_like),
    }
