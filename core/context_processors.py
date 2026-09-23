"""Переменные, доступные во всех шаблонах."""
from django.conf import settings


def site_context(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_TAGLINE": settings.SITE_TAGLINE,
        "SITE_DISCLAIMER": settings.SITE_DISCLAIMER,
    }
