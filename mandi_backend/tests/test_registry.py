from copy import deepcopy
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.establishments.models import Establishment, EstablishmentType, ExternalSystem, SourceLink
from apps.establishments.services import (save_establishment, import_establishment,
    refresh_identity, transfer_ownership, disconnect_source, establishment_choice_csv)
from apps.inspections.models import Checklist
from apps.integrations.registry import ADAPTERS, detail_with_field_ids
from apps.integrations.services import source_search


@override_settings(LICENSING_BASE_URL="", LICENSING_REGISTRATION_API_KEY="")
class RegistryTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_superuser(username="registry-manager", password="test-password")
        self.native = save_establishment(self.actor, {"name": "Native pharmacy", "kind": "pharmacy", "province": "Kabul", "attributes": {"cold_storage": True}})
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def record(self, name="Registry pharmacy"):
        return {"id": "external-42", "name": name, "details": {"name": name, "province": "Herat", "license_number": "LIC-42"}, "is_demo": False}

    def imported(self):
        with patch("apps.integrations.services.source_record", return_value=self.record()):
            return import_establishment(self.actor, "licensing", "external-42", "pharmacy")

    def submission(self, establishment):
        Checklist.objects.create(
            code="registry",
            name="Registry checklist",
        )

    def test_native_attributes_and_custom_types(self):
        EstablishmentType.objects.create(code="laboratory", name="Laboratory")
        obj = save_establishment(self.actor, {"name": "Lab", "province": "Kabul", "kind": "laboratory"})
        self.assertIn(b"Laboratory", establishment_choice_csv(kind="laboratory"))
        result = self.client.get("/api/v1/registry/")
        self.assertIn({"code": "laboratory", "name": "Laboratory"}, result.data["types"])
        checklist = Checklist(name="Lab", code="lab")
        checklist.full_clean()
        checklist.save()
        self.assertEqual(checklist.code, "lab")

    def test_invalid_type_or_attributes_rejected(self):
        for extra in [{"kind": "invalid"}]:
            with self.assertRaises(ValidationError):
                save_establishment(self.actor, {"name": "Invalid", "province": "Kabul", "kind": "pharmacy", **extra})

    def test_import_is_idempotent_and_minimal(self):
        obj = self.imported()
        with patch("apps.integrations.services.source_record") as fetch:
            repeated = import_establishment(self.actor, "licensing", "external-42", "pharmacy")
        fetch.assert_not_called()
        self.assertEqual(obj.pk, repeated.pk)
        self.assertEqual(obj.primary_source, "licensing")
        details = obj.source_links.get().details
        self.assertEqual(details["name"], "Registry pharmacy")
        self.assertEqual(details["province"], "Herat")
        self.assertEqual(details["license_number"], "LIC-42")
        with self.assertRaises(ValidationError):
            import_establishment(self.actor, "licensing", "external-42", "hospital")

    def test_primary_identity_read_only_and_disconnect_protected(self):
        obj = self.imported()
        for key, value in [("name", "Changed")]:
            response = self.client.patch(f"/api/v1/establishments/{obj.pk}/", {key: value}, format="json")
            self.assertEqual(response.status_code, 400)
        with self.assertRaises(ValidationError):
            disconnect_source(self.actor, obj.pk, "licensing")

    def test_outage_leaves_local_identity_intact(self):
        obj = self.imported()
        with patch("apps.integrations.services.source_record", side_effect=ValidationError("Unavailable")):
            with self.assertRaises(ValidationError):
                refresh_identity(self.actor, obj.pk)
        self.assertEqual(self.client.get(f"/api/v1/establishments/{obj.pk}/").status_code, 200)
        obj.refresh_from_db()
        self.assertEqual(obj.name, "Registry pharmacy")

    def test_transfer_to_native_and_back(self):
        obj = self.imported()
        transfer_ownership(self.actor, obj.pk)
        save_establishment(self.actor, {"name": "Local edit"}, obj.pk)
        with patch("apps.integrations.services.source_record", return_value=self.record("Upstream again")):
            obj = transfer_ownership(self.actor, obj.pk, "licensing")
        self.assertEqual(obj.primary_source, "licensing")
        self.assertEqual(obj.name, "Upstream again")

    def test_failed_transfer_rolls_back_ownership_and_identity(self):
        obj = self.imported()
        transfer_ownership(self.actor, obj.pk)
        with patch("apps.integrations.services.source_record", side_effect=ValidationError("Unavailable")):
            with self.assertRaises(ValidationError):
                transfer_ownership(self.actor, obj.pk, "licensing")
        obj.refresh_from_db()
        self.assertIsNone(obj.primary_source)
        self.assertEqual(obj.name, "Registry pharmacy")

    def test_unique_primary_and_reverse_mapping_constraints(self):
        self.imported()
        for params in [dict(establishment=self.native, source="licensing", external_id="external-42"),
                       dict(establishment=self.native, source="survey", external_id="a", is_primary=True)]:
            if params["source"] == "survey":
                SourceLink.objects.create(establishment=self.native, source="archive", external_id="b", is_primary=True, linked_by=self.actor)
            with self.assertRaises(IntegrityError), transaction.atomic():
                SourceLink.objects.create(**params, linked_by=self.actor)

    def test_new_system_uses_registered_adapter(self):
        ExternalSystem.objects.create(code="new-registry", name="New registry", adapter="test-registry")
        class Adapter:
            def search(self, *args):
                return {"results": [], "is_demo": False, "has_next": False, "count": 0}
        with patch.dict(ADAPTERS, {"test-registry": Adapter()}):
            self.assertEqual(source_search(self.actor, "new-registry", "hospital")["results"], [])
        ExternalSystem.objects.filter(pk="new-registry").update(is_active=False)
        with self.assertRaises(ValidationError):
            source_search(self.actor, "new-registry", "hospital")

    def test_unconfigured_licensing_never_returns_demo_records(self):
        with self.assertRaisesMessage(ValidationError, "not connected"):
            source_search(self.actor, "licensing", "pharmacy")

    def test_mutation_permissions_enforced(self):
        user = get_user_model().objects.create_user(username="unauthorized")
        with self.assertRaises(PermissionDenied):
            import_establishment(user, "licensing", "external-42", "pharmacy")

    def test_import_and_ownership_api(self):
        with patch("apps.integrations.services.source_record", return_value=self.record()):
            response = self.client.post("/api/v1/registry/import/", {"source": "licensing", "kind": "pharmacy", "external_id": "external-42"})
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        self.assertEqual(response.data["primary_source"], "licensing")
        response = self.client.post(f"/api/v1/establishments/{pk}/ownership/", {"source": None}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["primary_source"])

    @override_settings(LICENSING_BASE_URL="http://licensing.test", LICENSING_REGISTRATION_API_KEY="key")
    def test_adapter_cannot_return_a_different_identity(self):
        from apps.integrations.services import source_record
        class WrongAdapter:
            def identity(self, *args):
                return {"id": "wrong"}
        with patch.dict(ADAPTERS, {"licensing": WrongAdapter()}):
            with self.assertRaisesMessage(ValidationError, "different external ID"):
                source_record(self.actor, "licensing", "expected", "pharmacy")
