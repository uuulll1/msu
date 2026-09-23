"""Модель пользователя портала."""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse


class User(AbstractUser):
    """
    Собственная модель пользователя (заведена с самого начала проекта,
    чтобы позже можно было расширять её без сложных миграций).
    """

    email = models.EmailField("электронная почта", unique=True)
    bio = models.TextField("о себе", blank=True, max_length=2000, help_text="Поддерживается Markdown")
    specialty = models.ForeignKey(
        "catalog.Specialty",
        verbose_name="специальность",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    study_year = models.PositiveSmallIntegerField("курс", null=True, blank=True)

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"

    def __str__(self):
        return self.get_username()

    def get_absolute_url(self):
        return reverse("accounts:profile", kwargs={"username": self.username})

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    @property
    def is_moderator(self):
        """Модератор — тот, кто может менять материалы (группа «Модераторы» или суперпользователь)."""
        return self.is_active and (self.is_superuser or self.has_perm("materials.change_material"))
