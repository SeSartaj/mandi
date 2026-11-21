import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import Country, District, Province

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _read(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def seed_afghanistan(country_model=None, province_model=None, district_model=None):
    """Upsert the 34 Afghan provinces and their districts by English name (idempotent)."""
    Country_ = country_model or Country
    Province_ = province_model or Province
    District_ = district_model or District

    provinces = _read("afghanistan-provinces.json")
    districts = _read("afghanistan-districts.json")

    country, _ = Country_.objects.get_or_create(
        code="AF", defaults={"name": "Afghanistan"}
    )
    by_dataset_id = {}
    for record in provinces:
        name = (record.get("name") or {}).get("en", "").strip()
        local = (record.get("name") or {}).get("local", "").strip()
        code = (record.get("code") or {}).get("id") or record["id"]
        if not name:
            continue
        province = Province_.objects.filter(
            country=country, name__iexact=name
        ).first()
        if province is None:
            province = Province_.objects.create(
                country=country, code=code, name=name, name_local=local, is_active=True
            )
        elif (
            province.code != code
            or province.name_local != local
            or not province.is_active
        ):
            province.code = code
            province.name_local = local
            province.is_active = True
            province.save(update_fields=["code", "name_local", "is_active"])
        by_dataset_id[record["id"]] = province

    created_districts = 0
    for record in districts:
        name = (record.get("name") or {}).get("en", "").strip()
        parent_id = (record.get("parent") or {}).get("id")
        if not parent_id:
            parent_id = next(
                (item.get("id") for item in record.get("ancestors") or []), None
            )
        province = by_dataset_id.get(parent_id)
        code = (record.get("code") or {}).get("id") or record["id"]
        local = (record.get("name") or {}).get("local", "").strip()
        if not name or province is None:
            continue
        _, created = District_.objects.update_or_create(
            province=province,
            name__iexact=name,
            defaults={
                "name": name,
                "name_local": local,
                "code": code,
                "is_active": True,
            },
        )
        created_districts += int(created)

    return len(by_dataset_id), created_districts


class Command(BaseCommand):
    help = "Seed all 34 Afghan provinces and their 401 districts (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        provinces, created = seed_afghanistan()
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {provinces} provinces; {created} new districts."
            )
        )
