import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from apps.integrations.entities import sync_entities
from apps.integrations.models import FormDeployment

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reconcile Mandi establishments into the ODK Central Entity List."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")
        parser.add_argument("--project", default=None)
        parser.add_argument("--dataset", default=None)

    def handle(self, **options):
        while True:
            try:
                if options["project"]:
                    projects = [options["project"]]
                else:
                    projects = list(
                        FormDeployment.objects.filter(status="deployed")
                        .values_list("project_id", flat=True)
                        .distinct()
                    ) or [settings.ODK_PROJECT_ID]
                for project in projects:
                    counts = sync_entities(
                        project_id=project,
                        name=options["dataset"],
                    )
                    logger.info("Entity sync (%s) counts: %s", project, counts)
            except Exception:
                # Never log upstream responses; they can contain personal data.
                logger.error("Entity sync failed; check Central configuration.")
                if options["once"]:
                    raise
            finally:
                close_old_connections()
            if options["once"]:
                return
            time.sleep(max(30, settings.ENTITY_SYNC_INTERVAL))
