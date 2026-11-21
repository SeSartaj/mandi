from django.contrib import admin
from apps.establishments.admin import ReadOnlyAdmin

from .models import CollectionSubmission, CollectorGrant, FormDeployment


@admin.register(FormDeployment)
class FormDeploymentAdmin(ReadOnlyAdmin):
    list_display = ("checklist", "provider", "project_id", "form_id", "status", "deployed_at")
    list_filter = ("provider", "status")
    search_fields = ("checklist__name", "form_id", "project_id")
    list_select_related = ("checklist",)


@admin.register(CollectionSubmission)
class CollectionSubmissionAdmin(ReadOnlyAdmin):
    def get_queryset(self, request):
        from apps.accounts.services import scope_checklists
        return scope_checklists(
            request.user,
            super().get_queryset(request),
            "deployment__checklist_id",
        )

    list_display = ("establishment", "deployment", "submitted_at", "submission_id")
    list_filter = ("deployment__provider", "deployment__checklist")
    search_fields = ("establishment__name", "submission_id")
    date_hierarchy = "submitted_at"
    list_select_related = ("establishment", "deployment")


@admin.register(CollectorGrant)
class CollectorGrantAdmin(ReadOnlyAdmin):
    list_display = ("user", "deployment", "active", "created_at")
    list_filter = ("active",)
    search_fields = ("user__username", "remote_id")
    list_select_related = ("user", "deployment")
