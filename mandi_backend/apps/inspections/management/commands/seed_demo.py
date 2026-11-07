import os
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from apps.establishments.models import Establishment
from apps.establishments.services import save_establishment, connect_source
from apps.inspections.models import Checklist
from apps.inspections.services import ingest_inspection, approve_inspection


class Command(BaseCommand):
    help = (
        "Load synthetic review data. Set MANDI_DEMO_PASSWORD; never loads real records."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG or not settings.DEMO_INTEGRATIONS:
            raise CommandError("Demo seeding requires DEBUG and DEMO_INTEGRATIONS.")
        password = os.getenv("MANDI_DEMO_PASSWORD")
        if not password:
            raise CommandError(
                "Set MANDI_DEMO_PASSWORD to choose the local review password."
            )
        user, created = get_user_model().objects.get_or_create(
            username="reviewer",
            defaults={"display_name": "Review Administrator", "position": "Director"},
        )
        if created:
            user.set_password(password)
            user.save()
        managers = Group.objects.get(name="Mandi administrators")
        user.groups.add(managers)
        inspector, created = get_user_model().objects.get_or_create(
            username="demo.inspector",
            defaults={
                "display_name": "Demonstration Inspector",
                "position": "Inspector",
            },
        )
        if created:
            inspector.set_unusable_password()
            inspector.save()
        readers = Group.objects.get(name="Mandi inspectors")
        inspector.groups.add(readers)
        today = timezone.localdate()
        records = [
            ("Shifa Demonstration Pharmacy", "pharmacy", "Kabul"),
            ("Omid Demonstration Pharmacy", "pharmacy", "Herat"),
            ("Demonstration Hospital Pharmacy", "pharmacy", "Kabul"),
            ("Demonstration Wholesale", "wholesaler", "Balkh"),
            ("Demonstration Importer", "importer", "Kabul"),
            ("Demonstration Factory", "factory", "Herat"),
        ]
        establishments = []
        for name, kind, province in records:
            e = Establishment.objects.filter(name=name).first()
            if not e:
                e = save_establishment(
                    user,
                    {
                        "name": name,
                        "kind": kind,
                        "province": province,
                        "district": "Central",
                        "subtype": "hospital" if "Hospital" in name else "",
                        "address": "Synthetic review address",
                    },
                )
            establishments.append(e)
        connect_source(user, establishments[0].pk, "survey", "survey-pharmacy-001")
        for index, (e_index, kind, days, approved) in enumerate(
            [
                (0, "comprehensive", 12, True),
                (0, "follow_up", 3, False),
                (1, "comprehensive", 7, False),
                (3, "brief", 5, True),
            ]
        ):
            e = establishments[e_index]
            checklist, _ = Checklist.objects.get_or_create(
                code=f"demo-{e.kind}",
                version="review-only",
                defaults={
                    "name": f"Demonstration {e.kind} checklist",
                    "establishment_kind": e.kind,
                },
            )
            i = ingest_inspection(
                user,
                {
                    "establishment_id": e.pk,
                    "checklist_id": checklist.pk,
                    "inspected_on": today - timedelta(days=days),
                    "kind": kind,
                    "team_ids": [inspector.pk],
                    "provider": "demonstration",
                    "provider_form_id": f"demo-{e.kind}",
                    "submission_id": f"demo-{index + 1}",
                    "mapping_version": "demo-v1",
                    "is_demo": True,
                    "summary": {
                        "overall_percent": 80 if approved else 65,
                        "sections": [{"name": "Storage", "earned": 4, "possible": 5}],
                        "findings": [
                            {
                                "issue": "Demonstration: review temperature records",
                                "action": "Keep a daily log",
                                "deadline": str(today + timedelta(days=14)),
                            }
                        ],
                    },
                },
            )
            if approved:
                approve_inspection(user, i.pk)
        self.stdout.write(
            self.style.SUCCESS(
                "Review data ready. Username: reviewer. Existing passwords are not reset on rerun."
            )
        )
