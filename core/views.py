"""Главная страница, «О проекте» и обработчики ошибок."""
from django.db.models import Count, Q
from django.shortcuts import render

from catalog.models import Specialty, Subject
from forum.models import Post, Topic
from materials.models import Material


def home(request):
    approved = (
        Material.objects.approved()
        .filter(subject__is_active=True)
        .select_related("subject__faculty", "semester__course__specialty", "author")
        .prefetch_related("tags")
        .with_counts()
    )
    specialties = (
        Specialty.objects.active()
        .filter(faculty__is_active=True)
        .select_related("faculty")
        .annotate(
            materials_total=Count(
                "courses__semesters__materials",
                filter=Q(courses__semesters__materials__status=Material.Status.APPROVED),
                distinct=True,
            )
        )
        .order_by("faculty__order", "order")
    )
    active_topics = (
        Topic.objects.filter(subject__is_active=True)
        .select_related("subject__faculty", "author")
        .annotate(posts_total=Count("posts", filter=Q(posts__is_hidden=False)))
        .order_by("-last_activity_at")[:5]
    )
    stats = {
        "materials": Material.objects.approved().count(),
        "subjects": Subject.objects.active().count(),
        "topics": Topic.objects.count(),
        "posts": Post.objects.filter(is_hidden=False).count(),
    }
    context = {
        "latest": approved.order_by("-created_at")[:6],
        "popular": approved.order_by("-downloads_count", "-created_at")[:6],
        "specialties": specialties,
        "active_topics": active_topics,
        "stats": stats,
    }
    return render(request, "core/home.html", context)


def about(request):
    return render(request, "core/about.html")


def error_404(request, exception):
    return render(request, "errors/404.html", status=404)


def error_403(request, exception):
    return render(request, "errors/403.html", status=403)


def error_500(request):
    # Минимальный контекст: при ошибке сервера БД может быть недоступна
    return render(request, "errors/500.html", status=500)
