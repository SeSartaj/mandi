import logging
import os
import time
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import close_old_connections, connection
from apps.integrations.registry_sync import sync_batch, sync_all

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Automatically create and refresh primary registry establishments in bounded batches."
    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--full", action="store_true", help="Run one complete pass, then exit.")
        parser.add_argument(
            "--source",
            action="append",
            help="Limit sync to this external system code. Repeat for more than one source.",
        )

    @staticmethod
    def _actor():
        return get_user_model().objects.get(
            username=os.environ.get("MANDI_SYNC_USERNAME")
            or os.environ.get("MANDI_ADMIN_USERNAME", "admin"),
            is_active=True,
        )

    @staticmethod
    def _configured_sources(requested):
        """Default to every active source with a live, configured adapter."""
        from apps.establishments.models import ExternalSystem, RegistrySyncRequest
        from apps.integrations import licensing, survey
        from apps.integrations.registry import ADAPTERS

        if requested:
            return list(dict.fromkeys(requested))
        # A queued request must not stay pending forever after credentials are removed.
        pending = set(
            RegistrySyncRequest.objects.filter(state__in=["pending", "running"]).values_list(
                "source_id", flat=True
            )
        )
        sources = []
        for system in ExternalSystem.objects.filter(is_active=True).order_by("name"):
            adapter = ADAPTERS.get(system.adapter)
            if adapter is None or not hasattr(adapter, "list_page"):
                if system.code in pending:
                    sources.append(system.code)
                continue
            if system.code not in pending:
                if system.adapter == "licensing" and not licensing.configured():
                    continue
                if system.adapter == "survey" and not survey.configured():
                    continue
            sources.append(system.code)
        # Preserve the historic single-source behaviour when nothing is configured.
        return sources or ["licensing"]

    @staticmethod
    def _settings_for(source):
        if source == "survey":
            return (
                settings.SURVEY_SYNC_ENABLED,
                settings.SURVEY_SYNC_INTERVAL,
                settings.SURVEY_SYNC_PAGE_SIZE,
            )
        return (
            settings.LICENSING_SYNC_ENABLED,
            settings.LICENSING_SYNC_INTERVAL,
            settings.LICENSING_SYNC_PAGE_SIZE,
        )

    def _run_source(self, source, options):
        from django.utils import timezone
        from apps.establishments.models import RegistrySyncRequest

        enabled, _, page_size = self._settings_for(source)
        request = (
            RegistrySyncRequest.objects.filter(
                source_id=source, state__in=["pending", "running"]
            )
            .order_by("requested_at")
            .first()
        )
        if request is not None:
            # A complete pass can take minutes, so it is queued from the
            # UI and executed here, outside the HTTP request.
            if request.state == "pending":
                request.state = "running"
                request.started_at = timezone.now()
                request.save(update_fields=["state", "started_at"])
            counts = sync_all(self._actor(), source, page_size)
            if counts.get("busy"):
                request.state = "pending"
                request.started_at = None
                request.save(update_fields=["state", "started_at"])
                logger.info("Complete registry sync (%s) is waiting for the current batch.", source)
            else:
                request.state = "done"
                request.result = counts
                request.finished_at = timezone.now()
                request.error = ""
                request.save(update_fields=["state", "result", "finished_at", "error"])
                logger.info("Complete registry sync (%s) counts: %s", source, counts)
            return
        # Explicit runs are allowed even when continuous polling is off,
        # so an operator can import one source on demand.
        if enabled or options["once"] or options["full"]:
            sync_operation = sync_all if options["full"] else sync_batch
            counts = sync_operation(self._actor(), source, page_size)
            logger.info("Registry sync (%s) counts: %s", source, counts)

    @staticmethod
    def _mark_failed(source):
        from django.utils import timezone
        from apps.establishments.models import RegistrySyncRequest

        request = RegistrySyncRequest.objects.filter(source_id=source, state="running").first()
        if request is not None:
            request.state = "failed"
            request.finished_at = timezone.now()
            request.error = "Complete sync failed; check server configuration."
            request.save(update_fields=["state", "finished_at", "error"])

    def handle(self, **options):
        sources = self._configured_sources(options.get("source"))
        while True:
            for source in sources:
                try:
                    self._run_source(source, options)
                except Exception:
                    # No exception body/traceback: third-party exceptions can contain secrets.
                    logger.error(
                        "Registry sync (%s) failed; check server configuration. Will retry.",
                        source,
                    )
                    self._mark_failed(source)
                    if options["once"] or options["full"]:
                        raise
                finally:
                    # Recycle worker connections between polls, but never inside a
                    # transaction: closing would break the surrounding atomic block.
                    if not connection.in_atomic_block:
                        close_old_connections()
            if options["once"] or options["full"]:
                return
            intervals = [
                self._settings_for(source)[1]
                for source in sources
                if self._settings_for(source)[0]
            ]
            time.sleep(max(10, min(intervals or [settings.LICENSING_SYNC_INTERVAL])))
