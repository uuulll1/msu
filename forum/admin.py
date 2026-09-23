"""Админка форума."""
from django.contrib import admin

from .models import Post, Topic


class PostInline(admin.StackedInline):
    model = Post
    extra = 0
    fields = ("author", "body", "reply_to", "is_hidden", "is_edited")
    raw_id_fields = ("author", "reply_to")
    show_change_link = True


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "author", "created_at", "last_activity_at", "is_pinned", "is_locked")
    list_filter = ("is_pinned", "is_locked", "subject__faculty", "subject")
    list_editable = ("is_pinned", "is_locked")
    search_fields = ("title", "author__username")
    autocomplete_fields = ("subject", "author")
    inlines = [PostInline]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("__str__", "author", "created_at", "is_hidden")
    list_filter = ("is_hidden", "created_at")
    list_editable = ("is_hidden",)
    search_fields = ("body", "author__username", "topic__title")
    raw_id_fields = ("topic", "author", "reply_to")
    actions = ["hide", "show"]

    @admin.action(description="Скрыть выбранные сообщения")
    def hide(self, request, queryset):
        queryset.update(is_hidden=True)

    @admin.action(description="Показать выбранные сообщения")
    def show(self, request, queryset):
        queryset.update(is_hidden=False)
