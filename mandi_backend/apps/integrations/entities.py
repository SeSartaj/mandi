"""ODK Central Entity List client and establishment projection.

One project-scoped ``establishments`` Entity List is shared by every form in
that project. Central requires Entity UUIDs to be globally unique, so each
establishment gets a deterministic, project-scoped UUID that is stored in
``EntityBinding`` and used to resolve submitted inspections back to Mandi.
"""

import csv
import io
import uuid as uuid_module
from urllib.parse import quote

from django.conf import settings

from apps.establishments.models import Establishment

from .odk import request
from .providers import CollectionError

ENTITY_PROPERTIES = (
    "kind",
    "province",
    "district",
    "address",
    "latitude",
    "longitude",
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
    "active",
)


def _status(exc):
    response = getattr(exc.__cause__, "response", None)
    return response.status_code if response is not None else None


def _dataset_path(project_id, name=None):
    base = f"projects/{int(project_id)}/datasets"
    return f"{base}/{quote(str(name), safe='')}" if name else base


def ensure_dataset(project_id=None, name=None):
    """Create the Entity List and add any missing properties.

    Datasets and properties are additive in Central. This function is
    idempotent and safe to call before each deployment or sync.
    """
    project_id = project_id or settings.ODK_PROJECT_ID
    name = name or settings.ODK_ENTITY_LIST
    try:
        meta = request("GET", _dataset_path(project_id, name)).json()
    except CollectionError as exc:
        if _status(exc) != 404:
            raise
        meta = request(
            "POST", _dataset_path(project_id), json={"name": name}
        ).json()
    existing = {
        str(property.get("name") or "") for property in (meta.get("properties") or [])
    }
    for property_name in ENTITY_PROPERTIES:
        if property_name in existing:
            continue
        request(
            "POST",
            f"{_dataset_path(project_id, name)}/properties",
            json={"name": property_name},
        )
    return name


def _source_details(establishment):
    """Licensing stays authoritative when it is linked; Survey supplies the rest."""
    for source in ("licensing", "survey"):
        link = next(
            (item for item in establishment.source_links.all() if item.source == source),
            None,
        )
        if link and isinstance(link.details, dict) and link.details:
            return link.details
    return {}


def _value(source, key, fallback=""):
    value = source.get(key) if isinstance(source, dict) else None
    if value is None or value == "":
        return str(fallback or "")
    return str(value)


def establishment_entity(establishment, entity_uuid, licensing=None):
    """Return the Entity identity and string-only property payload."""
    licensing = (
        licensing if licensing is not None else _source_details(establishment)
    )
    province = establishment.province.name if establishment.province else ""
    district = establishment.district.name if establishment.district else ""
    data = {
        "kind": establishment.kind_id or "",
        "province": _value(licensing, "province", province),
        "district": _value(licensing, "district", district),
        "address": _value(licensing, "address", establishment.address),
        "latitude": (
            "" if establishment.latitude is None else str(establishment.latitude)
        ),
        "longitude": (
            "" if establishment.longitude is None else str(establishment.longitude)
        ),
        "license_number": _value(licensing, "license_number"),
        "license_issue_date": _value(licensing, "license_issue_date"),
        "license_expiry_date": _value(licensing, "license_expiry_date"),
        "grade": _value(licensing, "grade"),
        "pharmacy_type": _value(licensing, "pharmacy_type"),
        "owner": _value(licensing, "owner"),
        "owner_phone": _value(licensing, "owner_phone"),
        "owner_email": _value(licensing, "owner_email"),
        "technical_manager": _value(licensing, "technical_manager"),
        "technical_manager_phone": _value(licensing, "technical_manager_phone"),
        "technical_staff_count": _value(licensing, "technical_staff_count"),
        "activities": _value(licensing, "activities"),
        "status": _value(licensing, "status"),
        "active": "true",
    }
    label = f"{establishment.name} — {data['province']} — {data['kind']}".strip(" —")
    return {
        "uuid": str(entity_uuid),
        "label": label[:250],
        "data": data,
    }


def entity_binding(establishment, project_id):
    """Return the project-scoped Entity UUID for an establishment.

    Central requires Entity UUIDs to be globally unique. Deriving the UUID from
    the project and establishment makes it deterministic, while the binding
    provides a direct reverse lookup for submitted inspections.
    """
    from .models import EntityBinding

    raw_uuid = uuid_module.uuid5(
        uuid_module.NAMESPACE_URL,
        f"mandi-entity:{project_id}:{establishment.pk}",
    )
    # Central accepts only version 4 UUIDs. Keep the deterministic value but
    # stamp the version nibble so the identity stays stable across syncs.
    entity_uuid = uuid_module.UUID(str(raw_uuid), version=4)
    binding, _ = EntityBinding.objects.get_or_create(
        establishment=establishment,
        project_id=str(project_id),
        defaults={"entity_uuid": entity_uuid},
    )
    return binding


def establishment_for_entity(project_id, entity_uuid):
    """Resolve an Entity UUID submitted by a form to its establishment."""
    from .models import EntityBinding

    value = str(entity_uuid or "").strip()
    if value.lower().startswith("uuid:"):
        value = value[5:]
    try:
        value = uuid_module.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return None
    binding = (
        EntityBinding.objects.filter(
            project_id=str(project_id), entity_uuid=value
        )
        .select_related("establishment")
        .first()
    )
    return binding.establishment if binding else None


def download_entities(project_id=None, name=None):
    """Return the current published Entity rows keyed by Entity UUID."""
    project_id = project_id or settings.ODK_PROJECT_ID
    name = name or settings.ODK_ENTITY_LIST
    response = request("GET", f"{_dataset_path(project_id, name)}/entities.csv")
    reader = csv.DictReader(io.StringIO(response.content.decode("utf-8")))
    rows = {}
    for row in reader:
        identity = row.get("__id") or row.get("uuid") or row.get("name")
        if identity:
            rows[str(identity)] = row
    return rows


def create_entities(payloads, project_id=None, name=None):
    project_id = project_id or settings.ODK_PROJECT_ID
    name = name or settings.ODK_ENTITY_LIST
    batch_size = max(1, settings.ODK_ENTITY_BATCH_SIZE)
    created = 0
    for offset in range(0, len(payloads), batch_size):
        chunk = payloads[offset : offset + batch_size]
        request(
            "POST",
            f"{_dataset_path(project_id, name)}/entities",
            json={
                "entities": chunk,
                "source": {"name": "mandi-sync", "size": len(chunk)},
            },
        )
        created += len(chunk)
    return created


def update_entity(uuid, payload, project_id=None, name=None):
    project_id = project_id or settings.ODK_PROJECT_ID
    name = name or settings.ODK_ENTITY_LIST
    request(
        "PATCH",
        f"{_dataset_path(project_id, name)}/entities/{quote(str(uuid), safe='')}",
        params={"force": "true"},
        json={"label": payload["label"], "data": payload["data"]},
    )


def sync_entities(project_id=None, name=None):
    """Reconcile Mandi establishments into the Central Entity List.

    Existing entities are updated with ``force=true``; entities that exist only
    in Central are left untouched so form-created data is never destroyed.
    """
    project_id = project_id or settings.ODK_PROJECT_ID
    name = ensure_dataset(project_id, name)
    current = download_entities(project_id, name)
    establishments = (
        Establishment.objects.select_related("kind", "province", "district")
        .prefetch_related("source_links")
        .order_by("pk")
    )
    counts = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "central_only": 0,
        "failed": 0,
    }
    to_create = []
    seen = set()
    for establishment in establishments.iterator(chunk_size=200):
        binding = entity_binding(establishment, project_id)
        payload = establishment_entity(establishment, binding.entity_uuid)
        uuid = payload["uuid"]
        seen.add(uuid)
        row = current.get(uuid)
        if row is None:
            to_create.append(payload)
            continue
        current_data = {
            property_name: str(row.get(property_name) or "")
            for property_name in ENTITY_PROPERTIES
        }
        if (
            str(row.get("label") or "") == payload["label"]
            and current_data == payload["data"]
        ):
            counts["unchanged"] += 1
            continue
        try:
            update_entity(uuid, payload, project_id, name)
            counts["updated"] += 1
        except CollectionError:
            counts["failed"] += 1
    try:
        counts["created"] = create_entities(to_create, project_id, name)
    except CollectionError:
        counts["failed"] += len(to_create)
        counts["created"] = 0
    counts["central_only"] = len(set(current) - seen)
    return counts
