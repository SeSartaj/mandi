from django.db import migrations


def merge(apps, schema_editor):
    """Fold the legacy `registration` source into `licensing`.

    Both codes pointed at the same Licensing application API. Existing links and
    sync cursors are preserved; duplicates are collapsed to the licensing row.
    """
    SourceLink = apps.get_model("establishments", "SourceLink")
    Cursor = apps.get_model("establishments", "RegistrySyncCursor")
    System = apps.get_model("establishments", "ExternalSystem")
    db = schema_editor.connection.alias

    SourceLink.objects.using(db).filter(derived_from="registration").update(
        derived_from="licensing"
    )

    links = (
        SourceLink.objects.using(db)
        .filter(source="registration")
        .order_by("establishment_id", "-is_primary", "pk")
    )
    for link in links:
        existing = SourceLink.objects.using(db).filter(
            establishment_id=link.establishment_id, source="licensing"
        ).first()
        if existing:
            # One link per establishment; keep primary ownership if it lived on
            # the legacy row.
            if link.is_primary and not existing.is_primary:
                existing.is_primary = True
                existing.save(using=db, update_fields=["is_primary"])
            link.delete(using=db)
            continue
        clash = (
            SourceLink.objects.using(db)
            .filter(source="licensing", external_id=link.external_id)
            .first()
        )
        if clash:
            # The same upstream identity is already linked to another
            # establishment; cannot keep both under the unique constraint.
            link.delete(using=db)
            continue
        link.source = "licensing"
        link.save(using=db, update_fields=["source"])

    for cursor in Cursor.objects.using(db).filter(source_id="registration"):
        existing = Cursor.objects.using(db).filter(
            source_id="licensing", kind_id=cursor.kind_id
        ).first()
        if existing:
            cursor.delete(using=db)
        else:
            cursor.source_id = "licensing"
            cursor.save(using=db, update_fields=["source"])

    System.objects.using(db).filter(pk="registration").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("establishments", "0005_remove_establishment_entity_hash_and_more"),
    ]

    operations = [migrations.RunPython(merge, migrations.RunPython.noop)]
