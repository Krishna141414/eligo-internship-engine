from django.contrib import admin

from accounts.models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "user_type", "status", "registered_date")
    list_filter = ("user_type", "status")
    search_fields = ("email", "name")
    exclude = ("password",)
