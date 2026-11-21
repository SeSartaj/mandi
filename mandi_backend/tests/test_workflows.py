from apps.establishments.models import EstablishmentType
from apps.establishments.services import connect_source, save_establishment
from apps.inspections.models import Checklist
from apps.inspections.services import deploy_checklist, save_checklist
from apps.integrations.models import CollectionSubmission, FormDeployment
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient


@override_settings(LICENSING_BASE_URL="")
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
            code="pharmacy",
            name="Pharmacy",
            establishment_kind=EstablishmentType.objects.get(pk="pharmacy"),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def upload(self, name="checklist.xlsx"):
        return SimpleUploadedFile(
            name,
            b"test workbook",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_services_enforce_write_permissions(self):
        with self.assertRaises(PermissionDenied):
            save_establishment(
                self.reader,
                {"name": "Unauthorized", "kind": "pharmacy", "province": "Kabul"},
            )

    def test_checklist_requires_xlsform_upload(self):
        values = {
            "code": "new-pharmacy",
            "name": "New pharmacy checklist",
            "establishment_kind": EstablishmentType.objects.get(pk="pharmacy"),
        }
        with self.assertRaises(ValidationError):
            save_checklist(self.manager, values)
        checklist = save_checklist(self.manager, {**values, "xlsform": self.upload()})
        self.addCleanup(checklist.xlsform.delete, save=False)
        self.assertTrue(checklist.xlsform.name.endswith(".xlsx"))

    def test_checklist_code_is_unique(self):
        with self.assertRaises(ValidationError):
            save_checklist(
                self.manager,
                {
                    "code": "pharmacy",
                    "name": "Duplicate",
                    "establishment_kind": EstablishmentType.objects.get(pk="pharmacy"),
                    "xlsform": self.upload(),
                },
            )

    def test_api_creates_and_updates_checklist_with_xlsform(self):
        response = self.client.post(
            "/api/v1/checklists/",
            {
                "code": "api-pharmacy",
                "name": "API pharmacy checklist",
                "establishment_kind": "pharmacy",
                "xlsform": self.upload("api-checklist.xlsx"),
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

    def test_checklist_deployment_requires_permission(self):
        checklist = Checklist.objects.create(
            code="deploy-test",
            name="Deploy test",
            establishment_kind=EstablishmentType.objects.get(pk="pharmacy"),
            xlsform=self.upload("deploy-checklist.xlsx"),
        )
        self.addCleanup(checklist.xlsform.delete, save=False)
        with self.assertRaises(PermissionDenied):
            deploy_checklist(self.reader, checklist.pk)

    def test_establishment_csv_exposes_stable_ids(self):
        response = self.client.get("/api/v1/integrations/establishments.csv")
        self.assertEqual(response.status_code, 200)
        text = response.content.decode()
        header = text.splitlines()[0]
        for column in (
            "name",
            "label",
            "kind",
            "province",
            "district",
            "license_number",
            "owner",
            "technical_manager",
        ):
            self.assertIn(column, header.split(","))
        self.assertIn(str(self.e.pk), text)

    def test_establishment_csv_includes_licensing_details(self):
        from apps.establishments.models import SourceLink

        SourceLink.objects.create(
            establishment=self.e,
            source="licensing",
            external_id="pharmacy:P-1",
            linked_by=self.manager,
            details={
                "name": "First",
                "address": "Main street",
                "license_number": "LIC-1",
                "license_expiry_date": "2027-01-01",
                "grade": "A",
                "owner": "Owner Name",
                "owner_phone": "0700000000",
                "technical_manager": "Manager Name",
                "technical_staff_count": 2,
                "activities": "Medicines",
            },
        )
        text = self.client.get("/api/v1/integrations/establishments.csv").content.decode()
        row = next(
            line for line in text.splitlines() if line.startswith(f"{self.e.pk},")
        )
        for value in (
            "Main street",
            "LIC-1",
            "2027-01-01",
            "Owner Name",
            "0700000000",
            "Manager Name",
            "Medicines",
        ):
            self.assertIn(value, row)

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

    def test_api_validates_submission_filters(self):
        self.assertEqual(
            self.client.get("/api/v1/submissions/?date_from=invalid").status_code, 400
        )
        self.assertEqual(
            self.client.get("/api/v1/submissions/?establishment_id=invalid").status_code,
            400,
        )
        self.assertEqual(
            self.client.get(
                "/api/v1/submissions/?date_from=2026-11-10&date_to=2026-11-01"
            ).status_code,
            400,
        )

    def test_api_lists_and_filters_submissions(self):
        deployment = FormDeployment.objects.create(
            checklist=self.checklist,
            provider="odk",
            project_id="1",
            form_id="mandi_checklist_1",
            status="deployed",
        )
        for index in range(2):
            CollectionSubmission.objects.create(
                deployment=deployment,
                submission_id=f"s{index}",
                establishment=self.e,
                form_version="v1",
            )
        response = self.client.get("/api/v1/submissions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        response = self.client.get(
            "/api/v1/submissions/", {"establishment_kind": "pharmacy"}
        )
        self.assertEqual(response.data["count"], 2)
        response = self.client.get("/api/v1/submissions/", {"establishment_kind": "factory"})
        self.assertEqual(response.data["count"], 0)
        response = self.client.get(
            "/api/v1/submissions/", {"checklist_id": self.checklist.pk}
        )
        self.assertEqual(response.data["count"], 2)

    def test_api_honours_cms_page_size_contract(self):
        for index in range(3):
            save_establishment(
                self.manager,
                {"name": f"Page {index}", "kind": "pharmacy", "province": "Kabul"},
            )
        response = self.client.get("/api/v1/establishments/", {"page_size": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["count"], 5)

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

    def test_unconfigured_source_is_rejected(self):
        with self.assertRaises(ValidationError):
            connect_source(self.manager, self.e.pk, "survey", "survey-pharmacy-001")

    def test_establishment_types_can_be_managed(self):
        created = self.client.post(
            "/api/v1/establishment-types/",
            {"code": "laboratory", "name": "Laboratory"},
        )
        self.assertEqual(created.status_code, 201)
        updated = self.client.patch(
            "/api/v1/establishment-types/laboratory/", {"is_active": False}
        )
        self.assertEqual(updated.status_code, 200)
        self.assertFalse(updated.data["is_active"])
        listing = self.client.get("/api/v1/establishment-types/")
        self.assertIn("laboratory", [item["code"] for item in listing.data])

    def test_category_change_preserves_submission_history(self):
        FormDeployment.objects.create(
            checklist=self.checklist,
            provider="odk",
            project_id="1",
            form_id="mandi_checklist_1",
            status="deployed",
        )
        CollectionSubmission.objects.create(
            deployment=FormDeployment.objects.get(),
            submission_id="s1",
            establishment=self.e,
        )
        with self.assertRaises(ValidationError):
            save_establishment(self.manager, {"kind": "factory"}, self.e.pk)

    def test_schema_lists_submissions_and_not_inspections(self):
        response = self.client.get("/api/v1/schema/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("/submissions/", response.data["paths"])
        self.assertIn("/checklists/{pk}/versions/", response.data["paths"])
        self.assertNotIn("/integrations/ingest/", response.data["paths"])
        self.assertNotIn("/inspections/", response.data["paths"])
