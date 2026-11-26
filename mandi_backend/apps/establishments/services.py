import csv
import io
import uuid

from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError as ModelValidationError
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.services import require

from .models import Establishment, EstablishmentType, SourceLink


def list_establishments(actor, filters):
    require(actor, "establishments.view_establishment")
    qs = Establishment.objects.all()
    if filters.get("search"):
        qs = qs.filter(
            Q(name__icontains=filters["search"])
            | Q(address__icontains=filters["search"])
        )
    if filters.get("kind"):
        qs = qs.filter(kind_id=filters["kind"])
    for field in ("province", "district"):
        value = filters.get(field)
        if not value:
            continue
        key = _location_key(value)
        if key is None:
            qs = qs.filter(**{f"{field}__name__iexact": str(value)})
        else:
            qs = qs.filter(**{f"{field}_id": key})
    return qs


def _location_key(value):
    """Location filters accept a UUID, an integer ID or (as a fallback) a name."""
    for parse in (uuid.UUID, int):
        try:
            return parse(str(value))
        except (ValueError, TypeError):
            continue
    return None


def get_establishment(actor, pk):
    require(actor, "establishments.view_establishment")
    try:
        return Establishment.objects.prefetch_related("source_links").get(pk=pk)
    except Establishment.DoesNotExist as exc:
        raise NotFound("Establishment not found.") from exc


def list_establishment_types(actor):
    require(actor, "establishments.view_establishment")
    return EstablishmentType.objects.order_by("name")


@transaction.atomic
def save_establishment_type(actor, data, code=None):
    require(actor, "establishments.change_establishment")
    if code:
        try:
            obj = EstablishmentType.objects.select_for_update().get(pk=code)
        except EstablishmentType.DoesNotExist as exc:
            raise NotFound("Establishment type not found.") from exc
        for field in ("name", "is_active"):
            if field in data:
                setattr(obj, field, data[field])
    else:
        obj = EstablishmentType(
            code=data["code"],
            name=data["name"],
            is_active=data.get("is_active", True),
        )
    obj.full_clean()
    obj.save()
    return obj


def _location_value(value, province=None):
    """Accept a model instance, an ID-free name, or empty; resolve names to core models."""
    from apps.core.models import Country, District, Province

    if value in (None, ""):
        return None
    if not isinstance(value, str):
        return value
    country, _ = Country.objects.get_or_create(
        code="AF", defaults={"name": "Afghanistan"}
    )
    # Registries send the local name while the catalog stores the English one,
    # so match either column before creating a row.
    names = Q(name__iexact=value) | Q(name_local__iexact=value)
    if province is None:
        existing = Province.objects.filter(names, country=country).order_by("-code").first()
        if existing:
            return existing
        return Province.objects.create(country=country, name=value, code="")
    existing = District.objects.filter(names, province=province).order_by("-code").first()
    if existing:
        return existing
    return District.objects.create(province=province, name=value, code="")


def _type_value(value):
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        return value
    return EstablishmentType.objects.filter(pk=value).first()


def _type_id(value):
    return getattr(value, "pk", value)


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
        and _type_id(data.get("kind", obj.kind)) != obj.kind_id
        and (obj.collection_submissions.exists() or obj.source_links.exists())
    ):
        raise ValidationError(
            {
                "kind": "An establishment with submissions or source links cannot change category."
            }
        )
    values = dict(data)
    values["kind"] = _type_value(values.get("kind", getattr(obj, "kind", None)))
    values["province"] = _location_value(
        values.get("province", getattr(obj, "province", None))
    )
    values["district"] = _location_value(
        values.get("district", getattr(obj, "district", None)), values["province"]
    )
    field_names = {field.name for field in Establishment._meta.fields}
    for key, value in values.items():
        if key in field_names:
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
                    "details": {"name": record["name"]},
                    "last_synced_at": timezone.now(),
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
    require(actor, "establishments.change_sourcelink")
    obj = Establishment.objects.select_for_update().get(pk=get_establishment(actor, pk).pk)
    link = SourceLink.objects.filter(establishment=obj, source=source).first()
    if link:
        if link.is_primary:
            raise ValidationError("Transfer ownership to Mandi before disconnecting the primary source.")
        link.delete()


def establishment_choice_csv(limit=None, kind=None):
    """CSV consumed by an XLSForm select_one_from_file establishments.csv.

    Includes the Licensing or Survey fields the collector needs after selecting
    an establishment. Only the stored business/contact projection is exported.
    """
    qs = Establishment.objects.order_by("-updated_at")
    if kind:
        qs = qs.filter(kind_id=_type_id(kind))
    if limit:
        qs = qs[:limit]
    rows = list(qs)
    from .models import EstablishmentType, SourceLink

    labels = dict(EstablishmentType.objects.values_list("code", "name"))
    establishment_ids = [row.pk for row in rows]
    licensing = dict(
        SourceLink.objects.filter(
            source="licensing", establishment_id__in=establishment_ids
        ).values_list("establishment_id", "details")
    )
    # Survey-only establishments still contribute owner/contact details when
    # Licensing has no mapping for them.
    survey = dict(
        SourceLink.objects.filter(
            source="survey", establishment_id__in=establishment_ids
        ).values_list("establishment_id", "details")
    )
    columns = [
        "name",
        "label",
        "kind",
        "province",
        "district",
        "address",
        "license_number",
        "license_issue_date",
        "license_expiry_date",
        "grade",
        "owner",
        "owner_phone",
        "owner_email",
        "technical_manager",
        "technical_manager_phone",
        "technical_staff_count",
        "activities",
    ]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(columns)
    for establishment in rows:
        details = licensing.get(establishment.pk) or survey.get(establishment.pk) or {}
        source = [details.get(column, "") for column in columns[5:]]
        writer.writerow(
            [
                str(establishment.pk),
                f"{establishment.name} — {establishment.province.name if establishment.province else ''} — {labels.get(establishment.kind_id, establishment.kind_id)}",
                establishment.kind_id,
                establishment.province.name if establishment.province else "",
                establishment.district.name if establishment.district else "",
                *source,
            ]
        )
    return buffer.getvalue().encode("utf-8")


def identity_snapshot(establishment):
    """Identity known at ingestion, not a claim about an offline visit's time."""
    return {
        "id": str(establishment.pk),
        "kind": establishment.kind_id,
        "name": establishment.name,
        "province": establishment.province.name if establishment.province else "",
        "district": establishment.district.name if establishment.district else "",
        "address": establishment.address,
        "latitude": establishment.latitude,
        "longitude": establishment.longitude,
        "captured_at": timezone.now().isoformat(),
        "sources": list(establishment.source_links.values("source", "external_id", "is_primary")),
    }


def _source_map_details(establishment, record):
    details = {"name": establishment.name}
    source_details = record.get("details", {})
    for key in (
        "province",
        "district",
        "address",
        "village",
        "house_number",
        "floor",
        "market",
        "landmark",
        "neighborhood",
        "license_number",
        "license_issue_date",
        "license_expiry_date",
        "grade",
        "pharmacy_type",
        "owner",
        "owner_phone",
        "owner_email",
        "technical_manager",
        "technical_manager_phone",
        "technical_staff_count",
        "activities",
        "status",
        "tin_number",
        "opening_letter_number",
        "opening_letter_date",
        "years_of_activity",
        "current_entity_area",
        "required_entity_area",
        "wholesale_count_nearby",
        "pharmacy_count_nearby",
        "distance_to_nearest_pharmacy",
        "distance_to_nearest_health_center",
        "type_of_health_center",
        "is_official",
        "application_step",
        "has_lawyer",
        "has_pharmacist",
        "confirmed_by_team_leader",
        "confirmed_by_project_coordinator",
        "confirmed_by_audit",
        "rejection_reason",
        "is_resent",
    ):
        value = source_details.get(key)
        if value is not None and value != "":
            details[key] = value
    location = source_details.get("location")
    if location:
        details["location"] = location
    mappings = record.get("external_mappings") or {}
    for related in ("survey", "archive"):
        if mappings.get(related):
            details[f"{related}_id"] = str(mappings[related])
    return details


def _identity(record):
    details = record.get("details", {})
    location = details.get("location") or {}
    result = {
        "name": str(record.get("name") or details.get("name") or ""),
        "province": str(details.get("province") or ""),
        "district": str(details.get("district") or ""),
        "address": str(details.get("address") or ""),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
    }
    if not result["name"]:
        raise ValidationError("The registry must provide a name before import.")
    return result


def _resolve_identity(identity):
    """Map registry province/district names onto the core models."""
    resolved = dict(identity)
    province = _location_value(identity.get("province"))
    resolved["province"] = province
    resolved["district"] = (
        _location_value(identity.get("district"), province) if province else None
    )
    return resolved


def _identity_matches(obj, identity):
    return (
        obj.name == identity["name"]
        and obj.address == identity["address"]
        and obj.latitude == identity["latitude"]
        and obj.longitude == identity["longitude"]
        and (obj.province.name if obj.province else "") == identity["province"]
        and (obj.district.name if obj.district else "") == identity["district"]
    )


def _apply_identity(obj, identity):
    for key, value in _resolve_identity(identity).items():
        setattr(obj, key, value)


@transaction.atomic
def import_establishment(actor, source, external_id, kind):
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
        if existing.establishment.kind_id != kind:
            raise ValidationError("This external record already belongs to a different establishment type.")
        return existing.establishment
    record = source_record(actor, source, external_id, kind)
    obj = save_establishment(actor, dict(_resolve_identity(_identity(record)), kind=kind))
    try:
        with transaction.atomic():
            SourceLink.objects.create(establishment=obj, source=source, external_id=external_id,
                details=_source_map_details(obj, record), is_primary=True,
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
    record = source_record(actor, link.source, link.external_id, obj.kind_id)
    _apply_identity(obj, _identity(record))
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
    """Apply a trusted adapter projection; never reclaim locally owned mappings."""
    require(actor, "establishments.add_establishment")
    require(actor, "establishments.change_establishment")
    require(actor, "establishments.change_sourcelink")
    external_id = str(record["id"])
    link = SourceLink.objects.filter(source=source, external_id=external_id).first()
    if link:
        obj = Establishment.objects.select_for_update().get(pk=link.establishment_id)
        link.refresh_from_db()
        if obj.kind_id != kind:
            # Survey IDs are global: a `survey_id` already connected to another
            # establishment is the same record. Do not create a duplicate.
            return "skipped"
        if not link.is_primary:
            return "skipped"
        sync_related_mappings(actor, obj, source, record)
        identity = _identity(record)
        if _identity_matches(obj, identity):
            link.details = _source_map_details(obj, record)
            link.last_synced_at = timezone.now()
            link.save(update_fields=["details", "last_synced_at"])
            return "unchanged"
        _apply_identity(obj, identity)
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
    obj = save_establishment(actor, dict(_resolve_identity(_identity(record)), kind=kind))
    try:
        with transaction.atomic():
            SourceLink.objects.create(establishment=obj, source=source, external_id=external_id,
                details=_source_map_details(obj, record), is_primary=True,
                linked_by=actor, last_synced_at=timezone.now())
    except IntegrityError as exc:
        raise ValidationError("A concurrent import claimed this record; it will be retried.") from exc
    sync_related_mappings(actor, obj, source, record)
    return "created"


@transaction.atomic
def sync_related_mappings(actor, establishment, source, record):
    if source != "licensing":
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
                    defaults={"external_id": str(external_id), "details": {},
                        "derived_from": source, "linked_by": actor, "last_synced_at": timezone.now()})
        except IntegrityError as exc:
            raise ValidationError("This archive or survey ID is already mapped to another establishment.") from exc
