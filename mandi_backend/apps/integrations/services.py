from django.conf import settings
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.services import require
from apps.establishments.models import Establishment, SourceLink
from apps.inspections.models import Checklist

from .kobo import KoboError, fetch_submissions, get_asset
from .models import KoboSubmission
from .submissions import extract_scores, form_schema, submission_answers


def source_candidates(actor, source, kind, search=""):
    require(actor, "establishments.view_sourcelink")
    if source not in SourceLink.Source.values:
        raise ValidationError({"source": "Unknown source system."})
    if not settings.DEMO_INTEGRATIONS:
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
    return KoboSubmission.objects.filter(establishment=establishment).select_related(
        "checklist"
    )


def sync_kobo_submissions(actor, establishment_id=None):
    require(actor, "inspections.add_inspection")
    checklists = Checklist.objects.exclude(kobo_asset_uid="").select_related()
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
            except (Establishment.DoesNotExist, ValueError, ValidationError):
                counts["skipped"] += 1
                continue
            submission_id = (
                data.get("_id")
                or data.get("meta/instanceID")
                or data.get("_uuid")
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
                    "submitted_at": parse_datetime(
                        data.get("_submission_time") or ""
                    ),
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
