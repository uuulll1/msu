from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Пользователи: регистрация, вход, профиль."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Пользователи"
