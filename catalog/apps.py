from django.apps import AppConfig


class CatalogConfig(AppConfig):
    """Учебная иерархия: факультет → специальность → курс → семестр → предмет."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "catalog"
    verbose_name = "Учебная структура"
