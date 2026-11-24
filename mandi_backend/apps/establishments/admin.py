from django.contrib import admin
from .models import Establishment, SourceLink, EstablishmentType, ExternalSystem, RegistrySyncCursor, RegistrySyncRequest


class ReadOnlyAdmin(admin.ModelAdmin):
    """Domain records are visible in admin, but changes must go through services."""

    actions = None
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [
            field.name
            for field in (*self.model._meta.fields, *self.model._meta.many_to_many)
        ]


@admin.register(Establishment)
class EstablishmentAdmin(ReadOnlyAdmin):
    list_display = ("name", "kind", "province", "district", "created_at")
    list_filter = ("kind", "province", "district")
    search_fields = ("name", "address", "province__name", "district__name")
    list_select_related = ("province", "district")
    ordering = ("name",)


@admin.register(SourceLink)
class SourceLinkAdmin(ReadOnlyAdmin):
    list_display = ("establishment", "source", "external_id", "linked_by", "linked_at")
    list_filter = ("source",)
    search_fields = ("establishment__name", "external_id")
    list_select_related = ("establishment", "linked_by")



@admin.register(EstablishmentType)
class EstablishmentTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    readonly_fields = ()

    def get_readonly_fields(self, request, obj=None):
        return ("code",) if obj else ()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ExternalSystem)
class ExternalSystemAdmin(EstablishmentTypeAdmin):
    list_display = ("code", "name", "adapter", "is_active")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if "adapter" in form.base_fields:
            from apps.integrations.registry import ADAPTERS
            form.base_fields["adapter"].help_text = "Installed adapters: " + ", ".join(ADAPTERS) + ". Other codes are unavailable until implemented."
        return form


@admin.register(RegistrySyncCursor)
class RegistrySyncCursorAdmin(ReadOnlyAdmin):
    list_display = ("source", "kind", "next_page", "last_attempt_at", "last_success_at", "last_error")


@admin.register(RegistrySyncRequest)
class RegistrySyncRequestAdmin(ReadOnlyAdmin):
    list_display = ("source", "state", "requested_by", "requested_at", "started_at", "finished_at")
    list_filter = ("source", "state")
