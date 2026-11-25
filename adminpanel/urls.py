from django.urls import path

from adminpanel import views

app_name = "adminpanel"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("students/", views.students, name="students"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/toggle/", views.student_toggle, name="student_toggle"),
    path("results/", views.results, name="results"),
    path("recommendations/", views.recommendations, name="recommendations"),
    path("recommendations/run/<uuid:run_id>/", views.recommendation_run, name="recommendation_run"),
    path("recommendations/<int:pk>/", views.recommendation_detail, name="recommendation_detail"),
    path("ml/", views.ml, name="ml"),
    path("ml/figures/<str:name>", views.figure, name="figure"),
]
