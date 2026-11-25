from django.urls import path

from assessments import views

app_name = "assessments"
urlpatterns = [
    path("assessments/", views.assessment_list, name="list"),
    path("assessments/<int:pk>/start/", views.start, name="start"),
    path("attempts/<int:pk>/", views.exam, name="exam"),
    path("attempts/<int:pk>/answer/", views.save_answer, name="save_answer"),
    path("attempts/<int:pk>/submit/", views.submit, name="submit"),
    path("attempts/<int:pk>/result/", views.result, name="result"),
    path("manage/assessments/", views.admin_list, name="admin_list"),
    path("manage/assessments/add/", views.admin_add, name="admin_add"),
    path("manage/assessments/<int:pk>/edit/", views.admin_edit, name="admin_edit"),
    path("manage/assessments/<int:pk>/toggle/", views.admin_toggle, name="admin_toggle"),
    path("manage/assessments/<int:pk>/questions/", views.questions, name="questions"),
    path("manage/assessments/<int:pk>/questions/add/", views.question_add, name="question_add"),
    path("manage/questions/<int:pk>/edit/", views.question_edit, name="question_edit"),
    path("manage/questions/<int:pk>/delete/", views.question_delete, name="question_delete"),
]
