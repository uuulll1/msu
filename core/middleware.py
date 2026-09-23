"""Дополнительные заголовки безопасности."""
from django.conf import settings

# Политика безопасности содержимого: разрешаем только собственные скрипты
# (KaTeX лежит в static/vendor) и шрифты Google Fonts.
# Инлайновые <script> запрещены — даже если XSS-фильтр пропустит тег,
# браузер его не выполнит.
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        # KaTeX расставляет style-атрибуты, поэтому 'unsafe-inline' для стилей
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' data: https://fonts.gstatic.com",
        "img-src 'self' data:",
        "frame-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


class SecurityHeadersMiddleware:
    """Добавляет Content-Security-Policy и Permissions-Policy к HTML-ответам."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Админку Django не трогаем: у неё свои скрипты
        if request.path.startswith("/admin/"):
            return response
        content_type = response.get("Content-Type", "")
        if content_type.startswith("text/html") and not settings.DEBUG_CSP_DISABLED:
            response.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response
