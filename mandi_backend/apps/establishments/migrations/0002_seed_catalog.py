from django.db import migrations


def seed_catalog(apps, schema_editor):
    Kind = apps.get_model("establishments", "EstablishmentType")
    System = apps.get_model("establishments", "ExternalSystem")
    for code, name in [
        ("pharmacy", "Pharmacy"),
        ("wholesaler", "Wholesaler"),
        ("importer", "Importer"),
        ("factory", "Factory"),
        ("hospital", "Hospital"),
        ("clinic", "Clinic"),
    ]:
        Kind.objects.get_or_create(code=code, defaults={"name": name})
    for code, name in [
        ("registration", "Registration"),
        ("licensing", "Licensing"),
        ("survey", "Survey"),
        ("archive", "Archive"),
    ]:
        System.objects.get_or_create(code=code, defaults={"name": name, "adapter": code})


class Migration(migrations.Migration):
    dependencies = [("establishments", "0001_initial")]

    operations = [migrations.RunPython(seed_catalog, migrations.RunPython.noop)]
