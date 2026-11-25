from django.contrib.auth.views import LogoutView
from django.urls import path

from accounts import views

app_name = "accounts"
urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.EligoLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("password/", views.EligoPasswordChangeView.as_view(), name="password_change"),
]
