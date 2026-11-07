from django.db import migrations


REMOVED_PERMISSIONS = [
    ("establishments", "view_auditevent"),
    ("inspections", "view_annualtarget"),
    ("inspections", "change_annualtarget"),
    ("inspections", "add_annualtarget"),
    ("inspections", "delete_annualtarget"),
]


def remove_permissions(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    alias = schema_editor.connection.alias
    for app_label, codename in REMOVED_PERMISSIONS:
        Permission.objects.using(alias).filter(
            content_type__app_label=app_label,
            codename=codename,
        ).delete()
    for app_label, model in [
        ("establishments", "auditevent"),
        ("inspections", "annualtarget"),
    ]:
        ContentType.objects.using(alias).filter(
            app_label=app_label,
            model=model,
        ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_predefined_groups"),
        ("establishments", "0003_delete_auditevent"),
        ("inspections", "0004_checklist_xlsform_delete_annualtarget"),
    ]

    operations = [migrations.RunPython(remove_permissions, migrations.RunPython.noop)]
