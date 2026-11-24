import os
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.establishments.models import Establishment, EstablishmentType, RegistrySyncRequest
from apps.integrations.registry import ADAPTERS


class FakeLicensingAdapter:
    def list_page(self, kind, page, page_size):
        return {"results": [{"application_id": "P-1", "name": "Pharmacy"}], "next": None}

    def identity(self, kind, external_id):
        return {
            "id": external_id,
            "name": "Pharmacy",
            "details": {
                "name": "Pharmacy",
                "province": "Kabul",
                "status": "completed",
                "district": "District",
            },
            "is_demo": False,
        }


@override_settings(
    LICENSING_BASE_URL="http://licensing.test",
    LICENSING_REGISTRATION_API_KEY="key",
)
class ExternalSystemEndpointTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_superuser(
            username="systems-manager", email="systems@example.test", password="Testing-2026!"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.actor)
        EstablishmentType.objects.exclude(pk="pharmacy").update(is_active=False)

    def test_systems_list_reports_connection_and_sync_capability(self):
        response = self.client.get("/api/v1/registry/systems/")
        self.assertEqual(response.status_code, 200)
        rows = {row["code"]: row for row in response.data["systems"]}
        self.assertTrue(rows["licensing"]["configured"])
        self.assertTrue(rows["licensing"]["syncable"])
        self.assertTrue(rows["licensing"]["can_sync"])
        self.assertTrue(rows["archive"]["configured"])
        self.assertFalse(rows["archive"]["syncable"])
        self.assertFalse(rows["survey"]["syncable"])
        self.assertIsNone(rows["licensing"]["full_sync"])
        self.assertTrue(response.data["enabled"])

    @patch.dict(ADAPTERS, {"licensing": FakeLicensingAdapter()})
    def test_sync_runs_one_bounded_batch(self):
        response = self.client.post(
            "/api/v1/registry/systems/licensing/sync/", {"page_size": 1}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["created"], 1)
        self.assertEqual(Establishment.objects.count(), 1)
        self.assertEqual(Establishment.objects.get().primary_source, "licensing")

    def test_derived_sources_are_not_directly_syncable(self):
        response = self.client.post("/api/v1/registry/systems/archive/sync/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_complete_sync_is_queued_once(self):
        first = self.client.post("/api/v1/registry/systems/licensing/full-sync/", {}, format="json")
        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.data["state"], "pending")
        second = self.client.post("/api/v1/registry/systems/licensing/full-sync/", {}, format="json")
        self.assertEqual(second.status_code, 200)
        self.assertFalse(second.data["queued"])
        self.assertEqual(RegistrySyncRequest.objects.count(), 1)
        systems = self.client.get("/api/v1/registry/systems/").data["systems"]
        licensing = next(row for row in systems if row["code"] == "licensing")
        self.assertEqual(licensing["full_sync"]["state"], "pending")

    @patch.dict(os.environ, {"MANDI_SYNC_USERNAME": "systems-manager"})
    @patch.dict(ADAPTERS, {"licensing": FakeLicensingAdapter()})
    @override_settings(LICENSING_SYNC_ENABLED=False)
    def test_worker_runs_queued_complete_sync(self):
        self.client.post("/api/v1/registry/systems/licensing/full-sync/", {}, format="json")
        call_command("sync_registries", "--once")
        request = RegistrySyncRequest.objects.get()
        self.assertEqual(request.state, "done")
        self.assertEqual(request.result["created"], 1)
        self.assertEqual(request.result["failed"], 0)
        self.assertEqual(Establishment.objects.count(), 1)

    @override_settings(LICENSING_BASE_URL="", LICENSING_REGISTRATION_API_KEY="")
    def test_unconfigured_connection_is_rejected(self):
        response = self.client.post(
            "/api/v1/registry/systems/licensing/sync/", {}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_sync_requires_registry_permissions(self):
        from django.contrib.auth.models import Permission

        reader = get_user_model().objects.create_user(username="systems-reader")
        reader.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="establishments", codename="view_establishment"
            )
        )
        self.client.force_authenticate(reader)
        response = self.client.post(
            "/api/v1/registry/systems/licensing/sync/", {}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Establishment.objects.exists())

    def test_listing_requires_view_permission(self):
        reader = get_user_model().objects.create_user(username="systems-outsider")
        self.client.force_authenticate(reader)
        self.assertEqual(self.client.get("/api/v1/registry/systems/").status_code, 403)
