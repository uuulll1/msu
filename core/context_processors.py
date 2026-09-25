"""Переменные, доступные во всех шаблонах."""
from django.conf import settings
from django.utils.functional import SimpleLazyObject


def _static_version():
    """
    Версия статики для адресов вида main.css?v=...: меняется при изменении
    любого нашего CSS/JS, поэтому браузер (особенно Safari) не держит старый кэш.
    """
    latest = 0
    static_dir = settings.BASE_DIR / "static"
    for folder in ("css", "js"):
        for path in (static_dir / folder).glob("*"):
            latest = max(latest, int(path.stat().st_mtime))
    return str(latest)


def site_context(request):
    return {
        "STATIC_VERSION": _static_version() if settings.DEBUG else settings.STATIC_VERSION_PROD,
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
