from django.contrib import admin

from assessments.models import Answer, Assessment, Attempt, Question

admin.site.register([Assessment, Question, Attempt, Answer])
