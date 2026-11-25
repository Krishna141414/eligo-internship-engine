from django.contrib import admin

from recommendations.models import InternshipRecommendation, JobRolePrediction

admin.site.register([InternshipRecommendation, JobRolePrediction])
