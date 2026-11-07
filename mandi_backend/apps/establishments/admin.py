from django.contrib import admin
from .models import Establishment, SourceLink


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
    list_filter = ("kind", "province")
    search_fields = ("name", "province", "district", "address", "phone")
    ordering = ("name",)


@admin.register(SourceLink)
class SourceLinkAdmin(ReadOnlyAdmin):
    list_display = ("establishment", "source", "external_id", "is_demo", "linked_by", "linked_at")
    list_filter = ("source", "is_demo")
    search_fields = ("establishment__name", "external_id")
    list_select_related = ("establishment", "linked_by")

