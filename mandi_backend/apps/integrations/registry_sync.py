"""Bounded, restartable registry ingestion independent of collection providers."""
from django.db import connection
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound
from apps.accounts.services import require
from apps.establishments.models import ExternalSystem, EstablishmentType, RegistrySyncCursor
from apps.establishments.services import sync_registry_record
from . import licensing
from .registry import RegistryAdapter, adapter_for


def _categories(adapter):
    """Mandi kinds a source supports; registry adapters declare their own."""
    kinds = getattr(adapter, "kinds", None)
    return kinds if isinstance(kinds, dict) and kinds else licensing.KIND_CATEGORIES


def _project(adapter, category, raw):
    """Project a raw list item with the source's own identity rules."""
    if isinstance(adapter, RegistryAdapter):
        return adapter.project(category, raw)
    return licensing.candidate(category, raw)


def sync_batch(actor, source="licensing", page_size=50, selected_kinds=None):
    for permission in ("view_establishment", "view_sourcelink", "add_establishment", "change_establishment", "change_sourcelink"):
        require(actor, f"establishments.{permission}")
    page_size = min(100, max(1, int(page_size)))
    # Session advisory lock prevents simultaneous workers/manual runs on PostgreSQL.
    locked = False
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", [628194201])
            locked = cursor.fetchone()[0]
        if not locked:
            return {"busy": True}
    try:
        adapter = adapter_for(source)
        if not adapter or not hasattr(adapter, "list_page"):
            raise ValueError("This external system does not support automatic sync.")
        system = ExternalSystem.objects.get(pk=source, is_active=True)
        total = {key: 0 for key in ("created", "updated", "unchanged", "skipped", "failed", "pages")}
        categories = _categories(adapter)
        kinds = EstablishmentType.objects.filter(pk__in=categories, is_active=True).order_by("code")
        if selected_kinds is not None:
            kinds = kinds.filter(pk__in=selected_kinds)
        for kind in kinds:
            state, _ = RegistrySyncCursor.objects.get_or_create(source=system, kind=kind)
            state.last_attempt_at = timezone.now()
            state.last_error = ""
            counts = {key: 0 for key in ("created", "updated", "unchanged", "skipped", "failed")}
            try:
                payload = adapter.list_page(kind.code, state.next_page, page_size)
                records = payload if isinstance(payload, list) else payload["results"]
                if isinstance(payload, list):
                    start = (state.next_page - 1) * page_size
                    records = payload[start:start + page_size]
                for raw in records:
                    try:
                        external_id = _project(adapter, categories[kind.code], raw)["id"]
                        record = adapter.identity(kind.code, external_id)
                        if record.get("id") != external_id:
                            raise ValueError("Mismatched external ID")
                        counts[sync_registry_record(actor, source, kind.code, record)] += 1
                    except (APIException, ValueError, KeyError, TypeError):
                        # Do not log upstream bodies, IDs or personal data.
                        counts["failed"] += 1
                has_next = bool(payload.get("next")) if isinstance(payload, dict) else state.next_page * page_size < len(payload)
                state.next_page = state.next_page + 1 if has_next else 1
                state.last_success_at = timezone.now()
                if counts["failed"]:
                    state.last_error = "Some records could not be synced; they will be retried in the next pass."
                total["pages"] += 1
            except APIException as exc:
                # Keep the page for retries. No deletion or ownership changes on failure.
                detail = str(getattr(exc, "detail", "")).lower()
                if "credentials" in detail:
                    state.last_error = (
                        f"{system.name} rejected the integration key. Update it on both "
                        "servers and restart them."
                    )
                else:
                    state.last_error = "Registry page unavailable. Check its URL, credentials and API routes."
                # Shrinking lists can invalidate a persisted page; restart the next pass.
                if state.next_page > 1 and isinstance(exc, NotFound):
                    state.next_page = 1
                counts["failed"] += 1
            state.counts = counts
            state.save()
            for key, value in counts.items():
                total[key] += value
        return total
    finally:
        if locked:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [628194201])


def sync_all(actor, source="licensing", page_size=100):
    """One complete pass for initial imports/backfills; normal polling stays bounded."""
    for permission in ("view_establishment", "view_sourcelink", "add_establishment", "change_establishment", "change_sourcelink"):
        require(actor, f"establishments.{permission}")
    locked = False
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s)", [628194201])
            locked = cursor.fetchone()[0]
        if not locked:
            return {"busy": True}
    try:
        adapter = adapter_for(source)
        if not adapter or not hasattr(adapter, "list_page"):
            raise ValueError("This external system does not support automatic sync.")
        categories = _categories(adapter)
        pending = set(EstablishmentType.objects.filter(pk__in=categories, is_active=True).values_list("pk", flat=True))
        RegistrySyncCursor.objects.filter(source_id=source, kind_id__in=pending).update(next_page=1)
        total = {key: 0 for key in ("created", "updated", "unchanged", "skipped", "failed", "pages")}
        while pending:
            result = sync_batch(actor, source, page_size, selected_kinds=pending)
            for key in total:
                total[key] += result.get(key, 0)
            states = RegistrySyncCursor.objects.filter(source_id=source, kind_id__in=pending)
            completed = {state.kind_id for state in states if state.next_page == 1 or state.last_error.startswith("Registry page unavailable")}
            pending -= completed
        return total
    finally:
        if locked:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", [628194201])
