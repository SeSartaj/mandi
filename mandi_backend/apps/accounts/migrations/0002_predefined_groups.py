from django.db import migrations

# Explicit permissions: adding a model later never silently expands a role.
READ = [
    ("accounts", "user", "view_user"),
    ("establishments", "establishment", "view_establishment"),
    ("establishments", "sourcelink", "view_sourcelink"),
    ("inspections", "checklist", "view_checklist"),
    ("inspections", "inspection", "view_inspection"),
]
REGISTRY = [
    ("establishments", "establishment", "add_establishment"),
    ("establishments", "establishment", "change_establishment"),
    ("establishments", "sourcelink", "change_sourcelink"),
]
REVIEW = [
    ("inspections", "inspection", "approve_inspection"),
]
INGEST = [("inspections", "inspection", "add_inspection")]
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
    "Mandi inspection reviewers": READ + REVIEW,
    "Mandi viewers": READ,
    "Mandi integration operators": READ + INGEST + DEPLOY,
}


def create_roles(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    alias = schema_editor.connection.alias
    # Permissions normally appear after migrations. Create only these explicit
    # permissions now, using historical models, so fresh installs work as well.
    for old, new in [
        ("Review managers", "Mandi administrators"),
        ("Review readers", "Mandi viewers"),
    ]:
        legacy = Group.objects.using(alias).filter(name=old).first()
        if legacy and not Group.objects.using(alias).filter(name=new).exists():
            legacy.name = new
            legacy.save(using=alias, update_fields=["name"])
    for name, specs in ROLES.items():
        group, _ = Group.objects.using(alias).get_or_create(name=name)
        permissions = []
        for app, model, code in specs:
            ct, _ = ContentType.objects.using(alias).get_or_create(
                app_label=app, model=model
            )
            perm, _ = Permission.objects.using(alias).get_or_create(
                content_type=ct,
                codename=code,
                defaults={"name": code.replace("_", " ")},
            )
            permissions.append(perm.pk)
        group.permissions.set(permissions)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("establishments", "0002_establishment_establishme_kind_454ef1_idx"),
        ("inspections", "0002_inspection_inspections_inspect_f3c5cb_idx_and_more"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]
    operations = [migrations.RunPython(create_roles, migrations.RunPython.noop)]
