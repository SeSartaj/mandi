from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class AccountAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Employee", {"fields": ("display_name", "position")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Employee", {"fields": ("display_name", "position")}),
    )
    list_display = (
        "username",
        "display_name",
        "position",
        "is_staff",
        "is_active",
        "is_superuser",
    )
    list_filter = UserAdmin.list_filter + ("groups",)
    search_fields = ("username", "display_name", "position", "email")

