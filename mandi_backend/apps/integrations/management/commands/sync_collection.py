import logging
import os
import time

from apps.integrations.collection import sync
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import close_old_connections

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Periodically import provider submissions; retries collection outages without stopping Mandi."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, **options):
        while True:
            try:
                actor = get_user_model().objects.get(
                    username=os.environ.get("MANDI_SYNC_USERNAME")
                    or os.environ.get("MANDI_ADMIN_USERNAME", "admin"),
                    is_active=True,
                )
                if settings.COLLECTION_PROVIDER == "kobo":
                    from apps.integrations.services import sync_kobo_submissions

                    counts = sync_kobo_submissions(actor)
                else:
                    counts = sync(actor)
                if counts["fetched"]:
                    logger.info("Collection sync: %s", counts)
            except Exception:
                if options["once"]:
                    raise
                logger.exception("Collection sync failed; will retry")
            finally:
                close_old_connections()
            if options["once"]:
                return
            time.sleep(max(10, int(os.environ.get("COLLECTION_SYNC_INTERVAL", "60"))))
