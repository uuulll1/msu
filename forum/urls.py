from django.urls import path

from . import views

app_name = "forum"

urlpatterns = [
    path("", views.index, name="index"),
    path("topic/<int:pk>/", views.topic_detail, name="topic"),
    path("post/<int:pk>/edit/", views.edit_post, name="edit_post"),
    path("<slug:faculty>/<slug:subject>/", views.subject_forum, name="subject"),
    path("<slug:faculty>/<slug:subject>/new/", views.new_topic, name="new_topic"),
]
