from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.services import require
from apps.establishments.models import Establishment, SourceLink

from . import documents


def source_candidates(actor, source, kind, search="", page=1, page_size=20):
    require(actor, "establishments.view_sourcelink")
    from .registry import adapter_for
    adapter = adapter_for(source)
    if adapter:
        return adapter.search(kind, search, page, page_size)["results"]
    raise ValidationError(
        "This source is not connected. Configure a live adapter before use."
    )


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


def establishment_choices(actor, kind=None, checklist_id=None):
    from apps.accounts.services import require_checklist_access
    from apps.establishments.services import list_establishments

    qs = list_establishments(actor, {"kind": kind} if kind else {})
    if checklist_id:
        require_checklist_access(actor, checklist_id)
        qs = qs.filter(
            collection_submissions__deployment__checklist_id=checklist_id
        ).distinct()
    return [
        {
            "name": str(e.pk),
            "label": f"{e.name} · {e.province.name if e.province else ''} · {str(e.pk)[:8]}",
        }
        for e in qs
    ]


def source_search(actor, source, kind, search="", page=1, page_size=20, filters=None):
    require(actor, "establishments.view_sourcelink")
    from .registry import adapter_for
    adapter = adapter_for(source)
    if not adapter:
        raise ValidationError(
            "This source is not connected. Configure a live adapter before use."
        )
    if filters:
        return adapter.search(kind, search, page, page_size, filters=filters)
    return adapter.search(kind, search, page, page_size)


def _survey_via_licensing(establishment, link, include_sensitive):
    """Older Survey IDs may only exist inside a linked Licensing record."""
    primary = establishment.source_links.filter(source="licensing").first()
    if not primary:
        return None
    from .registry import adapter_for, detail_with_field_ids
    upstream = adapter_for(primary.source)
    if not upstream or not hasattr(upstream, "_record"):
        return None
    from . import licensing
    _, raw = upstream._record(establishment.kind_id, primary.external_id)
    return detail_with_field_ids(
        licensing.related_details(
            raw, "survey", link.external_id, include_sensitive=include_sensitive
        )
    )


def source_detail(actor, establishment_id, source, include_sensitive=None):
    """Load current details for the record already linked to this establishment."""
    from apps.establishments.services import get_establishment
    require(actor, "establishments.view_sourcelink")
    establishment = get_establishment(actor, establishment_id)
    try:
        link = establishment.source_links.get(source=source)
    except SourceLink.DoesNotExist as exc:
        raise NotFound("This source is not linked.") from exc
    from .registry import adapter_for, detail_with_field_ids
    adapter = adapter_for(source)
    include_sensitive = include_sensitive is not False and actor.has_perm("establishments.view_sensitive_source_details")
    if adapter:
        from .registry import LicensingAdapter, SurveyAdapter
        options = (
            {"include_sensitive": include_sensitive}
            if isinstance(adapter, (LicensingAdapter, SurveyAdapter))
            else {}
        )
        try:
            detail = adapter.details(establishment.kind_id, link.external_id, **options)
        except NotFound:
            fallback = (
                _survey_via_licensing(establishment, link, include_sensitive)
                if source == "survey"
                else None
            )
            if fallback:
                return documents.rewrite(fallback, source)
            raise
        if source == "survey" and not detail.get("sections"):
            fallback = _survey_via_licensing(
                establishment, link, include_sensitive
            )
            if fallback:
                return documents.rewrite(fallback, source)
        # Store only business coordinates, never the full source profile.
        if link.is_primary:
            sections = detail.get("sections", [])
            location = next((section["location"] for section in sections if section.get("location")), None)
            details = {key: value for key, value in link.details.items() if key != "location"}

            def plain(value):
                if isinstance(value, dict):
                    return value.get("name_fa") or value.get("name_en") or value.get("name_ps") or ""
                return str(value or "")

            location_section = next(
                (section for section in sections if section.get("title") == "Location"), None
            )
            fields = {
                str(field.get("label")): field.get("value")
                for field in (location_section or {}).get("fields", [])
            }
            for key, label in (
                ("province", "Province"),
                ("district", "District"),
                ("address", "Address"),
                ("village", "Village"),
                ("house_number", "House number"),
                ("floor", "Floor"),
                ("market", "Market"),
                ("landmark", "Landmark"),
                ("neighborhood", "Neighborhood"),
            ):
                value = fields.get(label)
                if value not in (None, "", {}, []):
                    details[key] = plain(value)
            establishment_section = next(
                (section for section in sections if section.get("title") == "Establishment"),
                None,
            )
            pharmacy_type = next(
                (
                    field.get("value")
                    for field in (establishment_section or {}).get("fields", [])
                    if field.get("label") == "Pharmacy type"
                ),
                None,
            )
            if pharmacy_type not in (None, "", {}, []):
                details["pharmacy_type"] = plain(pharmacy_type)
            if location:
                details["location"] = location
            SourceLink.objects.filter(pk=link.pk).update(details=details)
            from apps.establishments.models import Establishment
            Establishment.objects.filter(pk=establishment.pk).update(
                latitude=location["latitude"] if location else None,
                longitude=location["longitude"] if location else None,
            )
        return documents.rewrite(detail_with_field_ids(detail), source)
    if source in {"archive", "survey"}:
        from . import licensing
        primary = establishment.source_links.filter(source="licensing").order_by("-is_primary").first()
        if primary:
            upstream = adapter_for(primary.source)
            if upstream:
                _, raw = upstream._record(establishment.kind_id, primary.external_id)
                return documents.rewrite(
                    detail_with_field_ids(
                        licensing.related_details(
                            raw, source, link.external_id, include_sensitive=include_sensitive
                        )
                    ),
                    source,
                )
    raise ValidationError("This source is temporarily unavailable; the local establishment remains accessible.")
