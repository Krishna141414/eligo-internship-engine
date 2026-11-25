from django.contrib import admin

from internships.models import Internship


@admin.register(Internship)
class InternshipAdmin(admin.ModelAdmin):
    list_display = ("internship_title", "company_name", "location", "status")
    list_filter = ("status", "work_mode")
    search_fields = ("internship_title", "company_name", "location")
