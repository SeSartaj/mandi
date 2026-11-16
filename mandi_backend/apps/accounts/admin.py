from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class AccountAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Employee", {"fields": ("display_name", "position")}),
        (
            "Checklist access",
            {"fields": ("restrict_checklist_access", "allowed_checklists")},
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Roles", {"fields": ("groups",)}),
        ("Employee", {"fields": ("display_name", "position")}),
        (
            "Checklist access",
            {"fields": ("restrict_checklist_access", "allowed_checklists")},
        ),
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


# Keep the admin path consistent with the account API: remote credentials must
# be revoked explicitly before narrowing local access.
from django.contrib.auth.forms import UserChangeForm
from django.core.exceptions import ValidationError


class ManagedUserChangeForm(UserChangeForm):
    def clean(self):
        values = super().clean()
        access_fields = {
            "is_active",
            "groups",
            "restrict_checklist_access",
            "allowed_checklists",
        }
        if self.instance.pk and access_fields.intersection(self.changed_data):
            from apps.integrations.models import CollectorGrant

            if CollectorGrant.objects.filter(user=self.instance, active=True).exists():
                raise ValidationError(
                    "Revoke this employee's ODK Collect access in Mandi before changing their access."
                )
        return values


AccountAdmin.form = ManagedUserChangeForm
