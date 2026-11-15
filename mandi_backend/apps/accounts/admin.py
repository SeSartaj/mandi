from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class AccountAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Employee", {"fields": ("display_name", "position")}),
        ("Checklist access", {"fields": ("restrict_checklist_access", "allowed_checklists")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Roles", {"fields": ("groups",)}),
        ("Employee", {"fields": ("display_name", "position")}),
        ("Checklist access", {"fields": ("restrict_checklist_access", "allowed_checklists")}),
    )
    filter_horizontal = UserAdmin.filter_horizontal + ("allowed_checklists",)
    list_display = (
        "username",
        "display_name",
        "position",
        "is_staff",
        "is_active",
        "restrict_checklist_access",
        "is_superuser",
    )
    list_filter = UserAdmin.list_filter + ("groups",)
    search_fields = ("username", "display_name", "position", "email")

