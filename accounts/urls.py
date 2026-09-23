from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.PortalLoginView.as_view(), name="login"),
    path("logout/", views.PortalLogoutView.as_view(), name="logout"),
    path("password/", views.PortalPasswordChangeView.as_view(), name="password_change"),
    path("password/done/", views.PortalPasswordChangeDoneView.as_view(), name="password_change_done"),
    path("settings/", views.profile_edit, name="profile_edit"),
    path("u/<str:username>/", views.profile, name="profile"),
]
