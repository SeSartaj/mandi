from django.db import migrations


def grant_checklist_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    alias = schema_editor.connection.alias
    group = Group.objects.using(alias).filter(name="Mandi administrators").first()
    if not group:
        return
    content_type, _ = ContentType.objects.using(alias).get_or_create(
        app_label="inspections", model="checklist"
    )
    for codename in ("add_checklist", "change_checklist"):
        permission, _ = Permission.objects.using(alias).get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": codename.replace("_", " ")},
        )
        group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0003_remove_deleted_model_permissions"),
    ]

    operations = [
        migrations.RunPython(grant_checklist_permissions, migrations.RunPython.noop)
    ]
