"""Корневые маршруты проекта."""
from django.contrib import admin
from django.urls import include, path

# Оформление админки
admin.site.site_header = "Конспектариум — администрирование"
admin.site.site_title = "Конспектариум"
admin.site.index_title = "Модерация и управление контентом"

urlpatterns = [
    path("", include("core.urls")),
    path("f/", include("catalog.urls")),
    path("materials/", include("materials.urls")),
    path("forum/", include("forum.urls")),
    path("accounts/", include("accounts.urls")),
    path("admin/", admin.site.urls),
]

handler403 = "core.views.error_403"
handler404 = "core.views.error_404"
handler500 = "core.views.error_500"
