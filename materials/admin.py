"""
Админка материалов — основной инструмент модераторов.

Новые материалы получают статус «На проверке». Модератор открывает
раздел «Материалы» с фильтром по статусу и одобряет/отклоняет их
массовыми действиями или вручную в карточке.
"""
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html

from .models import Comment, Material, MaterialLike, Tag


class StatusFilter(admin.SimpleListFilter):
    """Фильтр по статусу с «На проверке» по умолчанию в подсказке."""

    title = "статус"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return Material.Status.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(status=self.value())
        return queryset


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "subject",
        "material_type",
        "author",
        "created_at",
        "status_badge",
        "downloads_count",
        "file_link",
    )
    list_filter = (StatusFilter, "material_type", "subject__faculty", "subject")
    search_fields = ("title", "teacher", "subject__name", "author__username", "tags__name")
    autocomplete_fields = ("subject", "tags", "author")
    readonly_fields = (
        "original_filename",
        "file_size",
        "downloads_count",
        "created_at",
        "updated_at",
        "moderated_by",
        "moderated_at",
    )
    date_hierarchy = "created_at"
    list_per_page = 50
    actions = ["approve", "reject", "return_to_pending"]
    fieldsets = (
        (None, {"fields": ("title", "subject", "semester", "material_type", "teacher", "academic_year")}),
        ("Содержимое", {"fields": ("description", "file", "original_filename", "file_size", "tags")}),
        (
            "Модерация",
            {"fields": ("status", "moderation_note", "moderated_by", "moderated_at")},
        ),
        ("Служебное", {"fields": ("author", "downloads_count", "created_at", "updated_at")}),
    )

    @admin.display(description="статус", ordering="status")
    def status_badge(self, obj):
        colors = {
            Material.Status.PENDING: "#b7791f",
            Material.Status.APPROVED: "#2f855a",
            Material.Status.REJECTED: "#c53030",
        }
        return format_html(
            '<strong style="color:{}">{}</strong>', colors.get(obj.status, "#333"), obj.get_status_display()
        )

    @admin.display(description="файл")
    def file_link(self, obj):
        if not obj.pk:
            return "—"
        return format_html('<a href="{}" target="_blank" rel="noopener">открыть</a>', obj.get_absolute_url())

    def _set_status(self, request, queryset, status, text):
        updated = queryset.update(status=status, moderated_by=request.user, moderated_at=timezone.now())
        self.message_user(request, f"{text}: {updated}", messages.SUCCESS)

    @admin.action(description="Одобрить выбранные материалы", permissions=["change"])
    def approve(self, request, queryset):
        self._set_status(request, queryset, Material.Status.APPROVED, "Одобрено")

    @admin.action(description="Отклонить выбранные материалы", permissions=["change"])
    def reject(self, request, queryset):
        self._set_status(request, queryset, Material.Status.REJECTED, "Отклонено")

    @admin.action(description="Вернуть на проверку", permissions=["change"])
    def return_to_pending(self, request, queryset):
        self._set_status(request, queryset, Material.Status.PENDING, "Возвращено на проверку")

    def save_model(self, request, obj, form, change):
        # Фиксируем, кто и когда поменял статус вручную
        if change and "status" in form.changed_data:
            obj.moderated_by = request.user
            obj.moderated_at = timezone.now()
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.rebuild_search_text(save=True)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("__str__", "author", "material", "created_at", "is_hidden")
    list_filter = ("is_hidden", "created_at")
    list_editable = ("is_hidden",)
    search_fields = ("body", "author__username", "material__title")
    autocomplete_fields = ("author", "material")
    actions = ["hide", "show"]

    @admin.action(description="Скрыть выбранные комментарии")
    def hide(self, request, queryset):
        queryset.update(is_hidden=True)

    @admin.action(description="Показать выбранные комментарии")
    def show(self, request, queryset):
        queryset.update(is_hidden=False)


@admin.register(MaterialLike)
class MaterialLikeAdmin(admin.ModelAdmin):
    list_display = ("material", "user", "created_at")
    search_fields = ("material__title", "user__username")
    autocomplete_fields = ("material", "user")
