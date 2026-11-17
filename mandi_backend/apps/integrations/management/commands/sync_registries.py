import logging
import os
import time
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from apps.integrations.registry_sync import sync_batch, sync_all

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Automatically create and refresh primary registry establishments in bounded batches."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--full", action="store_true", help="Run one complete pass, then exit.")
        parser.add_argument("--source", default="registration")

    def handle(self, **options):
        while True:
            try:
                if settings.REGISTRATION_SYNC_ENABLED:
                    actor = get_user_model().objects.get(username=os.environ.get("MANDI_SYNC_USERNAME") or os.environ.get("MANDI_ADMIN_USERNAME", "admin"), is_active=True)
                    sync_operation = sync_all if options["full"] else sync_batch
                    counts = sync_operation(actor, options["source"], settings.REGISTRATION_SYNC_PAGE_SIZE)
                    logger.info("Registry sync counts: %s", counts)
            except Exception:
                # No exception body/traceback: third-party exceptions can contain secrets.
                logger.error("Registry sync failed; check server configuration. Will retry.")
                if options["once"] or options["full"]:
                    raise
            finally:
                close_old_connections()
            if options["once"] or options["full"]:
                return
            time.sleep(max(10, settings.REGISTRATION_SYNC_INTERVAL))
