from django.urls import path

from students import views

app_name = "students"
urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile_edit, name="profile_edit"),
    path("account/", views.account_edit, name="account_edit"),
]
