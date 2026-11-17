from datetime import UTC

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.services import require, scope_checklists, require_checklist_access
from apps.establishments.models import Establishment, SourceLink
from apps.inspections.models import Checklist

from .kobo import KoboError, fetch_submissions, get_asset, open_attachment
from .models import KoboSubmission
from .submissions import (
    form_schema,
    submission_attachments,
)


def _utc(value):
    """KoBo timestamps are UTC without an offset, so make them timezone-aware."""
    parsed = parse_datetime(value or "")
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, UTC)
    return parsed


def source_candidates(actor, source, kind, search="", page=1, page_size=20):
    require(actor, "establishments.view_sourcelink")
    from .registry import adapter_for
    adapter = adapter_for(source)
    if adapter:
        return adapter.search(kind, search, page, page_size)["results"]
    if not settings.DEMO_INTEGRATIONS or source not in {"survey", "archive", "licensing"}:
        raise ValidationError(
            "This source is not connected. Configure a live adapter before use."
        )
    records = [
        {
            "id": f"{source}-{kind}-001",
            "name": "Shifa Demonstration",
            "details": {
                "name": "Shifa Demonstration",
                "province": "Kabul",
                "record_number": f"DEMO-{source}-001",
                "status": "Demonstration record",
            },
        },
        {
            "id": f"{source}-{kind}-002",
            "name": "Omid Demonstration",
            "details": {
                "name": "Omid Demonstration",
                "province": "Herat",
                "record_number": f"DEMO-{source}-002",
                "status": "Demonstration record",
            },
        },
    ]
    return [
        dict(r, is_demo=True) for r in records if search.lower() in r["name"].lower()
    ]


def source_record(actor, source, external_id, kind):
    require(actor, "establishments.view_sourcelink")
    from .registry import adapter_for
    adapter = adapter_for(source)
    if adapter:
        record = adapter.identity(kind, external_id)
        if str(record.get("id")) != external_id:
            raise ValidationError("The registry returned a different external ID. The mapping was not changed.")
        return record
    for record in source_candidates(actor, source, kind):
        if record["id"] == external_id:
            return record
    raise NotFound("External record not found.")


def establishment_choices(actor, kind):
    from apps.establishments.services import list_establishments

    return [
        {"name": str(e.pk), "label": f"{e.name} · {e.province} · {str(e.pk)[:8]}"}
        for e in list_establishments(actor, {"kind": kind})
    ]


def kobo_asset_url(asset_uid):
    """Deep link to the KoBo data table for a deployed form."""
    if not asset_uid:
        return None
    host = settings.KOBO_HOST_HEADER or settings.KOBO_BASE_URL
    if "://" not in host:
        host = f"http://{host}"
    return f"{host.rstrip('/')}/#/forms/{asset_uid}/data"


def kobo_submissions(actor, establishment_id):
    require(actor, "establishments.view_establishment")
    try:
        establishment = Establishment.objects.get(pk=establishment_id)
    except Establishment.DoesNotExist as exc:
        raise NotFound("Establishment not found.") from exc
    return scope_checklists(actor, KoboSubmission.objects.filter(establishment=establishment), "checklist_id").select_related(
        "checklist"
    )


def checklist_submissions(actor, checklist_id, filters=None):
    """Submissions of one checklist, filtered for the checklist detail page."""
    require(actor, "establishments.view_establishment")
    try:
        checklist = Checklist.objects.get(pk=checklist_id)
    except Checklist.DoesNotExist as exc:
        raise NotFound("Checklist not found.") from exc

    require_checklist_access(actor, checklist_id)
    filters = filters or {}
    qs = (
        KoboSubmission.objects.filter(checklist=checklist)
        .select_related("checklist", "establishment")
        .order_by("-submitted_at", "-id")
    )
    search = (filters.get("search") or "").strip()
    if search:
        qs = qs.filter(
            Q(establishment__name__icontains=search)
            | Q(submission_id__icontains=search)
        )
    if filters.get("establishment_id"):
        qs = qs.filter(establishment_id=filters["establishment_id"])
    if filters.get("date_from"):
        qs = qs.filter(submitted_at__date__gte=filters["date_from"])
    if filters.get("date_to"):
        qs = qs.filter(submitted_at__date__lte=filters["date_to"])
    return qs


def kobo_submission(actor, pk):
    require(actor, "establishments.view_establishment")
    try:
        return scope_checklists(actor, KoboSubmission.objects.all(), "checklist_id").select_related("checklist", "establishment").get(
            pk=pk
        )
    except KoboSubmission.DoesNotExist as exc:
        raise NotFound("Submission not found.") from exc


def submission_attachment(actor, pk, index):
    """Return the KoBo attachment stream for one submission file."""
    submission = kobo_submission(actor, pk)
    attachments = submission_attachments(submission.data)
    if index < 0 or index >= len(attachments):
        raise NotFound("Attachment not found.")
    return attachments[index], open_attachment(attachments[index]["download_url"])


def sync_kobo_submissions(actor, establishment_id=None, checklist_id=None):
    require(actor, "inspections.add_inspection")
    if checklist_id:
        require_checklist_access(actor, checklist_id)
    checklists = scope_checklists(actor, Checklist.objects.exclude(kobo_asset_uid="")).select_related()
    if checklist_id:
        checklists = checklists.filter(pk=checklist_id)
    counts = {"fetched": 0, "created": 0, "updated": 0, "skipped": 0}

    for checklist in checklists:
        try:
            submissions = fetch_submissions(checklist.kobo_asset_uid)
        except KoboError as exc:
            raise ValidationError({"kobo": str(exc)}) from exc
        try:
            asset = get_asset(checklist.kobo_asset_uid)
        except KoboError:
            asset = None
        schema = form_schema(asset) if asset else {}

        for data in submissions:
            counts["fetched"] += 1
            establishment_value = data.get("establishment_id")
            if not establishment_value:
                counts["skipped"] += 1
                continue
            if establishment_id and str(establishment_value) != str(establishment_id):
                counts["skipped"] += 1
                continue
            try:
                establishment = Establishment.objects.get(pk=establishment_value)
            except (Establishment.DoesNotExist, ValueError, DjangoValidationError):
                counts["skipped"] += 1
                continue
            submission_id = (
                data.get("_id") or data.get("meta/instanceID") or data.get("_uuid")
            )
            if not submission_id:
                counts["skipped"] += 1
                continue

            submission, created = KoboSubmission.objects.update_or_create(
                asset_uid=checklist.kobo_asset_uid,
                submission_id=str(submission_id),
                defaults={
                    "establishment": establishment,
                    "checklist": checklist,
                    "submitted_at": _utc(data.get("_submission_time")),
                    "data": data,
                    "form_schema": schema,
                    "updated_by": actor,
                },
            )
            if created:
                submission.created_by = actor
                submission.save(update_fields=["created_by"])
                counts["created"] += 1
            else:
                counts["updated"] += 1

    return counts


def source_search(actor, source, kind, search="", page=1, page_size=20):
    require(actor, "establishments.view_sourcelink")
    from .registry import adapter_for
    adapter = adapter_for(source)
    if adapter:
        return adapter.search(kind, search, page, page_size)
    records = source_candidates(actor, source, kind, search)
    return {"is_demo": True, "count": len(records), "has_next": False, "results": records}


def source_detail(actor, establishment_id, source, include_sensitive=None):
    """Load current details for the record already linked to this establishment."""
    from apps.establishments.services import get_establishment
    from .registry import canonical_source
    source = canonical_source(source)
    require(actor, "establishments.view_sourcelink")
    establishment = get_establishment(actor, establishment_id)
    try:
        link = establishment.source_links.get(source=source)
    except SourceLink.DoesNotExist as exc:
        raise NotFound("This source is not linked.") from exc
    from .registry import adapter_for, detail_with_field_ids
    adapter = adapter_for(source)
    include_sensitive = include_sensitive is not False and actor.has_perm("establishments.view_sensitive_source_details")
    if adapter and not link.is_demo:
        from .registry import LicensingAdapter
        options = {"include_sensitive": include_sensitive} if isinstance(adapter, LicensingAdapter) else {}
        detail = adapter.details(establishment.kind, link.external_id, **options)
        # Store only business coordinates, never the full source profile.
        if link.is_primary:
            location = next((section["location"] for section in detail.get("sections", []) if section.get("location")), None)
            details = {key: value for key, value in link.details.items() if key != "location"}
            if location:
                details["location"] = location
            SourceLink.objects.filter(pk=link.pk).update(details=details)
            from apps.establishments.models import Establishment
            Establishment.objects.filter(pk=establishment.pk).update(
                latitude=location["latitude"] if location else None,
                longitude=location["longitude"] if location else None,
            )
        return detail_with_field_ids(detail)
    if not link.is_demo and source in {"archive", "survey"}:
        from . import licensing
        primary = establishment.source_links.filter(source__in=["registration", "licensing"]).order_by("-is_primary").first()
        if primary:
            upstream = adapter_for(primary.source)
            if upstream:
                _, raw = upstream._record(establishment.kind, primary.external_id)
                return detail_with_field_ids(licensing.related_details(raw, source, link.external_id, include_sensitive=include_sensitive))
    if not link.is_demo:
        raise ValidationError("This source is temporarily unavailable; the local establishment remains accessible.")
    if link.is_demo:
        return detail_with_field_ids({"name": link.details.get("name") or establishment.name,
                "application_id": link.external_id, "is_demo": link.is_demo,
                "sections": [{"title": "Source details", "fields": [
                    {"label": key.replace("_", " ").capitalize(), "value": value}
                    for key, value in link.details.items() if isinstance(value, (str, int, float, bool))
                ]}]})
