"""Представления материалов: поиск, карточка, загрузка, скачивание, оценки."""
import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods, require_POST

from catalog.models import Faculty, Specialty, Subject
from core.utils import normalize_search_text

from .forms import CommentForm, MaterialForm, SearchForm
from .models import Material, MaterialLike, Tag


def _get_visible_material(request, pk):
    """Материал, доступный текущему пользователю, иначе 404."""
    queryset = Material.objects.visible_to(request.user).select_related(
        "subject__faculty", "semester__course__specialty", "author"
    )
    return get_object_or_404(queryset, pk=pk)


def search(request):
    """Каталог материалов с поиском и фильтрами."""
    form = SearchForm(request.GET or None)
    materials = (
        Material.objects.approved()
        .filter(subject__is_active=True)
        .select_related("subject__faculty", "semester__course__specialty", "author")
        .prefetch_related("tags")
        .with_counts()
    )
    active_filters = {}
    sort = "new"

    if form.is_valid():
        data = form.cleaned_data
        query = data.get("q", "").strip()
        if query:
            # Каждое слово запроса должно встречаться в поисковой строке
            for word in normalize_search_text(query).split()[:8]:
                materials = materials.filter(search_text__contains=word)
            active_filters["q"] = query
        if data.get("faculty"):
            materials = materials.filter(subject__faculty__slug=data["faculty"])
            active_filters["faculty"] = Faculty.objects.filter(slug=data["faculty"]).first()
        if data.get("specialty"):
            materials = materials.filter(semester__course__specialty__slug=data["specialty"])
            active_filters["specialty"] = Specialty.objects.filter(slug=data["specialty"]).first()
        if data.get("subject"):
            materials = materials.filter(subject__slug=data["subject"])
            active_filters["subject"] = Subject.objects.filter(slug=data["subject"]).first()
        if data.get("type"):
            materials = materials.filter(material_type=data["type"])
        if data.get("semester"):
            materials = materials.filter(semester__number=data["semester"])
        if data.get("tag"):
            materials = materials.filter(tags__slug=data["tag"])
            active_filters["tag"] = Tag.objects.filter(slug=data["tag"]).first()
        sort = data.get("sort") or "new"

    ordering = {
        "new": ["-created_at"],
        "popular": ["-downloads_count", "-created_at"],
        "likes": ["-likes_total", "-created_at"],
        "title": ["title"],
    }[sort]
    materials = materials.order_by(*ordering).distinct()

    paginator = Paginator(materials, 12)
    page = paginator.get_page(request.GET.get("page"))

    context = {
        "form": form,
        "page_obj": page,
        "total": paginator.count,
        "active_filters": active_filters,
        "faculties": Faculty.objects.active(),
        "specialties": Specialty.objects.active().select_related("faculty"),
        "subjects": Subject.objects.active().select_related("faculty"),
        "popular_tags": Tag.objects.filter(materials__status=Material.Status.APPROVED)
        .distinct()
        .order_by("name")[:30],
    }
    return render(request, "materials/search.html", context)


def detail(request, pk):
    material = _get_visible_material(request, pk)
    comments = material.comments.filter(is_hidden=False).select_related("author")
    likes_total = material.likes.count()
    user_liked = (
        request.user.is_authenticated and material.likes.filter(user=request.user).exists()
    )
    related = (
        Material.objects.approved()
        .filter(subject=material.subject)
        .exclude(pk=material.pk)
        .select_related("subject__faculty")
        .order_by("-downloads_count")[:4]
    )
    context = {
        "material": material,
        "comments": comments,
        "comment_form": CommentForm(),
        "likes_total": likes_total,
        "user_liked": user_liked,
        "related": related,
        "can_edit": material.can_edit(request.user),
        "text_preview": material.read_text_preview() if material.is_text else "",
    }
    return render(request, "materials/detail.html", context)


def _teacher_suggestions():
    return (
        Material.objects.approved()
        .exclude(teacher="")
        .values_list("teacher", flat=True)
        .distinct()
        .order_by("teacher")[:200]
    )


@login_required
@require_http_methods(["GET", "POST"])
def upload(request):
    initial = {}
    # Предзаполнение предмета/семестра, если пришли со страницы предмета
    if request.GET.get("subject"):
        initial["subject"] = Subject.objects.filter(pk=request.GET["subject"]).first()
    if request.GET.get("semester"):
        initial["semester"] = request.GET["semester"]

    form = MaterialForm(request.POST or None, request.FILES or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            material = form.save(commit=False)
            material.author = request.user
            material.original_filename = request.FILES["file"].name[:255]
            # Модераторы публикуют сразу, остальные — через проверку
            if request.user.is_moderator:
                material.status = Material.Status.APPROVED
                material.moderated_by = request.user
                material.moderated_at = timezone.now()
            else:
                material.status = Material.Status.PENDING
            material.save()
            form.save_tags(material)
        if material.is_approved:
            messages.success(request, "Материал опубликован.")
        else:
            messages.info(
                request,
                "Спасибо! Материал отправлен на проверку и появится на сайте после одобрения модератором.",
            )
        return redirect(material)
    return render(
        request,
        "materials/form.html",
        {"form": form, "teacher_suggestions": _teacher_suggestions(), "is_edit": False},
    )


@login_required
@require_http_methods(["GET", "POST"])
def edit(request, pk):
    material = _get_visible_material(request, pk)
    if not material.can_edit(request.user):
        raise PermissionDenied
    old_file_name = material.file.name
    form = MaterialForm(request.POST or None, request.FILES or None, instance=material)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            material = form.save(commit=False)
            new_file = request.FILES.get("file")
            if new_file:
                material.original_filename = new_file.name[:255]
            # После правки автором материал снова уходит на проверку
            if not request.user.is_moderator:
                material.status = Material.Status.PENDING
            material.save()
            form.save_tags(material)
        # Старый файл удаляем, только если его заменили
        if new_file and old_file_name and old_file_name != material.file.name:
            material.file.storage.delete(old_file_name)
        messages.success(
            request,
            "Изменения сохранены."
            + ("" if material.is_approved else " Материал снова отправлен на проверку."),
        )
        return redirect(material)
    return render(
        request,
        "materials/form.html",
        {
            "form": form,
            "material": material,
            "teacher_suggestions": _teacher_suggestions(),
            "is_edit": True,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def delete(request, pk):
    material = _get_visible_material(request, pk)
    if not material.can_edit(request.user):
        raise PermissionDenied
    if request.method == "POST":
        subject = material.subject
        material.delete()
        messages.success(request, "Материал удалён.")
        return redirect(subject)
    return render(request, "materials/confirm_delete.html", {"material": material})


def _file_response(material, as_attachment):
    try:
        handle = material.file.open("rb")
    except (FileNotFoundError, OSError):
        raise Http404("Файл не найден")
    content_type, _ = mimetypes.guess_type(material.download_filename)
    if material.is_text:
        # Текстовые файлы отдаём как text/plain, чтобы браузер ничего не исполнял
        content_type = "text/plain; charset=utf-8"
    response = FileResponse(
        handle,
        as_attachment=as_attachment,
        filename=material.download_filename,
        content_type=content_type or "application/octet-stream",
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, max-age=3600"
    return response


def download(request, pk):
    """Скачивание файла с увеличением счётчика."""
    material = _get_visible_material(request, pk)
    Material.objects.filter(pk=material.pk).update(downloads_count=F("downloads_count") + 1)
    return _file_response(material, as_attachment=True)


@xframe_options_sameorigin
def view_file(request, pk):
    """Встроенный просмотр (PDF во фрейме, изображения). Счётчик не увеличивает."""
    material = _get_visible_material(request, pk)
    if not (material.is_pdf or material.is_image):
        raise Http404("Для этого типа файла встроенный просмотр недоступен")
    return _file_response(material, as_attachment=False)


@login_required
@require_POST
def toggle_like(request, pk):
    material = _get_visible_material(request, pk)
    if not material.is_approved:
        messages.error(request, "Оценивать можно только опубликованные материалы.")
        return redirect(material)
    like, created = MaterialLike.objects.get_or_create(material=material, user=request.user)
    if not created:
        like.delete()
    return redirect(f"{material.get_absolute_url()}#rating")


@login_required
@require_POST
def add_comment(request, pk):
    material = _get_visible_material(request, pk)
    if not material.is_approved:
        messages.error(request, "Комментировать можно только опубликованные материалы.")
        return redirect(material)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.material = material
        comment.author = request.user
        comment.save()
        messages.success(request, "Комментарий добавлен.")
        return redirect(f"{material.get_absolute_url()}#comment-{comment.pk}")
    messages.error(request, "Комментарий не может быть пустым.")
    return redirect(f"{material.get_absolute_url()}#comments")


@login_required
def moderation_queue(request):
    """Очередь модерации для модераторов (одобрение — в админке)."""
    if not request.user.is_moderator:
        raise PermissionDenied
    pending = (
        Material.objects.pending()
        .select_related("subject__faculty", "author")
        .order_by("created_at")
    )
    return render(request, "materials/moderation.html", {"pending": pending})
