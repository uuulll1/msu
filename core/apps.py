from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Общие компоненты: главная, «О проекте», Markdown, служебные команды."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Ядро сайта"
