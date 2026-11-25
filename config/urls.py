from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("accounts.urls")),
    path("student/", include("students.urls")),
    path("manage/", include("adminpanel.urls")),
    path("django-admin/", admin.site.urls),
]

handler403 = "config.views.permission_denied"
handler404 = "config.views.page_not_found"
