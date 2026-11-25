from django.urls import path

from adminpanel import views

app_name = "adminpanel"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
