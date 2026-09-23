from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.faculty_list, name="faculty_list"),
    path("<slug:faculty>/", views.faculty_detail, name="faculty"),
    # Предметы — отдельный префикс, чтобы не пересекаться со slug'ами специальностей
    path("<slug:faculty>/subjects/<slug:subject>/", views.subject_detail, name="subject"),
    path("<slug:faculty>/<slug:specialty>/", views.specialty_detail, name="specialty"),
    path("<slug:faculty>/<slug:specialty>/<int:course>/", views.course_detail, name="course"),
    path(
        "<slug:faculty>/<slug:specialty>/<int:course>/<int:semester>/",
        views.semester_detail,
        name="semester",
    ),
]
