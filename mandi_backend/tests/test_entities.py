from io import BytesIO
from unittest.mock import Mock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings

from apps.establishments.models import Establishment, EstablishmentType
from apps.inspections.models import Checklist
from apps.inspections.services import deploy_checklist
from apps.integrations import entities
from apps.integrations.models import FormDeployment
from apps.integrations.providers import CollectionError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError


def workbook():
    from openpyxl import Workbook

    book = Workbook()
    survey = book.active
    survey.title = "survey"
    survey.append(["type", "name", "label"])
    survey.append(["integer", "score_total", "Score"])
    settings = book.create_sheet("settings")
    settings.append(["form_id", "form_title"])
    settings.append(["test", "Test"])
    output = BytesIO()
    book.save(output)
    return output.getvalue()


class EntityProjectionTests(SimpleTestCase):
    def test_projection_uses_licensing_details_and_stable_uuid(self):
        establishment = Establishment(
            name="Pharmacy",
            kind=EstablishmentType(code="pharmacy", name="Pharmacy"),
            address="Mandi address",
        )
        licensing = {
            "address": "Licensing address",
            "license_number": "LIC-1",
            "owner": "Owner",
            "technical_staff_count": 2,
            "activities": "Medicines",
        }
        payload = entities.establishment_entity(
            establishment, "11111111-1111-4111-8111-111111111111", licensing
        )
        self.assertEqual(payload["uuid"], "11111111-1111-4111-8111-111111111111")
        self.assertIn("Pharmacy", payload["label"])
        self.assertEqual(payload["data"]["address"], "Licensing address")
        self.assertEqual(payload["data"]["license_number"], "LIC-1")
        self.assertEqual(payload["data"]["technical_staff_count"], "2")
        self.assertEqual(payload["data"]["active"], "true")


class EntityBindingTests(TestCase):
    def setUp(self):
        self.establishment = Establishment.objects.create(
            name="Pharmacy", kind=EstablishmentType.objects.get(pk="pharmacy")
        )

    def test_uuid_is_stable_within_a_project_and_scoped_per_project(self):
        first = entities.entity_binding(self.establishment, 3)
        again = entities.entity_binding(self.establishment, 3)
        other = entities.entity_binding(self.establishment, 4)
        self.assertEqual(first.entity_uuid, again.entity_uuid)
        self.assertNotEqual(first.entity_uuid, other.entity_uuid)
        self.assertEqual(first.entity_uuid.version, 4)
        self.assertEqual(other.entity_uuid.version, 4)

    def test_submitted_entity_resolves_only_in_its_project(self):
        binding = entities.entity_binding(self.establishment, 3)
        self.assertEqual(
            entities.establishment_for_entity(3, str(binding.entity_uuid)),
            self.establishment,
        )
        self.assertEqual(
            entities.establishment_for_entity(3, f"uuid:{binding.entity_uuid}"),
            self.establishment,
        )
        self.assertIsNone(
            entities.establishment_for_entity(4, str(binding.entity_uuid))
        )
        self.assertIsNone(entities.establishment_for_entity(3, "not-a-uuid"))


class EnsureDatasetTests(SimpleTestCase):
    @patch("apps.integrations.entities.request")
    def test_missing_dataset_is_created_and_missing_properties_added(self, request):
        missing = CollectionError("missing")
        response = Mock(status_code=404)
        missing.__cause__ = requests.HTTPError(response=response)
        request.side_effect = [
            missing,
            Mock(json=Mock(return_value={"name": "establishments", "properties": []})),
            *[Mock(json=Mock(return_value={})) for _ in entities.ENTITY_PROPERTIES],
        ]
        entities.ensure_dataset(1, "establishments")
        self.assertEqual(request.call_args_list[1].args, ("POST", "projects/1/datasets"))
        self.assertEqual(
            request.call_args_list[1].kwargs,
            {"json": {"name": "establishments"}},
        )
        self.assertEqual(
            request.call_args_list[2].args,
            ("POST", "projects/1/datasets/establishments/properties"),
        )


@override_settings(ODK_ENTITY_LIST="establishments")
class EntitySyncTests(TestCase):
    def setUp(self):
        self.kind = EstablishmentType.objects.get(pk="pharmacy")
        self.establishment = Establishment.objects.create(
            name="Pharmacy", kind=self.kind
        )
        self.binding = entities.entity_binding(self.establishment, 1)

    @patch("apps.integrations.entities.create_entities")
    @patch("apps.integrations.entities.update_entity")
    @patch("apps.integrations.entities.download_entities")
    @patch("apps.integrations.entities.ensure_dataset")
    def test_creates_updates_and_keeps_central_only(
        self, ensure, download, update, create
    ):
        ensure.return_value = "establishments"
        download.return_value = {}
        create.return_value = 1
        counts = entities.sync_entities(project_id=1)
        self.assertEqual(counts["created"], 1)
        create.assert_called_once()

        create.reset_mock()
        download.return_value = {
            str(self.binding.entity_uuid): {
                "__id": str(self.binding.entity_uuid),
                "label": "old",
                **{name: "" for name in entities.ENTITY_PROPERTIES},
            },
            "central-only": {
                "__id": "central-only",
                "label": "Other",
                **{name: "" for name in entities.ENTITY_PROPERTIES},
            },
        }
        counts = entities.sync_entities(project_id=1)
        self.assertEqual(counts["updated"], 1)
        self.assertEqual(counts["central_only"], 1)
        update.assert_called_once()
        self.assertEqual(create.call_args.args[0], [])


@override_settings(
    COLLECTION_PROVIDER="odk",
    ODK_PROJECT_ID="1",
    ODK_ENTITY_LIST="establishments",
)
class EntityDeploymentTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="entity-admin", password="TestPassword-2026!"
        )
        self.checklist = Checklist.objects.create(
            code="entity-test",
            name="Entity test",
            xlsform=SimpleUploadedFile("entity.xlsx", workbook()),
        )
        self.addCleanup(self.checklist.xlsform.delete, save=False)

    @patch("apps.integrations.collection.sync_entities", return_value={"failed": 0})
    @patch("apps.integrations.collection.ensure_dataset", return_value="establishments")
    @patch("apps.integrations.collection.provider")
    def test_entity_mode_links_dataset_instead_of_csv(
        self, provider, ensure, sync_entities
    ):
        deploy_checklist(self.admin, self.checklist.pk)
        kwargs = provider.return_value.deploy.call_args.kwargs
        self.assertEqual(kwargs["dataset"], "establishments")
        ensure.assert_called_once()
        sync_entities.assert_called_once_with("1", "establishments")

    @patch("apps.integrations.collection.sync_entities", return_value={"failed": 1})
    @patch("apps.integrations.collection.ensure_dataset", return_value="establishments")
    @patch("apps.integrations.collection.provider")
    def test_entity_sync_failure_blocks_deployment(
        self, provider, ensure, sync_entities
    ):
        with self.assertRaises(ValidationError):
            deploy_checklist(self.admin, self.checklist.pk)
        provider.return_value.deploy.assert_not_called()
        deployment = FormDeployment.objects.get(checklist=self.checklist)
        self.assertEqual(deployment.status, "failed")
