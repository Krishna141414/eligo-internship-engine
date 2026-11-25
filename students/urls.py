from django.urls import path

from students import views

app_name = "students"
urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
]
