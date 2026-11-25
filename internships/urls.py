from django.urls import path

from internships import views

app_name = "internships"
urlpatterns = [
    path("internships/", views.internship_list, name="list"),
    path("internships/<int:pk>/", views.internship_detail, name="detail"),
    path("manage/internships/", views.admin_list, name="admin_list"),
    path("manage/internships/add/", views.admin_add, name="admin_add"),
    path("manage/internships/<int:pk>/edit/", views.admin_edit, name="admin_edit"),
    path("manage/internships/<int:pk>/toggle/", views.admin_toggle, name="admin_toggle"),
]
