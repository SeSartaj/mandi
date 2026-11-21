from django.db import migrations

REMOVED = [
    ("inspections", "inspection"),
]


def clean(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    alias = schema_editor.connection.alias
    for app_label, model in REMOVED:
        stale = Permission.objects.using(alias).filter(
            content_type__app_label=app_label, content_type__model=model
        )
        for group in Group.objects.using(alias).all():
            group.permissions.remove(*stale)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_predefined_groups"),
        ("inspections", "0004_remove_inspection_approved_by_and_more"),
    ]

    operations = [migrations.RunPython(clean, migrations.RunPython.noop)]
