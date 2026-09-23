"""Админка пользователей."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "specialty", "study_year", "is_staff", "is_active", "date_joined")
    list_filter = BaseUserAdmin.list_filter + ("specialty",)
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Учёба", {"fields": ("specialty", "study_year", "bio")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Контакты", {"fields": ("email",)}),
    )
