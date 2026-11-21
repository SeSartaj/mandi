import json
from pathlib import Path

from django.db import migrations, models

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _read(name):
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def populate_local_names(apps, schema_editor):
    Province = apps.get_model("core", "Province")
    District = apps.get_model("core", "District")
    alias = schema_editor.connection.alias

    for record in _read("afghanistan-provinces.json"):
        code = (record.get("code") or {}).get("id") or record["id"]
        local = (record.get("name") or {}).get("local", "").strip()
        if code and local:
            Province.objects.using(alias).filter(code=code).update(name_local=local)

    for record in _read("afghanistan-districts.json"):
        code = (record.get("code") or {}).get("id") or record["id"]
        local = (record.get("name") or {}).get("local", "").strip()
        if code and local:
            District.objects.using(alias).filter(code=code).update(name_local=local)


class Migration(migrations.Migration):
    dependencies = [("core", "0002_seed_afghanistan")]

    operations = [
        migrations.AddField(
            model_name="province",
            name="name_local",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="district",
            name="name_local",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.RunPython(populate_local_names, migrations.RunPython.noop),
    ]
