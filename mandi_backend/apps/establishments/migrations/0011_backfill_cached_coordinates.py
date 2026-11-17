import math
from django.db import migrations


def backfill(apps, schema_editor):
    Establishment = apps.get_model("establishments", "Establishment")
    SourceLink = apps.get_model("establishments", "SourceLink")
    alias = schema_editor.connection.alias
    for link in SourceLink.objects.using(alias).filter(is_primary=True).iterator(chunk_size=500):
        location = link.details.get("location")
        if not isinstance(location, dict):
            continue
        try:
            lat, lon = float(location["latitude"]), float(location["longitude"])
        except (KeyError, TypeError, ValueError, OverflowError):
            continue
        if math.isfinite(lat) and math.isfinite(lon) and abs(lat) <= 90 and abs(lon) <= 180:
            Establishment.objects.using(alias).filter(pk=link.establishment_id).update(latitude=lat, longitude=lon)


class Migration(migrations.Migration):
    dependencies = [("establishments", "0010_establishment_latitude_establishment_longitude")]
    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
