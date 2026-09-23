from django.apps import AppConfig


class ForumConfig(AppConfig):
    """Форум: у каждого предмета своя ветка обсуждений."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "forum"
    verbose_name = "Форум"
