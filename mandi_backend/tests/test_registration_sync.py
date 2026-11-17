from copy import deepcopy
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.exceptions import NotFound, ValidationError
from apps.establishments.models import Establishment, EstablishmentType, RegistrySyncCursor, SourceLink
from apps.establishments.services import transfer_ownership, save_establishment
from apps.integrations.licensing import LicensingError
from apps.integrations.registry import ADAPTERS, RegistrationAdapter
from apps.integrations.registry_sync import sync_batch


@override_settings(REGISTRATION_BASE_URL="http://registration.test:9000", REGISTRATION_API_KEY="registration-test-key", REGISTRATION_TIMEOUT=3)
class RegistrationSyncTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_superuser(username="sync-manager", password="test-password")
        EstablishmentType.objects.exclude(pk="pharmacy").update(is_active=False)
        self.adapter = Mock()
        self.adapter.list_page.return_value = {"results": [{"application_id": "P-1", "name": "Pharmacy"}], "next": None}
        self.record = {"id": "pharmacy:P-1", "name": "Pharmacy", "details": {"name": "Pharmacy", "province": "Kabul", "status": "completed", "district": "District"}, "is_demo": False}
        self.adapter.identity.side_effect = lambda kind, external_id: deepcopy(self.record)
        self.patcher = patch.dict(ADAPTERS, {"registration": self.adapter})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_auto_create_then_update_without_duplicates(self):
        self.assertEqual(sync_batch(self.actor)["created"], 1)
        obj = Establishment.objects.get()
        self.assertEqual(obj.kind, "pharmacy")
        self.assertEqual(obj.primary_source, "registration")
        self.assertEqual(obj.status, "completed")
        self.record["name"] = "Updated pharmacy"
        self.record["details"]["province"] = "Herat"
        self.assertEqual(sync_batch(self.actor)["updated"], 1)
        obj.refresh_from_db()
        self.assertEqual(obj.name, "Updated pharmacy")
        self.assertEqual(obj.province, "Herat")
        self.assertEqual(Establishment.objects.count(), 1)
        self.assertEqual(sync_batch(self.actor)["unchanged"], 1)

    def test_local_ownership_is_never_reclaimed(self):
        sync_batch(self.actor)
        obj = Establishment.objects.get()
        transfer_ownership(self.actor, obj.pk)
        save_establishment(self.actor, {"name": "Local owner"}, obj.pk)
        self.record["name"] = "Upstream edit"
        self.assertEqual(sync_batch(self.actor)["skipped"], 1)
        obj.refresh_from_db()
        self.assertEqual(obj.name, "Local owner")
        self.assertIsNone(obj.primary_source)

    def test_secondary_mapping_never_becomes_primary_implicitly(self):
        obj = save_establishment(self.actor, {"name": "Native", "kind": "pharmacy", "province": "Kabul"})
        SourceLink.objects.create(establishment=obj, source="registration", external_id="pharmacy:P-1", linked_by=self.actor)
        self.assertEqual(sync_batch(self.actor)["skipped"], 1)
        self.assertIsNone(obj.primary_source)
        self.assertEqual(Establishment.objects.count(), 1)

    def test_pagination_resumes_and_restarts_after_last_page(self):
        self.adapter.list_page.return_value["next"] = "http://untrusted-next.example/path"
        sync_batch(self.actor, page_size=10)
        self.assertEqual(RegistrySyncCursor.objects.get().next_page, 2)
        self.adapter.list_page.return_value = {"results": [], "next": None}
        sync_batch(self.actor, page_size=10)
        self.adapter.list_page.assert_called_with("pharmacy", 2, 10)
        self.assertEqual(RegistrySyncCursor.objects.get().next_page, 1)

    def test_page_failure_preserves_records_and_retries(self):
        sync_batch(self.actor)
        state = RegistrySyncCursor.objects.get()
        success = state.last_success_at
        state.next_page = 2
        state.save()
        self.adapter.list_page.side_effect = LicensingError("private response secret")
        self.assertEqual(sync_batch(self.actor)["failed"], 1)
        state.refresh_from_db()
        self.assertEqual(state.next_page, 2)
        self.assertEqual(state.last_success_at, success)
        self.assertNotIn("secret", state.last_error)
        self.assertEqual(Establishment.objects.count(), 1)

    def test_shrinking_list_recovers_from_invalid_page(self):
        sync_batch(self.actor)
        RegistrySyncCursor.objects.update(next_page=4)
        self.adapter.list_page.side_effect = NotFound()
        sync_batch(self.actor)
        self.assertEqual(RegistrySyncCursor.objects.get().next_page, 1)

    def test_missing_identity_does_not_create_incomplete_establishment(self):
        self.record["name"] = ""
        self.record["details"]["name"] = ""
        result = sync_batch(self.actor)
        self.assertEqual(result["failed"], 1)
        self.assertFalse(Establishment.objects.exists())

    def test_detail_failure_does_not_stop_other_records(self):
        self.adapter.list_page.return_value = {"results": [{"application_id": "bad"}, {"application_id": "P-1"}], "next": None}
        self.adapter.identity.side_effect = [NotFound(), self.record]
        result = sync_batch(self.actor)
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(Establishment.objects.count(), 1)

    def test_full_array_response_is_bounded_and_idempotent(self):
        self.adapter.list_page.return_value = [{"application_id": "P-1"}, {"application_id": "P-2"}]
        self.adapter.identity.side_effect = lambda kind, external_id: dict(self.record, id=external_id)
        self.assertEqual(sync_batch(self.actor, page_size=1)["created"], 1)
        self.assertEqual(RegistrySyncCursor.objects.get().next_page, 2)
        self.assertEqual(sync_batch(self.actor, page_size=1)["created"], 1)
        self.assertEqual(RegistrySyncCursor.objects.get().next_page, 1)

    @patch("apps.integrations.licensing.requests.get")
    def test_registration_uses_own_credentials_and_exact_contract(self, get):
        response = Mock(status_code=200)
        response.json.return_value = {"results": [], "next": None}
        get.return_value = response
        adapter = RegistrationAdapter()
        for kind, category in [("importer", "company"), ("factory", "factory"), ("pharmacy", "pharmacy"), ("wholesaler", "wholesale")]:
            adapter.list_page(kind, 2, 50)
            self.assertEqual(get.call_args.args[0], f"http://registration.test:9000/api/applications/{category}/registration/list/")
            self.assertEqual(get.call_args.kwargs["headers"]["X-API-KEY"], "registration-test-key")
            self.assertEqual(get.call_args.kwargs["params"], {"page": 2, "page_size": 50, "ordering": "created_at"})
            self.assertFalse(get.call_args.kwargs["allow_redirects"])
        response.json.return_value = {"application_id": "ID /?#", "name": "Business", "address": None}
        adapter.identity("pharmacy", "pharmacy:ID /?#")
        self.assertTrue(get.call_args.args[0].endswith("/ID%20%2F%3F%23/"))

    def test_all_four_categories_are_processed_independently(self):
        EstablishmentType.objects.filter(pk__in=["pharmacy", "factory", "importer", "wholesaler"]).update(is_active=True)
        self.adapter.list_page.side_effect = lambda kind, *args: (_ for _ in ()).throw(LicensingError()) if kind == "factory" else {"results": [], "next": None}
        result = sync_batch(self.actor)
        self.assertEqual(result["failed"], 1)
        self.assertEqual(result["pages"], 3)
        self.assertEqual(RegistrySyncCursor.objects.count(), 4)
