from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError as ModelValidationError
from django.db.models import Q
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.services import require

from .models import Establishment, SourceLink


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
    require(actor, "establishments.change_sourcelink")
    obj = get_establishment(actor, pk)
    from apps.integrations.services import source_record

    record = source_record(actor, source, external_id, obj.kind)
    try:
        with transaction.atomic():
            link, _ = SourceLink.objects.update_or_create(
                establishment=obj,
                source=source,
                defaults={
                    "external_id": external_id,
                    "details": record["details"],
                    "is_demo": record["is_demo"],
                    "linked_by": actor,
                },
            )
    except IntegrityError as exc:
        raise ValidationError(
            "This external record is already linked to another establishment."
        ) from exc
    return link


@transaction.atomic
def disconnect_source(actor, pk, source):
    require(actor, "establishments.change_sourcelink")
    obj = get_establishment(actor, pk)
    link = SourceLink.objects.filter(establishment=obj, source=source).first()
    if link:
        link.delete()
