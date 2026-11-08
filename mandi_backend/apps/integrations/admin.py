from django.contrib import admin
from apps.establishments.admin import ReadOnlyAdmin

from .models import KoboSubmission


@admin.register(KoboSubmission)
class KoboSubmissionAdmin(ReadOnlyAdmin):
    list_display = ("establishment", "checklist", "submitted_at", "asset_uid", "submission_id")
    list_filter = ("asset_uid", "checklist")
    search_fields = ("establishment__name", "submission_id", "asset_uid")
    date_hierarchy = "submitted_at"
    list_select_related = ("establishment", "checklist")
