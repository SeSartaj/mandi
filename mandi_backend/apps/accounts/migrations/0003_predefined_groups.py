from django.db import migrations

# Explicit permissions: adding a model later never silently expands a role.
READ = [
    ("accounts", "user", "view_user"),
    ("establishments", "establishment", "view_establishment"),
    ("establishments", "sourcelink", "view_sourcelink"),
    ("inspections", "checklist", "view_checklist"),
]
REGISTRY = [
    ("establishments", "establishment", "add_establishment"),
    ("establishments", "establishment", "change_establishment"),
    ("establishments", "sourcelink", "change_sourcelink"),
]
REVIEW = []
INGEST = []
DEPLOY = [("inspections", "checklist", "deploy_checklist")]
ADMIN = [
    ("accounts", "user", "add_user"),
    ("accounts", "user", "change_user"),
    ("auth", "group", "view_group"),
    ("inspections", "checklist", "add_checklist"),
    ("inspections", "checklist", "change_checklist"),
]
ROLES = {
    "Mandi administrators": READ + REGISTRY + REVIEW + INGEST + DEPLOY + ADMIN,
    "Mandi registry officers": READ + REGISTRY,
    "Mandi inspectors": READ,
    "Mandi inspection reviewers": READ,
    "Mandi viewers": READ,
    "Mandi integration operators": READ + DEPLOY,
}


def create_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    alias = schema_editor.connection.alias
    for name, specs in ROLES.items():
        group, _ = Group.objects.using(alias).get_or_create(name=name)
        permissions = []
        for app, model, code in specs:
            content_type, _ = ContentType.objects.using(alias).get_or_create(
                app_label=app, model=model
            )
            permission, _ = Permission.objects.using(alias).get_or_create(
                content_type=content_type,
                codename=code,
                defaults={"name": code.replace("_", " ")},
            )
            permissions.append(permission.pk)
        group.permissions.set(permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_initial"),
        ("establishments", "0001_initial"),
        ("inspections", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [migrations.RunPython(create_roles, migrations.RunPython.noop)]
