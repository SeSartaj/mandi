from django.conf import settings
from rest_framework.exceptions import NotFound, ValidationError
from apps.accounts.services import require
from apps.establishments.models import SourceLink


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
