import logging
import time

logger = logging.getLogger('raiz.security')


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time

        response.headers.setdefault(
            'Content-Security-Policy',
            "default-src 'self'; img-src 'self' data: https: blob:; media-src 'self' blob:; style-src 'self'; script-src 'self'; "
            "font-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'",
        )
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.headers.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        if request.user.is_authenticated:
            response.headers.setdefault('Cache-Control', 'private, no-store, max-age=0')

        # Log suspeitas de segurança
        if response.status_code >= 400:
            log_level = logging.WARNING if response.status_code < 500 else logging.ERROR
            logger.log(
                log_level,
                f'{response.status_code} {request.method} {request.path}',
                extra={
                    'user_id': request.user.id if request.user.is_authenticated else None,
                    'ip': request.META.get('REMOTE_ADDR'),
                    'duration_ms': int(duration * 1000),
                }
            )

        return response
