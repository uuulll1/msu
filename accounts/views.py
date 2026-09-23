"""Регистрация, вход, профиль."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from forum.models import Topic
from materials.models import Material

from .forms import LoginForm, ProfileForm, SignUpForm
from .models import User


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("core:home")
    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, f"Добро пожаловать, {user.username}! Аккаунт создан.")
        return redirect("core:home")
    return render(request, "accounts/signup.html", {"form": form})


class PortalLoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class PortalLogoutView(auth_views.LogoutView):
    """Выход только POST-запросом (защита от CSRF-выхода по ссылке)."""


class PortalPasswordChangeView(auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:password_change_done")


class PortalPasswordChangeDoneView(auth_views.PasswordChangeDoneView):
    template_name = "accounts/password_change_done.html"


def profile(request, username):
    """Публичный профиль: загрузки пользователя и его темы на форуме."""
    profile_user = get_object_or_404(User.objects.select_related("specialty__faculty"), username=username)
    is_owner = request.user.is_authenticated and request.user.pk == profile_user.pk

    materials_qs = Material.objects.filter(author=profile_user).select_related(
        "subject__faculty", "semester"
    ).prefetch_related("tags")
    if not is_owner:
        # Чужие непроверенные материалы не показываем
        materials_qs = materials_qs.approved()

    paginator = Paginator(materials_qs.order_by("-created_at"), 12)
    page = paginator.get_page(request.GET.get("page"))

    topics = (
        Topic.objects.filter(author=profile_user, subject__is_active=True)
        .select_related("subject__faculty")
        .order_by("-created_at")[:10]
    )
    stats = {
        "materials": Material.objects.filter(author=profile_user).approved().count(),
        "downloads": sum(
            Material.objects.filter(author=profile_user).approved().values_list("downloads_count", flat=True)
        ),
        "posts": profile_user.forum_posts.count(),
    }
    return render(
        request,
        "accounts/profile.html",
        {
            "profile_user": profile_user,
            "is_owner": is_owner,
            "page_obj": page,
            "topics": topics,
            "stats": stats,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def profile_edit(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Профиль обновлён.")
        return redirect(request.user.get_absolute_url())
    return render(request, "accounts/profile_edit.html", {"form": form})
