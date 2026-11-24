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
        parser.add_argument("--source", default="licensing")

    @staticmethod
    def _actor():
        return get_user_model().objects.get(
            username=os.environ.get("MANDI_SYNC_USERNAME")
            or os.environ.get("MANDI_ADMIN_USERNAME", "admin"),
            is_active=True,
        )

    def handle(self, **options):
        from django.utils import timezone
        from apps.establishments.models import RegistrySyncRequest

        while True:
            request = None
            try:
                request = (
                    RegistrySyncRequest.objects.filter(
                        source_id=options["source"], state__in=["pending", "running"]
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
                    counts = sync_all(
                        self._actor(),
                        options["source"],
                        settings.LICENSING_SYNC_PAGE_SIZE,
                    )
                    if counts.get("busy"):
                        request.state = "pending"
                        request.started_at = None
                        request.save(update_fields=["state", "started_at"])
                        logger.info("Complete registry sync is waiting for the current batch.")
                    else:
                        request.state = "done"
                        request.result = counts
                        request.finished_at = timezone.now()
                        request.error = ""
                        request.save(
                            update_fields=["state", "result", "finished_at", "error"]
                        )
                        logger.info(
                            "Complete registry sync (%s) counts: %s",
                            options["source"],
                            counts,
                        )
                # Explicit runs are allowed even when continuous polling is off,
                # so an operator can import one source on demand.
                elif settings.LICENSING_SYNC_ENABLED or options["once"] or options["full"]:
                    sync_operation = sync_all if options["full"] else sync_batch
                    counts = sync_operation(
                        self._actor(),
                        options["source"],
                        settings.LICENSING_SYNC_PAGE_SIZE,
                    )
                    logger.info("Registry sync (%s) counts: %s", options["source"], counts)
            except Exception:
                if request is not None and request.state == "running":
                    request.state = "failed"
                    request.finished_at = timezone.now()
                    request.error = "Complete sync failed; check server configuration."
                    request.save(update_fields=["state", "finished_at", "error"])
                # No exception body/traceback: third-party exceptions can contain secrets.
                logger.error("Registry sync failed; check server configuration. Will retry.")
                if options["once"] or options["full"]:
                    raise
            finally:
                # Recycle worker connections between polls, but never inside a
                # transaction: closing would break the surrounding atomic block.
                if not connection.in_atomic_block:
                    close_old_connections()
            if options["once"] or options["full"]:
                return
            time.sleep(max(10, settings.LICENSING_SYNC_INTERVAL))
