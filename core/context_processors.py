"""Переменные, доступные во всех шаблонах."""
from django.conf import settings
from django.utils.functional import SimpleLazyObject


def site_context(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_TAGLINE": settings.SITE_TAGLINE,
        "SITE_DISCLAIMER": settings.SITE_DISCLAIMER,
        # Для полноэкранного меню; запрос к БД выполняется, только если шаблон его использует
        "nav_specialties": SimpleLazyObject(_nav_specialties),
    }


def _nav_specialties():
    from catalog.models import Specialty

    return list(
        Specialty.objects.active()
        .filter(faculty__is_active=True)
        .select_related("faculty")
        .order_by("faculty__order", "order")
    )
