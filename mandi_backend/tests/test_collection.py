import io
import uuid
from datetime import timedelta
from unittest.mock import Mock, patch

import requests
from apps.accounts.services import update_employee
from apps.establishments.models import Establishment, EstablishmentType
from apps.inspections.models import Checklist
from apps.inspections.services import deploy_checklist
from apps.integrations.collection import provision, revoke, sync
from apps.integrations.models import (
    CollectionSubmission,
    CollectorGrant,
    EntityBinding,
    FormDeployment,
)
from apps.integrations.odk import CollectionError, OdkProvider
from apps.integrations.odk import request as odk_request
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone
from openpyxl import Workbook, load_workbook
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient


def workbook():
    book = Workbook()
    survey = book.active
    survey.title = "survey"
    survey.append(["type", "name", "label"])
    survey.append(["integer", "score_total", "Score"])
    settings = book.create_sheet("settings")
    settings.append(["form_id", "version", "form_title"])
    settings.append(["original", "1", "Original"])
    out = io.BytesIO()
    book.save(out)
    return out.getvalue()


@override_settings(
    COLLECTION_PROVIDER="odk",
    ODK_PROJECT_ID="1",
    ODK_PUBLIC_URL="https://collect.test",
)
class CollectionWorkflowTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="admin", password="TestPassword-2026!"
        )
        self.collector = get_user_model().objects.create_user(
            username="collector", display_name="Collector"
        )
        self.establishment = Establishment.objects.create(
            name="Pharmacy", kind=EstablishmentType.objects.get(pk="pharmacy")
        )
        self.checklist = Checklist.objects.create(
            code="test",
            name="Checklist",
            xlsform=SimpleUploadedFile("test.xlsx", workbook()),
        )
        self.deployment = FormDeployment.objects.create(
            checklist=self.checklist,
            provider="odk",
            project_id="1",
            form_id="mandi_1",
            status="deployed",
        )
        self.grant = CollectorGrant.objects.create(
            user=self.collector, deployment=self.deployment, remote_id=123
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def tearDown(self):
        self.checklist.xlsform.delete(save=False)

    def test_establishment_detail_reports_inspection_counters(self):
        older = timezone.now() - timedelta(days=800)
        for index, submitted_at in enumerate(
            [timezone.now(), timezone.now(), older], start=1
        ):
            CollectionSubmission.objects.create(
                deployment=self.deployment,
                submission_id=f"submission-{index}",
                establishment=self.establishment,
                submitted_at=submitted_at,
                data={},
            )
        response = self.client.get(f"/api/v1/establishments/{self.establishment.pk}/")
        self.assertEqual(response.status_code, 200)
        stats = response.data["inspection_stats"]
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["this_year"], 2)
        self.assertIsNotNone(stats["last_submitted_at"])

    def test_establishment_detail_reports_empty_counters_without_submissions(self):
        response = self.client.get(f"/api/v1/establishments/{self.establishment.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["inspection_stats"],
            {"total": 0, "this_year": 0, "last_submitted_at": None},
        )

    @patch("apps.integrations.collection.sync_entities", return_value={"failed": 0})
    @patch("apps.integrations.collection.ensure_dataset", return_value="establishments")
    @patch("apps.integrations.collection.provider")
    def test_deployment_preserves_original_and_links_entity_list(
        self, provider, ensure, sync_entities
    ):
        Establishment.objects.create(
            name="Factory", kind=EstablishmentType.objects.get(pk="factory")
        )
        original = self.checklist.xlsform.read()
        self.checklist.xlsform.close()
        deploy_checklist(self.admin, self.checklist.pk)
        args = provider.return_value.deploy.call_args.args
        kwargs = provider.return_value.deploy.call_args.kwargs
        prepared = load_workbook(io.BytesIO(args[1]))
        self.assertEqual(prepared["survey"].cell(2, 2).value, "establishment_id")
        self.assertEqual(
            prepared["settings"].cell(2, 1).value, f"mandi_checklist_{self.checklist.pk}"
        )
        self.assertEqual(kwargs["dataset"], "establishments")
        ensure.assert_called_once()
        sync_entities.assert_called_once_with("1", "establishments")
        with self.checklist.xlsform.open() as source:
            self.assertEqual(source.read(), original)
        self.deployment.refresh_from_db()
        self.assertEqual(self.deployment.status, "deployed")
        self.assertEqual(self.deployment.entity_list, "establishments")

    def test_corrupt_workbook_returns_validation_error_and_retryable_status(self):
        self.checklist.xlsform.save(
            "corrupt.xlsx", SimpleUploadedFile("corrupt.xlsx", b"not a workbook")
        )
        with self.assertRaises(ValidationError):
            deploy_checklist(self.admin, self.checklist.pk)
        self.deployment.refresh_from_db()
        self.assertEqual(self.deployment.status, "failed")

    @patch("apps.integrations.odk.list_projects")
    def test_projects_are_listed_through_mandi(self, list_projects):
        list_projects.return_value = [
            {"id": 1, "name": "Default", "description": "", "archived": False}
        ]
        response = self.client.get("/api/v1/odk/projects/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["name"], "Default")

    @patch("apps.integrations.odk.create_project")
    def test_projects_can_be_created(self, create_project):
        create_project.return_value = {
            "id": 2,
            "name": "New project",
            "archived": False,
        }
        response = self.client.post(
            "/api/v1/odk/projects/", {"name": "New project"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["id"], 2)

    @patch("apps.integrations.odk.create_project")
    def test_project_create_reports_missing_central_role(self, create_project):
        forbidden = Mock(status_code=403)
        error = CollectionError("refused")
        error.__cause__ = requests.HTTPError(response=forbidden)
        create_project.side_effect = error
        response = self.client.post(
            "/api/v1/odk/projects/", {"name": "Blocked"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Administrator", str(response.data["collection"]))

    @patch("apps.integrations.odk.update_project")
    def test_projects_can_be_renamed_and_archived(self, update_project):
        update_project.return_value = {
            "id": 2,
            "name": "Renamed",
            "archived": True,
        }
        response = self.client.patch(
            "/api/v1/odk/projects/2/",
            {"name": "Renamed", "archived": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["archived"])

    @patch("apps.integrations.collection.sync_entities", return_value={"failed": 0})
    @patch("apps.integrations.collection.ensure_dataset", return_value="establishments")
    @patch("apps.integrations.collection.provider")
    def test_deploy_uses_the_selected_project(self, provider, ensure, sync_entities):
        deploy_checklist(self.admin, self.checklist.pk, project_id=5)
        self.deployment.refresh_from_db()
        self.assertEqual(self.deployment.project_id, "5")
        sync_entities.assert_called_once_with("5", "establishments")

    @patch("apps.integrations.collection.sync_entities", return_value={"failed": 0})
    @patch("apps.integrations.collection.ensure_dataset", return_value="establishments")
    @patch("apps.integrations.collection.provider")
    def test_failure_is_retryable_and_concurrent_publish_is_rejected(
        self, provider, ensure, sync_entities
    ):
        provider.return_value.deploy.side_effect = CollectionError("offline")
        with self.assertRaises(ValidationError):
            deploy_checklist(self.admin, self.checklist.pk)
        self.deployment.refresh_from_db()
        self.assertEqual(self.deployment.status, "failed")
        self.deployment.status = "deploying"
        from django.utils import timezone

        self.deployment.started_at = timezone.now()
        self.deployment.save()
        with self.assertRaises(ValidationError):
            deploy_checklist(self.admin, self.checklist.pk)
        self.assertEqual(provider.return_value.deploy.call_count, 1)

    @patch("apps.integrations.odk.request")
    @patch("apps.integrations.collection.provider")
    def test_sync_stores_submissions_with_form_version_idempotently(
        self, provider, request
    ):
        request.return_value.json.return_value = []
        binding = EntityBinding.objects.create(
            establishment=self.establishment,
            project_id=self.deployment.project_id,
            entity_uuid=uuid.uuid4(),
        )
        row = {
            "__id": "uuid:one",
            "establishment_id": str(binding.entity_uuid),
            "result_pct": 80,
            "__system": {
                "submissionDate": "2026-11-15T10:00:00Z",
                "submitterId": 123,
                "formVersion": "20261115120000",
            },
            "section": {"answer": "yes"},
        }
        provider.return_value.submissions.return_value = [OdkProvider.normalize(row)]
        counts = sync(self.admin)
        self.assertEqual(counts["created"], 1)
        submission = CollectionSubmission.objects.get()
        self.assertEqual(submission.establishment, self.establishment)
        self.assertEqual(submission.establishment_snapshot["name"], "Pharmacy")
        self.assertEqual(submission.form_version, "20261115120000")
        self.assertEqual(submission.data["section"]["answer"], "yes")
        sync(self.admin)
        self.assertEqual(CollectionSubmission.objects.count(), 1)
        self.assertEqual(sync(self.admin)["updated"], 1)

    @patch("apps.integrations.odk.request")
    @patch("apps.integrations.collection.provider")
    def test_submission_without_establishment_is_accepted(self, provider, request):
        request.return_value.json.return_value = []
        row = {
            "__id": "uuid:no-establishment",
            "__system": {
                "submissionDate": "2026-11-15T10:00:00Z",
                "formVersion": "1",
            },
            "question": "answer",
        }
        provider.return_value.submissions.return_value = [OdkProvider.normalize(row)]
        counts = sync(self.admin)
        self.assertEqual(counts["created"], 1)
        submission = CollectionSubmission.objects.get()
        self.assertIsNone(submission.establishment)

    @patch("apps.integrations.odk.request")
    @patch("apps.integrations.collection.provider")
    def test_invalid_establishment_is_skipped_without_inventing_records(
        self, provider, request
    ):
        request.return_value.json.return_value = []
        provider.return_value.submissions.return_value = [
            OdkProvider.normalize(item)
            for item in [
                {"__id": "bad", "establishment_id": "not-a-uuid"},
                {
                    "__id": "unknown",
                    "establishment_id": str(uuid.uuid4()),
                    "__system": {"submissionDate": "2026-11-15T10:00:00Z"},
                },
            ]
        ]
        counts = sync(self.admin)
        self.assertEqual(counts["skipped"], 2)
        self.assertEqual(CollectionSubmission.objects.count(), 0)

    @patch("apps.integrations.collection.provider")
    def test_revoke_before_deactivation_and_token_not_persisted(self, provider):
        with self.assertRaises(ValidationError):
            update_employee(self.admin, self.collector.pk, {"is_active": False})
        provider.return_value.delete_collector.side_effect = CollectionError("offline")
        with self.assertRaises(CollectionError):
            revoke(self.admin, self.grant)
        self.grant.refresh_from_db()
        self.assertTrue(self.grant.active)
        provider.return_value.delete_collector.side_effect = None
        revoke(self.admin, self.grant)
        provider.return_value.create_collector.return_value = {
            "id": "124",
            "token": "private-token",
        }
        provider.return_value.collector_configuration.return_value = {
            "server_url": "https://collect.test/v1/key/private-token/projects/1"
        }
        result = provision(self.admin, self.collector, [self.checklist.pk])
        self.assertIn("private-token", result["credentials"][0]["server_url"])
        self.assertNotIn("token", [field.name for field in CollectorGrant._meta.fields])
        provider.return_value.create_collector.assert_called_once_with("1", "Collector")
        provider.return_value.assign_collector.assert_called_once()
        revoke(self.admin, CollectorGrant.objects.get(user=self.collector, active=True))
        provider.return_value.delete_collector.assert_called_with("1", "124")
        update_employee(self.admin, self.collector.pk, {"is_active": False})
        self.collector.refresh_from_db()
        self.assertFalse(self.collector.is_active)

    @patch("apps.integrations.collection.provider")
    def test_one_credential_can_cover_multiple_checklists_in_a_project(self, provider):
        other = Checklist.objects.create(
            code="test-2",
            name="Second checklist",
            xlsform=SimpleUploadedFile("test2.xlsx", workbook()),
        )
        self.addCleanup(other.xlsform.delete, save=False)
        FormDeployment.objects.create(
            checklist=other,
            provider="odk",
            project_id="1",
            form_id="mandi_2",
            status="deployed",
        )
        worker = get_user_model().objects.create_user(
            username="multi-collector", display_name="Multi Collector"
        )
        provider.return_value.create_collector.return_value = {
            "id": "200",
            "token": "shared-token",
        }
        provider.return_value.collector_configuration.return_value = {
            "server_url": "https://collect.test/v1/key/shared-token/projects/1"
        }

        result = provision(self.admin, worker, [self.checklist.pk, other.pk])

        self.assertEqual(provider.return_value.create_collector.call_count, 1)
        self.assertEqual(provider.return_value.assign_collector.call_count, 2)
        self.assertEqual(len(result["credentials"]), 1)
        self.assertEqual(len(result["credentials"][0]["checklists"]), 2)
        grants = list(CollectorGrant.objects.filter(user=worker, active=True))
        self.assertEqual(len(grants), 2)
        self.assertEqual({grant.remote_id for grant in grants}, {"200"})

        revoke(self.admin, grants[0])
        provider.return_value.unassign_collector.assert_called_once()
        provider.return_value.delete_collector.assert_not_called()
        self.assertEqual(
            CollectorGrant.objects.filter(user=worker, active=True).count(), 1
        )

        revoke(self.admin, grants[1])
        provider.return_value.delete_collector.assert_called_once_with("1", "200")
        self.assertEqual(
            CollectorGrant.objects.filter(user=worker, active=True).count(), 0
        )

    @patch("apps.integrations.collection.provider")
    def test_checklists_in_different_projects_get_separate_credentials(self, provider):
        other = Checklist.objects.create(
            code="test-3",
            name="Other project checklist",
            xlsform=SimpleUploadedFile("test3.xlsx", workbook()),
        )
        self.addCleanup(other.xlsform.delete, save=False)
        FormDeployment.objects.create(
            checklist=other,
            provider="odk",
            project_id="2",
            form_id="mandi_3",
            status="deployed",
        )
        worker = get_user_model().objects.create_user(
            username="cross-project", display_name="Cross Project"
        )
        provider.return_value.create_collector.side_effect = [
            {"id": "301", "token": "token-1"},
            {"id": "302", "token": "token-2"},
        ]
        provider.return_value.collector_configuration.side_effect = (
            lambda project_id, token: {
                "server_url": f"https://collect.test/v1/key/{token}/projects/{project_id}"
            }
        )

        result = provision(self.admin, worker, [self.checklist.pk, other.pk])

        self.assertEqual(provider.return_value.create_collector.call_count, 2)
        self.assertEqual(provider.return_value.assign_collector.call_count, 2)
        self.assertEqual(
            {credential["project_id"] for credential in result["credentials"]},
            {1, 2},
        )
        self.assertEqual(
            set(
                CollectorGrant.objects.filter(user=worker, active=True).values_list(
                    "remote_id", flat=True
                )
            ),
            {"301", "302"},
        )

    @patch("apps.integrations.collection.provider")
    def test_collection_access_api_accepts_multiple_checklists(self, provider):
        other = Checklist.objects.create(
            code="api-second",
            name="API second checklist",
            xlsform=SimpleUploadedFile("api-second.xlsx", workbook()),
        )
        self.addCleanup(other.xlsform.delete, save=False)
        FormDeployment.objects.create(
            checklist=other,
            provider="odk",
            project_id="1",
            form_id="mandi_api_second",
            status="deployed",
        )
        worker = get_user_model().objects.create_user(
            username="api-collector", display_name="API collector"
        )
        provider.return_value.create_collector.return_value = {
            "id": "700",
            "token": "api-token",
        }
        provider.return_value.collector_configuration.return_value = {
            "server_url": "https://collect.test/v1/key/api-token/projects/1"
        }
        response = self.client.post(
            f"/api/v1/employees/{worker.pk}/collection-access/",
            {"checklist_ids": [self.checklist.pk, other.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(response.data["credentials"]), 1)
        self.assertEqual(len(response.data["credentials"][0]["checklists"]), 2)
        listing = self.client.get(
            f"/api/v1/employees/{worker.pk}/collection-access/"
        )
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(len(listing.data), 1)
        self.assertEqual(listing.data[0]["project_id"], 1)
        self.assertEqual(len(listing.data[0]["checklists"]), 2)

    def test_checklist_scope_protects_submissions_and_downloads(self):
        self.collector.restrict_checklist_access = True
        self.collector.save()
        from django.contrib.auth.models import Permission

        self.collector.user_permissions.set(
            Permission.objects.filter(codename__startswith="view_")
        )
        self.client.force_authenticate(self.collector)
        CollectionSubmission.objects.create(
            deployment=self.deployment,
            establishment=self.establishment,
            submission_id="s1",
        )
        response = self.client.get(
            f"/api/v1/checklists/{self.checklist.pk}/collection-submissions/"
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            self.client.get(
                f"/api/v1/checklists/{self.checklist.pk}/download/"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.get("/api/v1/collection-submissions/1/").status_code, 404
        )

    def test_password_reset_revokes_login_token_and_cannot_escalate_to_superuser(self):
        from rest_framework.authtoken.models import Token

        Token.objects.create(user=self.collector)
        update_employee(
            self.admin, self.collector.pk, {"password": "NewPassword-2026!"}
        )
        self.assertFalse(Token.objects.filter(user=self.collector).exists())
        self.assertEqual(
            self.client.patch(
                f"/api/v1/employees/{self.collector.pk}/",
                {"is_superuser": True},
                format="json",
            ).status_code,
            200,
        )
        self.collector.refresh_from_db()
        self.assertFalse(self.collector.is_superuser)


class OdkAdapterTests(SimpleTestCase):
    def test_settings_qr_is_a_png_data_uri(self):
        from apps.integrations.odk import build_settings_qr

        qr = build_settings_qr("https://collect.test/v1/key/x/projects/1", "Pharmacy")
        self.assertTrue(qr.startswith("data:image/png;base64,"))

    def test_normalization_contract_is_independent_of_central_metadata(self):
        remote = OdkProvider.normalize(
            {
                "__id": "uuid:s1",
                "establishment_id": "est-1",
                "__system": {
                    "submitterId": 123,
                    "submissionDate": "2026-11-15T10:00:00Z",
                    "formVersion": "20261115120000",
                },
            }
        )
        self.assertEqual(remote.submission_id, "uuid:s1")
        self.assertEqual(remote.form_version, "20261115120000")
        self.assertIsNotNone(remote.submitted_at)

    @patch("apps.integrations.odk.request")
    def test_form_versions_accepts_list_and_paginated_responses(self, request):
        deployment = Mock(project_id="1", form_id="form")
        request.return_value.json.return_value = [
            {"version": "2", "publishedAt": "2026-11-16T10:00:00Z"},
            {"version": "1", "publishedAt": "2026-11-15T10:00:00Z"},
        ]
        self.assertEqual(
            [item["version"] for item in OdkProvider().form_versions(deployment)],
            ["2", "1"],
        )
        request.return_value.json.return_value = {
            "value": [{"version": "3", "publishedAt": None}]
        }
        self.assertEqual(
            [item["version"] for item in OdkProvider().form_versions(deployment)],
            ["3"],
        )

    @patch("apps.integrations.odk.request")
    def test_revocation_is_idempotent_after_external_deletion(self, request):
        cause = requests.HTTPError(response=Mock(status_code=404))
        error = CollectionError("Missing")
        error.__cause__ = cause
        request.side_effect = error
        OdkProvider().delete_collector("1", "123")

    @patch("apps.integrations.odk.request")
    def test_pagination_never_sends_credentials_to_another_host(self, request):
        request.return_value.json.return_value = {
            "value": [],
            "@odata.nextLink": "https://attacker.test/v1/stolen",
        }
        deployment = Mock(project_id="1", form_id="form")
        with (
            override_settings(ODK_BASE_URL="https://collect.test"),
            self.assertRaises(CollectionError),
        ):
            list(OdkProvider().submissions(deployment))
        self.assertEqual(request.call_count, 1)

    @patch("apps.integrations.odk.request")
    def test_adapter_does_not_create_form_after_auth_failure(self, request):
        response = Mock(status_code=401)
        cause = requests.HTTPError(response=response)
        error = CollectionError("Unauthorized")
        error.__cause__ = cause
        request.side_effect = error
        with self.assertRaises(CollectionError):
            OdkProvider().deploy(Mock(project_id="1", form_id="form"), b"file")
        self.assertEqual(request.call_count, 1)

    @patch("apps.integrations.odk.request")
    def test_new_form_draft_attachment_and_publish_contract(self, request):
        response = Mock(status_code=404)
        cause = requests.HTTPError(response=response)
        error = CollectionError("Missing")
        error.__cause__ = cause
        attachment_response = Mock()
        attachment_response.json.return_value = [{"name": "establishments.csv"}]
        request.side_effect = [error, Mock(), attachment_response, Mock(), Mock()]
        OdkProvider().deploy(
            Mock(project_id="1", form_id="my/form"),
            b"xls",
            dataset="establishments",
        )
        calls = request.call_args_list
        self.assertEqual(calls[1].args, ("POST", "projects/1/forms"))
        self.assertEqual(calls[1].kwargs["params"], {"publish": "false"})
        self.assertEqual(calls[-1].args[1], "projects/1/forms/my%2Fform/draft/publish")

    @patch("apps.integrations.odk.request")
    def test_redeploy_reports_structure_warnings_with_a_hint(self, request):
        warning = Mock(status_code=400)
        warning.json.return_value = {
            "code": 400.16,
            "details": {"fields": ["label"]},
        }
        error = CollectionError("structure changed")
        error.__cause__ = requests.HTTPError(response=warning)
        request.side_effect = [Mock(), error]
        with self.assertRaises(CollectionError) as raised:
            OdkProvider().deploy(Mock(project_id="1", form_id="form"), b"xls")
        message = str(raised.exception)
        self.assertIn("label", message)
        self.assertIn("new checklist", message)
        self.assertFalse(
            any(
                call.kwargs.get("params", {}).get("ignoreWarnings") == "true"
                for call in request.call_args_list
            )
        )

    @patch("apps.integrations.odk.request")
    def test_force_redeploy_confirms_structure_warning(self, request):
        warning = Mock(status_code=400)
        warning.json.return_value = {
            "code": 400.16,
            "details": {"fields": ["label"]},
        }
        error = CollectionError("structure changed")
        error.__cause__ = requests.HTTPError(response=warning)
        attachments = Mock()
        attachments.json.return_value = []
        request.side_effect = [Mock(), error, Mock(), attachments, Mock()]
        OdkProvider().deploy(
            Mock(project_id="1", form_id="form"), b"xls", force=True
        )
        retried = [
            call
            for call in request.call_args_list
            if call.args[0] == "POST" and call.args[1].endswith("/draft")
        ]
        self.assertEqual(retried[-1].kwargs["params"], {"ignoreWarnings": "true"})


@override_settings(
    ODK_BASE_URL="http://central-service:8383",
    ODK_EMAIL="service@example.org",
    ODK_PASSWORD="secret",
)
class OdkRequestTests(SimpleTestCase):
    @patch("apps.integrations.odk.requests.request")
    def test_internal_requests_look_like_https_for_basic_auth(self, send):
        send.return_value = Mock(is_redirect=False)
        odk_request("POST", "projects/1/forms", headers={"Content-Type": "text/csv"})
        kwargs = send.call_args.kwargs
        # Central rejects Basic auth unless the request claims HTTPS. The call
        # stays private inside the Compose network.
        self.assertEqual(kwargs["headers"]["X-Forwarded-Proto"], "https")
        self.assertEqual(kwargs["headers"]["Content-Type"], "text/csv")
        self.assertEqual(kwargs["auth"], ("service@example.org", "secret"))
