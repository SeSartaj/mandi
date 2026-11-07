from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.establishments.services import (
    save_establishment,
    connect_source,
    disconnect_source,
)
from apps.establishments.models import SourceLink
from apps.inspections.models import Checklist, Inspection
from apps.integrations.kobo import KoboError
from apps.inspections.services import (
    approve_inspection,
    deploy_checklist,
    ingest_inspection,
    save_checklist,
)
from apps.reporting.services import coverage


@override_settings(DEMO_INTEGRATIONS=True)
class WorkflowTests(TestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user(
            username="manager", password="TestPassword-2026!"
        )
        self.manager.user_permissions.set(Permission.objects.all())
        self.reader = get_user_model().objects.create_user(username="reader")
        self.reader.user_permissions.set(
            Permission.objects.filter(codename__startswith="view_")
        )
        self.e = save_establishment(
            self.manager, {"name": "First", "kind": "pharmacy", "province": "Kabul"}
        )
        self.empty = save_establishment(
            self.manager, {"name": "Second", "kind": "pharmacy", "province": "Kabul"}
        )
        self.checklist = Checklist.objects.create(
            code="pharmacy", version="1", name="Pharmacy", establishment_kind="pharmacy"
        )
        self.payload = {
            "establishment_id": self.e.pk,
            "checklist_id": self.checklist.pk,
            "inspected_on": date(2026, 11, 1),
            "kind": "comprehensive",
            "team_ids": [self.reader.pk],
            "provider": "test",
            "provider_form_id": "form1",
            "submission_id": "sub1",
            "mapping_version": "1",
            "summary": {"overall_percent": 80},
        }
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def test_services_enforce_write_permissions(self):
        with self.assertRaises(PermissionDenied):
            save_establishment(
                self.reader,
                {"name": "Unauthorized", "kind": "pharmacy", "province": "Kabul"},
            )
        with self.assertRaises(PermissionDenied):
            ingest_inspection(self.reader, self.payload)

    def test_manual_link_preserves_source_details_and_name(self):
        link = connect_source(
            self.manager, self.e.pk, "archive", "archive-pharmacy-001"
        )
        self.e.refresh_from_db()
        self.assertEqual(self.e.name, "First")
        self.assertEqual(link.details["name"], "Shifa Demonstration")
        self.assertTrue(link.is_demo)

    def test_external_record_cannot_map_to_two_establishments(self):
        connect_source(self.manager, self.e.pk, "archive", "archive-pharmacy-001")
        with self.assertRaises(ValidationError):
            connect_source(
                self.manager, self.empty.pk, "archive", "archive-pharmacy-001"
            )
        self.assertEqual(SourceLink.objects.count(), 1)

    def test_relink_and_unlink(self):
        connect_source(self.manager, self.e.pk, "survey", "survey-pharmacy-001")
        connect_source(self.manager, self.e.pk, "survey", "survey-pharmacy-002")
        disconnect_source(self.manager, self.e.pk, "survey")
        self.assertEqual(SourceLink.objects.count(), 0)

    def test_ingestion_retry_is_idempotent_and_keeps_approval(self):
        i = ingest_inspection(self.manager, self.payload)
        approve_inspection(self.manager, i.pk)
        retried = ingest_inspection(self.manager, self.payload)
        self.assertTrue(retried.approved)
        self.assertEqual(Inspection.objects.count(), 1)

    def test_changed_submission_resets_approval(self):
        i = ingest_inspection(self.manager, self.payload)
        approve_inspection(self.manager, i.pk)
        updated = ingest_inspection(
            self.manager, dict(self.payload, summary={"overall_percent": 50})
        )
        self.assertFalse(updated.approved)
        self.assertIsNone(updated.approved_by)
        self.assertEqual(Inspection.objects.count(), 1)

    def test_checklist_requires_xlsform_upload(self):
        values = {
            "code": "new-pharmacy",
            "name": "New pharmacy checklist",
            "version": "1",
            "establishment_kind": "pharmacy",
        }
        with self.assertRaises(ValidationError):
            save_checklist(self.manager, values)
        upload = SimpleUploadedFile(
            "pharmacy-checklist.xlsx",
            b"test workbook",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        checklist = save_checklist(self.manager, {**values, "xlsform": upload})
        self.addCleanup(checklist.xlsform.delete, save=False)
        self.assertTrue(checklist.xlsform.name.endswith(".xlsx"))

    def test_api_creates_and_updates_checklist_with_xlsform(self):
        upload = SimpleUploadedFile(
            "api-checklist.xlsx",
            b"test workbook",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response = self.client.post(
            "/api/v1/checklists/",
            {
                "code": "api-pharmacy",
                "name": "API pharmacy checklist",
                "version": "1",
                "establishment_kind": "pharmacy",
                "xlsform": upload,
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        checklist = Checklist.objects.get(pk=response.data["id"])
        self.addCleanup(checklist.xlsform.delete, save=False)
        self.assertTrue(response.data["xlsform"].endswith(".xlsx"))
        response = self.client.patch(
            f"/api/v1/checklists/{checklist.pk}/",
            {"name": "Updated API checklist"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Updated API checklist")
        self.assertTrue(response.data["xlsform"])

    def test_checklist_deployment_requires_permission_and_records_failure(self):
        upload = SimpleUploadedFile(
            "deploy-checklist.xlsx",
            b"test workbook",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        checklist = Checklist.objects.create(
            code="deploy-test",
            name="Deploy test",
            version="1",
            establishment_kind="pharmacy",
            xlsform=upload,
        )
        self.addCleanup(checklist.xlsform.delete, save=False)

        with self.assertRaises(PermissionDenied):
            deploy_checklist(self.reader, checklist.pk)

        with patch(
            "apps.inspections.services.deploy_checklist_to_kobo",
            side_effect=KoboError("KoBo rejected the form"),
        ):
            with self.assertRaises(ValidationError):
                deploy_checklist(self.manager, checklist.pk)

        checklist.refresh_from_db()
        self.assertEqual(checklist.kobo_deployment_status, "failed")
        self.assertIn("KoBo rejected the form", checklist.kobo_deployment_error)

    def test_checklist_deployment_success_records_asset(self):
        upload = SimpleUploadedFile(
            "deploy-ok.xlsx",
            b"test workbook",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        checklist = Checklist.objects.create(
            code="deploy-ok",
            name="Deploy success",
            version="1",
            establishment_kind="pharmacy",
            xlsform=upload,
        )
        self.addCleanup(checklist.xlsform.delete, save=False)
        with patch(
            "apps.inspections.services.deploy_checklist_to_kobo",
            return_value=("asset-123", {"uid": "asset-123", "deployment_status": "deployed"}),
        ):
            result = deploy_checklist(self.manager, checklist.pk)

        self.assertEqual(result.kobo_asset_uid, "asset-123")
        self.assertEqual(result.kobo_deployment_status, "deployed")
        self.assertIsNotNone(result.kobo_deployed_at)

    def test_checklist_applicability_and_team_validation(self):
        c = Checklist.objects.create(
            code="factory", version="1", name="Factory", establishment_kind="factory"
        )
        with self.assertRaises(ValidationError):
            ingest_inspection(self.manager, dict(self.payload, checklist_id=c.pk))
        with self.assertRaises(ValidationError):
            ingest_inspection(self.manager, dict(self.payload, team_ids=[999999]))

    def test_approval_is_permission_protected_and_repeat_safe(self):
        i = ingest_inspection(self.manager, self.payload)
        with self.assertRaises(PermissionDenied):
            approve_inspection(self.reader, i.pk)
        approve_inspection(self.manager, i.pk)
        approve_inspection(self.manager, i.pk)
        self.assertEqual(
            Inspection.objects.filter(approved=True, approved_by=self.manager).count(),
            1,
        )

    def test_coverage_counts_establishments_not_visits(self):
        i = ingest_inspection(self.manager, self.payload)
        approve_inspection(self.manager, i.pk)
        ingest_inspection(
            self.manager, dict(self.payload, submission_id="sub2", kind="follow_up")
        )
        report = coverage(self.manager, {})
        self.assertEqual(
            report,
            {
                "establishments": 2,
                "inspected": 1,
                "uninspected": 1,
                "visits": 2,
                "approved": 1,
                "unapproved": 1,
                "coverage_percent": 50.0,
            },
        )
        self.assertEqual(coverage(self.manager, {"approved": "false"})["visits"], 1)
        self.assertEqual(
            coverage(self.manager, {"date_from": date(2027, 1, 1)})["uninspected"], 2
        )

    def test_api_rejects_unauthenticated_and_unauthorized_actions(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/v1/establishments/").status_code, 401)
        self.client.force_authenticate(self.reader)
        self.assertEqual(
            self.client.post(
                "/api/v1/establishments/",
                {"name": "No", "kind": "pharmacy", "province": "Kabul"},
            ).status_code,
            403,
        )

    def test_api_validates_filters(self):
        self.assertEqual(
            self.client.get("/api/v1/inspections/?date_from=invalid").status_code, 400
        )
        self.assertEqual(
            self.client.get(
                "/api/v1/inspections/?establishment_id=invalid"
            ).status_code,
            400,
        )
        self.assertEqual(
            self.client.get(
                "/api/v1/reports/coverage/?date_from=2026-11-10&date_to=2026-11-01"
            ).status_code,
            400,
        )

    def test_api_honours_cms_page_size_contract(self):
        for index in range(3):
            save_establishment(
                self.manager,
                {
                    "name": f"Page {index}",
                    "kind": "pharmacy",
                    "province": "Kabul",
                },
            )
        response = self.client.get("/api/v1/establishments/", {"page_size": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["count"], 5)

    def test_api_establishment_and_inspection_detail(self):
        i = ingest_inspection(self.manager, self.payload)
        self.assertEqual(
            self.client.get(f"/api/v1/establishments/{self.e.pk}/").status_code, 200
        )
        response = self.client.get(f"/api/v1/inspections/{i.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["team"][0]["id"], self.reader.pk)
        self.assertEqual(response.data["checklist"]["version"], "1")

    def test_choices_carry_stable_ids(self):
        response = self.client.get(
            "/api/v1/integrations/establishment-choices/?kind=pharmacy"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {r["name"] for r in response.data}, {str(self.e.pk), str(self.empty.pk)}
        )

    def test_login_and_logout_revoke_token(self):
        self.client.force_authenticate(None)
        response = self.client.post(
            "/api/v1/auth/login/",
            {"username": "manager", "password": "TestPassword-2026!"},
        )
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION="Token " + response.data["token"])
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 200)
        self.assertEqual(self.client.post("/api/v1/auth/logout/").status_code, 204)
        self.assertEqual(self.client.get("/api/v1/auth/me/").status_code, 401)

    @override_settings(DEMO_INTEGRATIONS=False)
    def test_demo_sources_disabled_explicitly(self):
        with self.assertRaises(ValidationError):
            connect_source(self.manager, self.e.pk, "survey", "survey-pharmacy-001")

    def test_category_change_preserves_inspection_history(self):
        ingest_inspection(self.manager, self.payload)
        with self.assertRaises(ValidationError):
            save_establishment(self.manager, {"kind": "factory"}, self.e.pk)

    def test_summary_and_schema_contract(self):
        response = self.client.post(
            "/api/v1/integrations/ingest/",
            dict(
                self.payload,
                establishment_id=str(self.e.pk),
                inspected_on="2026-11-01",
                summary={"findings": [{"issue": "Storage", "deadline": "2026-12-01"}]},
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["summary"]["findings"][0]["deadline"], "2026-12-01"
        )
        invalid = self.client.post(
            "/api/v1/integrations/ingest/",
            dict(
                self.payload,
                establishment_id=str(self.e.pk),
                inspected_on="2026-11-01",
                summary={"sections": [{"name": "Storage", "earned": 6, "possible": 5}]},
            ),
            format="json",
        )
        self.assertEqual(invalid.status_code, 400)
        response = self.client.get("/api/v1/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/integrations/ingest/", response.data["paths"])
