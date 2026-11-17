import csv
import io

from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError as ModelValidationError
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.services import require

from .models import Establishment, SourceLink
from apps.integrations.registry import canonical_source


def list_establishments(actor, filters):
    require(actor, "establishments.view_establishment")
    qs = Establishment.objects.all()
    if filters.get("search"):
        qs = qs.filter(
            Q(name__icontains=filters["search"])
            | Q(address__icontains=filters["search"])
        )
    for field in ("kind", "province", "district"):
        if filters.get(field):
            qs = qs.filter(**{field: filters[field]})
    return qs


def get_establishment(actor, pk):
    require(actor, "establishments.view_establishment")
    try:
        return Establishment.objects.prefetch_related("source_links").get(pk=pk)
    except Establishment.DoesNotExist as exc:
        raise NotFound("Establishment not found.") from exc


@transaction.atomic
def save_establishment(actor, data, pk=None):
    require(
        actor,
        "establishments.change_establishment"
        if pk
        else "establishments.add_establishment",
    )
    obj = get_establishment(actor, pk) if pk else Establishment()
    if pk:
        obj = Establishment.objects.select_for_update().get(pk=pk)
        if obj.primary_source and any(getattr(obj, key) != value for key, value in data.items()):
            raise ValidationError("Identity is managed by the primary registry. Refresh it from that source.")
    if (
        pk
        and data.get("kind", obj.kind) != obj.kind
        and (obj.inspections.exists() or obj.source_links.exists())
    ):
        raise ValidationError(
            {
                "kind": "An establishment with inspections or source links cannot change category."
            }
        )
    for key, value in data.items():
        setattr(obj, key, value)
    if not pk:
        obj.created_by = actor
    obj.updated_by = actor
    try:
        obj.full_clean()
    except ModelValidationError as exc:
        raise ValidationError(exc.message_dict) from exc
    obj.save()
    return obj


@transaction.atomic
def connect_source(actor, pk, source, external_id):
    source = canonical_source(source)
    require(actor, "establishments.change_sourcelink")
    obj = Establishment.objects.select_for_update().get(pk=get_establishment(actor, pk).pk)
    from apps.integrations.services import source_record

    record = source_record(actor, source, external_id, obj.kind)
    existing = obj.source_links.filter(source=source).first()
    if existing and existing.is_primary:
        raise ValidationError("Transfer ownership before replacing a primary mapping.")
    try:
        with transaction.atomic():
            link, _ = SourceLink.objects.update_or_create(
                establishment=obj,
                source=source,
                defaults={
                    "external_id": external_id,
                    "details": record["details"] if record["is_demo"] else {"name": record["name"]},
                    "last_synced_at": timezone.now(),
                    "is_demo": record["is_demo"],
                    "linked_by": actor,
                },
            )
    except IntegrityError as exc:
        raise ValidationError(
            "This external record is already linked to another establishment."
        ) from exc
    sync_related_mappings(actor, obj, source, record)
    return link


@transaction.atomic
def disconnect_source(actor, pk, source):
    source = canonical_source(source)
    require(actor, "establishments.change_sourcelink")
    obj = Establishment.objects.select_for_update().get(pk=get_establishment(actor, pk).pk)
    link = SourceLink.objects.filter(establishment=obj, source=source).first()
    if link:
        if link.is_primary:
            raise ValidationError("Transfer ownership to Mandi before disconnecting the primary source.")
        link.delete()


def establishment_choice_csv(limit=None, kind=None):
    """CSV consumed by an XLSForm select_one_from_file establishments.csv."""
    qs = Establishment.objects.order_by("-updated_at")
    if kind:
        qs = qs.filter(kind=kind)
    if limit:
        qs = qs[:limit]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["name", "label", "kind", "province", "district"])
    from .models import EstablishmentType
    labels = dict(EstablishmentType.objects.values_list("code", "name"))
    for establishment in qs.iterator():
        writer.writerow(
            [
                str(establishment.pk),
                f"{establishment.name} — {establishment.province} — {labels.get(establishment.kind, establishment.kind)}",
                establishment.kind,
                establishment.province,
                establishment.district,
            ]
        )
    return buffer.getvalue().encode("utf-8")


IDENTITY_FIELDS = ("name", "province", "district", "address", "phone", "subtype", "license_number", "status")


def identity_snapshot(establishment):
    """Identity known at ingestion, not a claim about an offline visit's time."""
    return {
        "id": str(establishment.pk), "kind": establishment.kind,
        **{key: getattr(establishment, key) for key in IDENTITY_FIELDS},
        "attributes": establishment.attributes,
        "captured_at": timezone.now().isoformat(),
        "sources": list(establishment.source_links.values("source", "external_id", "is_primary")),
    }



def _source_map_details(establishment, record):
    details = {"name": establishment.name}
    location = record.get("details", {}).get("location")
    if location:
        details["location"] = location
    return details


def _identity(record):
    details = record.get("details", {})
    result = {key: str(details.get(key) or "") for key in IDENTITY_FIELDS}
    location = details.get("location") or {}
    result["latitude"] = location.get("latitude")
    result["longitude"] = location.get("longitude")
    result["name"] = str(record.get("name") or result.get("name", ""))
    if not result["name"]:
        raise ValidationError("The registry must provide a name before import.")
    return result


@transaction.atomic
def import_establishment(actor, source, external_id, kind):
    source = canonical_source(source)
    require(actor, "establishments.add_establishment")
    require(actor, "establishments.view_establishment")
    require(actor, "establishments.view_sourcelink")
    require(actor, "establishments.change_sourcelink")
    from apps.integrations.services import source_record
    from .models import EstablishmentType
    if not EstablishmentType.objects.filter(pk=kind, is_active=True).exists():
        raise ValidationError({"kind": "Select an active establishment type."})
    existing = SourceLink.objects.select_related("establishment").filter(source=source, external_id=external_id).first()
    if existing:
        if existing.establishment.kind != kind:
            raise ValidationError("This external record already belongs to a different establishment type.")
        return existing.establishment
    record = source_record(actor, source, external_id, kind)
    obj = save_establishment(actor, dict(_identity(record), kind=kind))
    try:
        with transaction.atomic():
            SourceLink.objects.create(establishment=obj, source=source, external_id=external_id,
                details=_source_map_details(obj, record), is_demo=record["is_demo"], is_primary=True,
                linked_by=actor, last_synced_at=timezone.now())
    except IntegrityError as exc:
        raise ValidationError("This external record was imported concurrently; retry the import.") from exc
    sync_related_mappings(actor, obj, source, record)
    return obj


@transaction.atomic
def refresh_identity(actor, pk):
    require(actor, "establishments.change_establishment")
    require(actor, "establishments.view_sourcelink")
    from apps.integrations.services import source_record
    obj = Establishment.objects.select_for_update().get(pk=get_establishment(actor, pk).pk)
    link = obj.source_links.filter(is_primary=True).first()
    if not link:
        raise ValidationError("This establishment is managed by Mandi.")
    record = source_record(actor, link.source, link.external_id, obj.kind)
    for key, value in _identity(record).items():
        setattr(obj, key, value)
    obj.updated_by = actor
    try:
        obj.full_clean()
    except ModelValidationError as exc:
        raise ValidationError(exc.message_dict) from exc
    obj.save()
    link.details = _source_map_details(obj, record)
    link.last_synced_at = timezone.now()
    link.save(update_fields=["details", "last_synced_at"])
    sync_related_mappings(actor, obj, link.source, record)
    return obj


@transaction.atomic
def transfer_ownership(actor, pk, source=None):
    require(actor, "establishments.change_establishment")
    require(actor, "establishments.change_sourcelink")
    obj = Establishment.objects.select_for_update().get(pk=get_establishment(actor, pk).pk)
    link = None
    if source:
        link = obj.source_links.filter(source=source).first()
        if not link:
            raise ValidationError("Connect this source before transferring ownership.")
    obj.source_links.filter(is_primary=True).update(is_primary=False)
    if link:
        link.is_primary = True
        link.save(update_fields=["is_primary"])
        return refresh_identity(actor, pk)
    obj.updated_by = actor
    obj.save(update_fields=["updated_by", "updated_at"])
    return obj


@transaction.atomic
def sync_registry_record(actor, source, kind, record):
    source = canonical_source(source)
    """Apply a trusted adapter projection; never reclaim locally owned mappings."""
    require(actor, "establishments.add_establishment")
    require(actor, "establishments.change_establishment")
    require(actor, "establishments.change_sourcelink")
    external_id = str(record["id"])
    link = SourceLink.objects.filter(source=source, external_id=external_id).first()
    if link:
        obj = Establishment.objects.select_for_update().get(pk=link.establishment_id)
        link.refresh_from_db()
        if obj.kind != kind:
            raise ValidationError("The external record is mapped to another establishment type.")
        if not link.is_primary:
            return "skipped"
        sync_related_mappings(actor, obj, source, record)
        identity = _identity(record)
        if all(getattr(obj, key) == value for key, value in identity.items()):
            link.details = _source_map_details(obj, record)
            link.last_synced_at = timezone.now()
            link.save(update_fields=["details", "last_synced_at"])
            return "unchanged"
        for key, value in identity.items():
            setattr(obj, key, value)
        obj.updated_by = actor
        try:
            obj.full_clean()
        except ModelValidationError as exc:
            raise ValidationError("The registry identity is incomplete or invalid.") from exc
        obj.save()
        link.details = _source_map_details(obj, record)
        link.last_synced_at = timezone.now()
        link.save(update_fields=["details", "last_synced_at"])
        return "updated"
    obj = save_establishment(actor, dict(_identity(record), kind=kind))
    try:
        with transaction.atomic():
            SourceLink.objects.create(establishment=obj, source=source, external_id=external_id,
                details=_source_map_details(obj, record), is_demo=False, is_primary=True,
                linked_by=actor, last_synced_at=timezone.now())
    except IntegrityError as exc:
        raise ValidationError("A concurrent import claimed this record; it will be retried.") from exc
    sync_related_mappings(actor, obj, source, record)
    return "created"


@transaction.atomic
def sync_related_mappings(actor, establishment, source, record):
    if source not in {"registration", "licensing"}:
        return
    for related_source, external_id in record.get("external_mappings", {}).items():
        if related_source not in {"archive", "survey"}:
            continue
        existing = establishment.source_links.filter(source=related_source).first()
        if not external_id:
            if existing and existing.derived_from == source and not existing.is_primary:
                existing.delete()
            continue
        if existing and (existing.is_primary or not existing.derived_from):
            if existing.external_id != external_id:
                raise ValidationError("A manually linked source conflicts with the Licensing reference. Review that mapping before syncing.")
            continue
        try:
            with transaction.atomic():
                SourceLink.objects.update_or_create(establishment=establishment, source=related_source,
                    defaults={"external_id": str(external_id), "details": {}, "is_demo": False,
                        "derived_from": source, "linked_by": actor, "last_synced_at": timezone.now()})
        except IntegrityError as exc:
            raise ValidationError("This archive or survey ID is already mapped to another establishment.") from exc
