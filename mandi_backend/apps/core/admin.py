from django.contrib import admin

from .models import Country, District, Province


class AuditFieldsAdminMixin:
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Country)
class CountryAdmin(AuditFieldsAdminMixin, admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "updated_at", "updated_by")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("name",)


@admin.register(Province)
class ProvinceAdmin(AuditFieldsAdminMixin, admin.ModelAdmin):
    list_display = ("name", "code", "country", "is_active", "updated_at", "updated_by")
    list_filter = ("country", "is_active")
    search_fields = ("name", "code", "country__name")
    list_select_related = ("country", "updated_by")
    ordering = ("country__name", "name")


@admin.register(District)
class DistrictAdmin(AuditFieldsAdminMixin, admin.ModelAdmin):
    list_display = ("name", "code", "province", "is_active", "updated_at", "updated_by")
    list_filter = ("province__country", "province", "is_active")
    search_fields = ("name", "code", "province__name", "province__country__name")
    list_select_related = ("province", "province__country", "updated_by")
    ordering = ("province__name", "name")
