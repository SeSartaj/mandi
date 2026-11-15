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

    def get_queryset(self, request):
        from apps.accounts.services import scope_checklists
        return scope_checklists(request.user, super().get_queryset(request))

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
    def get_queryset(self, request):
        from apps.accounts.services import scope_checklists
        return scope_checklists(request.user, super().get_queryset(request), "checklist_id")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "checklist":
            from apps.accounts.services import scope_checklists
            kwargs["queryset"] = scope_checklists(request.user, Checklist.objects.all())
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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


