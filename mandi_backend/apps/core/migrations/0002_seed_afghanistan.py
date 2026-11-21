import json
from pathlib import Path

from django.db import migrations

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _read(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def seed_afghanistan(apps, schema_editor):
    Country = apps.get_model("core", "Country")
    Province = apps.get_model("core", "Province")
    District = apps.get_model("core", "District")
    alias = schema_editor.connection.alias

    country, _ = Country.objects.using(alias).get_or_create(
        code="AF", defaults={"name": "Afghanistan"}
    )
    by_dataset_id = {}
    for record in _read("afghanistan-provinces.json"):
        name = (record.get("name") or {}).get("en", "").strip()
        code = (record.get("code") or {}).get("id") or record["id"]
        if not name:
            continue
        province = (
            Province.objects.using(alias)
            .filter(country=country, name__iexact=name)
            .first()
        )
        if province is None:
            province = Province.objects.using(alias).create(
                country=country, code=code, name=name, is_active=True
            )
        elif province.code != code or not province.is_active:
            province.code = code
            province.is_active = True
            province.save(using=alias, update_fields=["code", "is_active"])
        by_dataset_id[record["id"]] = province

    for record in _read("afghanistan-districts.json"):
        name = (record.get("name") or {}).get("en", "").strip()
        parent_id = (record.get("parent") or {}).get("id")
        if not parent_id:
            parent_id = next(
                (item.get("id") for item in record.get("ancestors") or []), None
            )
        province = by_dataset_id.get(parent_id)
        code = (record.get("code") or {}).get("id") or record["id"]
        if not name or province is None:
            continue
        District.objects.using(alias).update_or_create(
            province=province,
            name__iexact=name,
            defaults={"name": name, "code": code, "is_active": True},
        )


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]

    operations = [
        migrations.RunPython(seed_afghanistan, migrations.RunPython.noop),
    ]
