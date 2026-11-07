from django.contrib import admin
from . import services
from .models import Checklist, Inspection


class AddOnlyAdmin(admin.ModelAdmin):
    """Allow creating a record, but not silently editing an existing one."""

    actions = None

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    fields = ("name", "code", "version", "establishment_kind", "xlsform")
    list_display = ("name", "code", "version", "establishment_kind")
    list_filter = ("establishment_kind",)
    search_fields = ("name", "code", "version")
    ordering = ("name", "version")

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        saved = services.save_checklist(
            request.user,
            form.cleaned_data,
            obj.pk if change else None,
        )
        obj.pk = saved.pk
        obj._state.adding = False


@admin.register(Inspection)
class InspectionAdmin(AddOnlyAdmin):
    fields = (
        "establishment",
        "checklist",
        "inspected_on",
        "kind",
        "team",
        "provider",
        "provider_form_id",
        "submission_id",
        "mapping_version",
        "summary",
    )
    list_display = (
        "establishment",
        "inspected_on",
        "kind",
        "approved",
        "is_demo",
        "provider",
    )
    list_filter = ("kind", "approved", "is_demo", "provider", "checklist")
    search_fields = ("establishment__name", "submission_id", "provider_form_id")
    date_hierarchy = "inspected_on"
    list_select_related = ("establishment", "checklist", "approved_by")

    def save_model(self, request, obj, form, change):
        data = form.cleaned_data
        created = services.create_manual_inspection(
            request.user,
            establishment=data["establishment"],
            checklist=data["checklist"],
            inspected_on=data["inspected_on"],
            kind=data["kind"],
            team=data["team"],
            provider=data["provider"],
            provider_form_id=data["provider_form_id"],
            submission_id=data["submission_id"],
            mapping_version=data["mapping_version"],
            summary=data.get("summary") or {},
        )
        obj.pk = created.pk
    list_select_related = ("establishment",)


