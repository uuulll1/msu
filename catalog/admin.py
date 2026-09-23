"""Админка учебной структуры."""
from django.contrib import admin, messages

from .models import Course, Faculty, Semester, Specialty, Subject


class SpecialtyInline(admin.TabularInline):
    model = Specialty
    extra = 0
    fields = ("name", "short_name", "slug", "degree", "duration_years", "order", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    show_change_link = True


@admin.register(Faculty)
class FacultyAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "slug", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name", "short_name")
    prepopulated_fields = {"slug": ("short_name",)}
    inlines = [SpecialtyInline]


class CourseInline(admin.TabularInline):
    model = Course
    extra = 0
    show_change_link = True


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "faculty", "degree", "duration_years", "order", "is_active")
    list_filter = ("faculty", "degree", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name", "short_name", "code")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CourseInline]
    actions = ["create_structure"]

    @admin.action(description="Создать курсы и семестры по сроку обучения")
    def create_structure(self, request, queryset):
        total = sum(specialty.ensure_structure() for specialty in queryset)
        self.message_user(request, f"Создано семестров: {total}", messages.SUCCESS)


class SemesterInline(admin.TabularInline):
    model = Semester
    extra = 0
    fields = ("number",)
    show_change_link = True


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("__str__", "specialty", "number")
    list_filter = ("specialty__faculty", "specialty")
    inlines = [SemesterInline]


@admin.register(Semester)
class SemesterAdmin(admin.ModelAdmin):
    list_display = ("__str__", "number", "course", "subjects_count")
    list_filter = ("course__specialty__faculty", "course__specialty", "number")
    filter_horizontal = ("subjects",)

    @admin.display(description="предметов")
    def subjects_count(self, obj):
        return obj.subjects.count()


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "faculty", "slug", "is_active")
    list_filter = ("faculty", "is_active", "semesters__course__specialty")
    list_editable = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
