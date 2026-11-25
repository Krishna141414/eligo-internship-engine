from django.urls import path

from recommendations import views

app_name = "recommendations"
urlpatterns = [
    path("recommendations/", views.recommendation_list, name="list"),
    path("recommendations/<int:pk>/", views.recommendation_detail, name="detail"),
    path("job-role/", views.job_role, name="job_role"),
]
