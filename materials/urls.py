from django.urls import path

from . import views

app_name = "materials"

urlpatterns = [
    path("", views.search, name="search"),
    path("upload/", views.upload, name="upload"),
    path("moderation/", views.moderation_queue, name="moderation"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/edit/", views.edit, name="edit"),
    path("<int:pk>/delete/", views.delete, name="delete"),
    path("<int:pk>/download/", views.download, name="download"),
    path("<int:pk>/view/", views.view_file, name="view_file"),
    path("<int:pk>/like/", views.toggle_like, name="like"),
    path("<int:pk>/comment/", views.add_comment, name="comment"),
]
