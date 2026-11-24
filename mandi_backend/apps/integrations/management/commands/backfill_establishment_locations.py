"""Backfill coordinates from registry list pages without fetching personal profiles."""
from django.core.management.base import BaseCommand, CommandError
from apps.establishments.models import SourceLink, Establishment
from apps.integrations.registry import adapter_for
from apps.integrations.licensing import candidate, KIND_CATEGORIES


class Command(BaseCommand):
    help = "Save coordinates for existing primary registry establishments from all registry list pages."

    def add_arguments(self, parser):
        parser.add_argument("--source", default="licensing")

    def handle(self, **options):
        source = options["source"]
        adapter = adapter_for(source)
        if not adapter or not hasattr(adapter, "list_page"):
            raise CommandError("This registry does not support listing establishments.")
        updated = 0
        for kind, category in KIND_CATEGORIES.items():
            links = dict(SourceLink.objects.filter(source=source, is_primary=True,
                establishment__kind=kind).values_list("external_id", "establishment_id"))
            if not links:
                continue
            page = 1
            while True:
                payload = adapter.list_page(kind, page, 100)
                rows = payload if isinstance(payload, list) else payload["results"]
                if isinstance(payload, list):
                    rows = rows[(page - 1) * 100:page * 100]
                for raw in rows:
                    record = candidate(category, raw)
                    pk = links.get(record["id"])
                    location = record["details"].get("location")
                    if pk and location:
                        # Match ownership again in case it changed during this request.
                        updated += Establishment.objects.filter(pk=pk, source_links__source=source,
                            source_links__external_id=record["id"], source_links__is_primary=True).update(**location)
                has_next = page * 100 < len(payload) if isinstance(payload, list) else bool(payload.get("next"))
                if not has_next:
                    break
                page += 1
        self.stdout.write(self.style.SUCCESS(f"Saved coordinates for {updated} establishments."))
