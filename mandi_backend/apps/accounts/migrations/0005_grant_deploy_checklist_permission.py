from django.db import migrations


def grant_deploy_permission(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    alias = schema_editor.connection.alias
    content_type, _ = ContentType.objects.using(alias).get_or_create(
        app_label="inspections", model="checklist"
    )
    permission, _ = Permission.objects.using(alias).get_or_create(
        content_type=content_type,
        codename="deploy_checklist",
        defaults={"name": "Can deploy checklists to KoBo"},
    )
    for group_name in ("Mandi administrators", "Mandi integration operators"):
        group = Group.objects.using(alias).filter(name=group_name).first()
        if group:
            group.permissions.add(permission)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_grant_checklist_permissions"),
        ("inspections", "0006_checklist_kobo_deployment_fields"),
    ]

    operations = [
        migrations.RunPython(grant_deploy_permission, migrations.RunPython.noop)
    ]
