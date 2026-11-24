"""Registries send local province names, so the catalog ended up with pairs.

Example: the seeded `Kabul` row (with `name_local="کابل"`) plus a `کابل` row
created by a registry sync. Filtering by either one only half of the records.
This merges the pairs onto the curated catalog row.
"""

from django.db import migrations


def _norm(value):
    return (value or "").strip().casefold()


def _merge_provinces(apps):
    Country = apps.get_model("core", "Country")
    Province = apps.get_model("core", "Province")
    District = apps.get_model("core", "District")
    Establishment = apps.get_model("establishments", "Establishment")

    for country in Country.objects.all():
        provinces = list(Province.objects.filter(country=country))
        by_name = {}
        for province in sorted(provinces, key=lambda row: (not row.code, row.pk)):
            keys = {_norm(province.name), _norm(province.name_local)} - {""}
            target = next((by_name[key] for key in keys if key in by_name), None)
            if target is None:
                for key in keys:
                    by_name[key] = province
                continue
            for key in keys:
                by_name.setdefault(key, target)
            if province.pk == target.pk:
                continue
            District.objects.filter(province=province).update(province=target)
            Establishment.objects.filter(province=province).update(province=target)
            province.delete()


def _merge_districts(apps):
    District = apps.get_model("core", "District")
    Establishment = apps.get_model("establishments", "Establishment")

    province_ids = District.objects.values_list("province_id", flat=True).distinct()
    for province_id in list(province_ids):
        by_name = {}
        for district in sorted(
            District.objects.filter(province_id=province_id), key=lambda row: (not row.code, row.pk)
        ):
            keys = {_norm(district.name), _norm(district.name_local)} - {""}
            target = next((by_name[key] for key in keys if key in by_name), None)
            if target is None:
                for key in keys:
                    by_name[key] = district
                continue
            for key in keys:
                by_name.setdefault(key, target)
            if district.pk == target.pk:
                continue
            Establishment.objects.filter(district=district).update(district=target)
            district.delete()


def merge_locations(apps, schema_editor):
    _merge_provinces(apps)
    _merge_districts(apps)


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0007_registrysyncrequest"),
        ("core", "0003_local_names"),
    ]

    operations = [migrations.RunPython(merge_locations, migrations.RunPython.noop)]
