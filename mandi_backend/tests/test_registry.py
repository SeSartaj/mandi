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
from apps.inspections.models import Checklist, Inspection
from apps.inspections.services import ingest_inspection, approve_inspection, capture_evidence
from apps.integrations.registry import ADAPTERS, detail_with_field_ids
from apps.integrations.services import source_search


@override_settings(DEMO_INTEGRATIONS=True, LICENSING_BASE_URL="", REGISTRATION_BASE_URL="", REGISTRATION_API_KEY="")
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
            return import_establishment(self.actor, "registration", "external-42", "pharmacy")

    def submission(self, establishment):
        checklist = Checklist.objects.create(code="registry", name="Registry checklist", version="1", establishment_kind="pharmacy")
        data = {"establishment_id": establishment.pk, "checklist_id": checklist.pk,
            "inspected_on": date(2026, 11, 17), "kind": "brief", "team_ids": [self.actor.pk],
            "provider": "test", "provider_form_id": "form", "submission_id": "one", "mapping_version": "1",
            "summary": {"overall_percent": 80}}
        return ingest_inspection(self.actor, data), data

    def test_native_attributes_and_custom_types(self):
        EstablishmentType.objects.create(code="laboratory", name="Laboratory")
        obj = save_establishment(self.actor, {"name": "Lab", "province": "Kabul", "kind": "laboratory", "attributes": {"rooms": 3}})
        self.assertEqual(obj.attributes, {"rooms": 3})
        self.assertIn(b"Laboratory", establishment_choice_csv(kind="laboratory"))
        result = self.client.get("/api/v1/registry/")
        self.assertIn({"code": "laboratory", "name": "Laboratory"}, result.data["types"])
        checklist = Checklist(name="Lab", code="lab", version="1", establishment_kind="laboratory")
        checklist.full_clean()
        checklist.save()
        self.assertEqual(checklist.establishment_kind, "laboratory")

    def test_invalid_type_or_attributes_rejected(self):
        for extra in [{"kind": "invalid"}, {"attributes": []}, {"attributes": "bad"}]:
            with self.assertRaises(ValidationError):
                save_establishment(self.actor, {"name": "Invalid", "province": "Kabul", "kind": "pharmacy", **extra})

    def test_import_is_idempotent_and_minimal(self):
        obj = self.imported()
        with patch("apps.integrations.services.source_record") as fetch:
            repeated = import_establishment(self.actor, "registration", "external-42", "pharmacy")
        fetch.assert_not_called()
        self.assertEqual(obj.pk, repeated.pk)
        self.assertEqual(obj.primary_source, "registration")
        self.assertEqual(obj.source_links.get().details, {"name": "Registry pharmacy"})
        self.assertEqual(obj.license_number, "LIC-42")
        with self.assertRaises(ValidationError):
            import_establishment(self.actor, "registration", "external-42", "hospital")

    def test_primary_identity_read_only_and_disconnect_protected(self):
        obj = self.imported()
        for key, value in [("name", "Changed"), ("province", "Kabul"), ("attributes", {"x": 1})]:
            response = self.client.patch(f"/api/v1/establishments/{obj.pk}/", {key: value}, format="json")
            self.assertEqual(response.status_code, 400)
        with self.assertRaises(ValidationError):
            disconnect_source(self.actor, obj.pk, "registration")

    def test_refresh_freezes_inspection_identity_and_preserves_approval_on_resync(self):
        obj = self.imported()
        inspection, data = self.submission(obj)
        snapshot = deepcopy(inspection.establishment_snapshot)
        approve_inspection(self.actor, inspection.pk)
        with patch("apps.integrations.services.source_record", return_value=self.record("New registry name")):
            refresh_identity(self.actor, obj.pk)
        synced = ingest_inspection(self.actor, data)
        self.assertEqual(synced.establishment_snapshot, snapshot)
        self.assertTrue(synced.approved)
        response = self.client.get(f"/api/v1/inspections/{inspection.pk}/")
        self.assertEqual(response.data["establishment_name"], "Registry pharmacy")
        self.assertEqual(Establishment.objects.get(pk=obj.pk).name, "New registry name")

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
            obj = transfer_ownership(self.actor, obj.pk, "registration")
        self.assertEqual(obj.primary_source, "registration")
        self.assertEqual(obj.name, "Upstream again")

    def test_failed_transfer_rolls_back_ownership_and_identity(self):
        obj = self.imported()
        transfer_ownership(self.actor, obj.pk)
        with patch("apps.integrations.services.source_record", side_effect=ValidationError("Unavailable")):
            with self.assertRaises(ValidationError):
                transfer_ownership(self.actor, obj.pk, "registration")
        obj.refresh_from_db()
        self.assertIsNone(obj.primary_source)
        self.assertEqual(obj.name, "Registry pharmacy")

    def test_unique_primary_and_reverse_mapping_constraints(self):
        self.imported()
        for params in [dict(establishment=self.native, source="registration", external_id="external-42"),
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

    def test_unconfigured_registration_never_returns_demo_records(self):
        with self.assertRaisesMessage(ValidationError, "not configured"):
            source_search(self.actor, "registration", "pharmacy")

    def test_evidence_selected_fields_only_and_approval_reset(self):
        obj = self.imported()
        inspection, _ = self.submission(obj)
        approve_inspection(self.actor, inspection.pk)
        details = detail_with_field_ids({"sections": [{"title": "License", "fields": [{"label": "Status", "value": "Active"}, {"label": "Other", "value": "Omitted"}]}]})
        selected = details["sections"][0]["fields"][0]["id"]
        with patch("apps.integrations.services.source_detail", return_value=details):
            evidence = capture_evidence(self.actor, inspection.pk, "registration", [selected])
        self.assertEqual(len(evidence.fields), 1)
        self.assertEqual(evidence.fields[0]["value"], "Active")
        inspection.refresh_from_db()
        self.assertFalse(inspection.approved)
        transfer_ownership(self.actor, obj.pk)
        disconnect_source(self.actor, obj.pk, "registration")
        evidence.refresh_from_db()
        self.assertEqual(evidence.external_id, "external-42")

    def test_stale_or_invalid_evidence_selection_rejected(self):
        obj = self.imported()
        inspection, _ = self.submission(obj)
        old = detail_with_field_ids({"sections": [{"title": "License", "fields": [{"label": "Status", "value": "Active"}]}]})
        new = detail_with_field_ids({"sections": [{"title": "License", "fields": [{"label": "Status", "value": "Expired"}]}]})
        with patch("apps.integrations.services.source_detail", return_value=new):
            with self.assertRaises(ValidationError):
                capture_evidence(self.actor, inspection.pk, "registration", [old["sections"][0]["fields"][0]["id"]])
        self.assertEqual(inspection.evidence.count(), 0)

    def test_mutation_permissions_enforced(self):
        user = get_user_model().objects.create_user(username="unauthorized")
        with self.assertRaises(PermissionDenied):
            import_establishment(user, "registration", "external-42", "pharmacy")
        with self.assertRaises(PermissionDenied):
            capture_evidence(user, 123, "registration", ["field"])

    def test_import_and_ownership_api(self):
        with patch("apps.integrations.services.source_record", return_value=self.record()):
            response = self.client.post("/api/v1/registry/import/", {"source": "registration", "kind": "pharmacy", "external_id": "external-42"})
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        self.assertEqual(response.data["primary_source"], "registration")
        response = self.client.post(f"/api/v1/establishments/{pk}/ownership/", {"source": None}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["primary_source"])

    def test_adapter_cannot_return_a_different_identity(self):
        from apps.integrations.services import source_record
        class WrongAdapter:
            def identity(self, *args):
                return {"id": "wrong"}
        with patch.dict(ADAPTERS, {"registration": WrongAdapter()}):
            with self.assertRaisesMessage(ValidationError, "different external ID"):
                source_record(self.actor, "registration", "expected", "pharmacy")
