from django.apps import AppConfig


class MaterialsConfig(AppConfig):
    """Учебные материалы: загрузка, модерация, просмотр, поиск."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "materials"
    verbose_name = "Материалы"

    def ready(self):
        # Подключаем обработчики сигналов (обновление поискового индекса)
        from . import signals  # noqa: F401
