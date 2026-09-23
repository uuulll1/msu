"""Представления форума."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, F, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from catalog.models import Faculty, Subject
from core.markdown import quote_markdown

from .forms import PostForm, TopicForm
from .models import POSTS_PER_PAGE, Post, Topic


def _visible_posts():
    return Post.objects.filter(is_hidden=False)


def index(request):
    """Главная форума: ветки всех предметов, сгруппированные по факультетам."""
    faculties = []
    for faculty in Faculty.objects.active():
        subjects = (
            Subject.objects.active()
            .filter(faculty=faculty)
            .annotate(
                topics_total=Count("topics", distinct=True),
                posts_total=Count("topics__posts", filter=Q(topics__posts__is_hidden=False), distinct=True),
                last_activity=Max("topics__last_activity_at"),
            )
            .order_by("name")
        )
        faculties.append((faculty, subjects))

    recent_topics = (
        Topic.objects.filter(subject__is_active=True)
        .select_related("subject__faculty", "author")
        .annotate(posts_total=Count("posts", filter=Q(posts__is_hidden=False)))
        .order_by("-last_activity_at")[:8]
    )
    return render(request, "forum/index.html", {"faculties": faculties, "recent_topics": recent_topics})


def subject_forum(request, faculty, subject):
    """Ветка обсуждений конкретного предмета."""
    subject = get_object_or_404(
        Subject.objects.active().select_related("faculty"), faculty__slug=faculty, slug=subject
    )
    topics = (
        subject.topics.select_related("author")
        .annotate(posts_total=Count("posts", filter=Q(posts__is_hidden=False)))
        .order_by("-is_pinned", "-last_activity_at")
    )
    page = Paginator(topics, 20).get_page(request.GET.get("page"))
    return render(request, "forum/subject.html", {"subject": subject, "page_obj": page})


def _register_view(request, topic):
    """Считаем просмотр темы не чаще одного раза за сессию."""
    viewed = request.session.get("viewed_topics", [])
    if topic.pk not in viewed:
        Topic.objects.filter(pk=topic.pk).update(views_count=F("views_count") + 1)
        viewed = (viewed + [topic.pk])[-200:]
        request.session["viewed_topics"] = viewed


@require_http_methods(["GET", "POST"])
def topic_detail(request, pk):
    topic = get_object_or_404(
        Topic.objects.select_related("subject__faculty", "author").filter(subject__is_active=True), pk=pk
    )
    preview = None
    form = PostForm()

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(topic.get_absolute_url())
        if topic.is_locked and not request.user.is_moderator:
            messages.error(request, "Тема закрыта для новых ответов.")
            return redirect(topic)
        form = PostForm(request.POST)
        reply_to = None
        reply_to_id = request.POST.get("reply_to")
        if reply_to_id and reply_to_id.isdigit():
            reply_to = topic.posts.filter(pk=reply_to_id).first()
        if form.is_valid():
            if "preview" in request.POST:
                preview = form.cleaned_data["body"]
            else:
                with transaction.atomic():
                    post = form.save(commit=False)
                    post.topic = topic
                    post.author = request.user
                    post.reply_to = reply_to
                    post.save()
                    Topic.objects.filter(pk=topic.pk).update(last_activity_at=timezone.now())
                messages.success(request, "Ответ опубликован.")
                return redirect(post.get_absolute_url())
    else:
        _register_view(request, topic)
        # Цитирование: ?quote=<id> подставляет цитату в форму ответа
        quote_id = request.GET.get("quote")
        if quote_id and quote_id.isdigit() and request.user.is_authenticated:
            quoted = _visible_posts().filter(topic=topic, pk=quote_id).select_related("author").first()
            if quoted:
                author = quoted.author.username if quoted.author else "Удалённый пользователь"
                form = PostForm(initial={"body": quote_markdown(quoted.body, author)})
                form.reply_to_id = quoted.pk

    posts = _visible_posts().filter(topic=topic).select_related("author", "reply_to__author")
    page = Paginator(posts, POSTS_PER_PAGE).get_page(request.GET.get("page"))
    first_post_id = _visible_posts().filter(topic=topic).values_list("pk", flat=True).first()

    return render(
        request,
        "forum/topic.html",
        {
            "topic": topic,
            "subject": topic.subject,
            "page_obj": page,
            "form": form,
            "preview": preview,
            "reply_to_id": getattr(form, "reply_to_id", None) or request.POST.get("reply_to", ""),
            "first_post_id": first_post_id,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def new_topic(request, faculty, subject):
    subject = get_object_or_404(
        Subject.objects.active().select_related("faculty"), faculty__slug=faculty, slug=subject
    )
    form = TopicForm(request.POST or None)
    preview = None
    if request.method == "POST" and form.is_valid():
        if "preview" in request.POST:
            preview = form.cleaned_data["body"]
        else:
            with transaction.atomic():
                topic = form.save(commit=False)
                topic.subject = subject
                topic.author = request.user
                topic.save()
                Post.objects.create(topic=topic, author=request.user, body=form.cleaned_data["body"])
            messages.success(request, "Тема создана.")
            return redirect(topic)
    return render(request, "forum/topic_form.html", {"subject": subject, "form": form, "preview": preview})


@login_required
@require_http_methods(["GET", "POST"])
def edit_post(request, pk):
    post = get_object_or_404(Post.objects.select_related("topic__subject__faculty"), pk=pk)
    if not post.can_edit(request.user):
        raise PermissionDenied
    form = PostForm(request.POST or None, instance=post)
    preview = None
    if request.method == "POST" and form.is_valid():
        if "preview" in request.POST:
            preview = form.cleaned_data["body"]
        else:
            post = form.save(commit=False)
            post.is_edited = True
            post.save()
            messages.success(request, "Сообщение изменено.")
            return redirect(post.get_absolute_url())
    return render(request, "forum/post_edit.html", {"post": post, "form": form, "preview": preview})
