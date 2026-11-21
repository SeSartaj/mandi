from django.contrib import admin

from apps.core.admin import AuditFieldsAdminMixin

from .models import Checklist


@admin.register(Checklist)
class ChecklistAdmin(AuditFieldsAdminMixin, admin.ModelAdmin):
    list_display = ("code", "name", "establishment_kind", "allows_all_types")
    list_filter = ("establishment_kind", "allows_all_types")
    search_fields = ("code", "name")
