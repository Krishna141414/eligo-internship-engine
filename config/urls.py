from django.contrib import admin
from django.templatetags.static import static
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # Browsers ask for /favicon.ico on pages that don't link an icon (e.g. Django's debug 404 page).
    path("favicon.ico", RedirectView.as_view(url=static("img/favicon.svg"), permanent=True)),
    path("", include("accounts.urls")),
    path("student/", include("students.urls")),
    path("", include("internships.urls")),
    path("", include("assessments.urls")),
    path("", include("recommendations.urls")),
    path("manage/", include("adminpanel.urls")),
    path("django-admin/", admin.site.urls),
]

handler403 = "config.views.permission_denied"
handler404 = "config.views.page_not_found"
