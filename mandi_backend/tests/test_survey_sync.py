from copy import deepcopy
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.establishments.models import Establishment, EstablishmentType, RegistrySyncCursor, SourceLink
from apps.establishments.services import save_establishment
from apps.integrations import survey
from apps.integrations.management.commands.sync_registries import Command
from apps.integrations.registry import ADAPTERS
from apps.integrations.registry_sync import sync_batch

SAMPLE = {
    "application_id": 123,
    "name": "Example Pharmacy",
    "address": {
        "province": "Herat",
        "province_name": {"id": 1, "name": "Herat"},
        "district_name": {"id": 10, "name": "Injil"},
        "village": "Example Village",
        "exact_address": "Example Road",
        "latitude": "34.35000000",
        "longitude": "62.20000000",
        "point": {"type": "Point", "coordinates": [62.2, 34.35]},
    },
    "applicant": {"first_name": "Example", "last_name": "Owner", "phone_number": "0700000000"},
}


@override_settings(
    SURVEY_BASE_URL="http://survey.test:9100",
    SURVEY_REGISTRATION_API_KEY="survey-test-key",
    SURVEY_TIMEOUT=3,
)
class SurveyClientTests(TestCase):
    def test_candidate_maps_identity_location_and_applicant(self):
        projection = survey.candidate("pharmacy", SAMPLE)
        self.assertEqual(projection["id"], "123")
        details = projection["details"]
        self.assertEqual(details["name"], "Example Pharmacy")
        self.assertEqual(details["province"], "Herat")
        self.assertEqual(details["district"], "Injil")
        self.assertEqual(details["address"], "Example Village · Example Road")
        self.assertEqual(details["owner"], "Example Owner")
        self.assertEqual(details["owner_phone"], "0700000000")
        self.assertEqual(details["location"], {"latitude": 34.35, "longitude": 62.2})

    def test_point_is_used_when_decimal_fields_are_missing(self):
        raw = deepcopy(SAMPLE)
        raw["address"].pop("latitude")
        raw["address"].pop("longitude")
        details = survey.candidate("pharmacy", raw)["details"]
        self.assertEqual(details["location"], {"latitude": 34.35, "longitude": 62.2})

    def test_empty_address_and_applicant_are_safe(self):
        raw = {"application_id": 7, "name": "No address", "address": None, "applicant": None}
        projection = survey.candidate("wholesale", raw)
        self.assertEqual(projection["id"], "7")
        self.assertEqual(projection["details"]["province"], "")
        self.assertNotIn("location", projection["details"])
        self.assertEqual(projection["details"]["owner"], "")

    @patch("apps.integrations.survey.requests.get")
    def test_list_response_has_no_next_link_and_page_is_derived_from_count(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {"count": 3, "results": [SAMPLE]}
        adapter = ADAPTERS["survey"]
        first = adapter.list_page("pharmacy", 1, 2)
        self.assertEqual(first["next"], "more")
        get.return_value.json.return_value = {"count": 3, "results": [SAMPLE]}
        second = adapter.list_page("pharmacy", 2, 2)
        self.assertIsNone(second["next"])
        self.assertEqual(get.call_args.args[0], "http://survey.test:9100/api/applications/pharmacy/registration/list/")
        self.assertEqual(get.call_args.kwargs["headers"]["X-API-KEY"], "survey-test-key")
        self.assertEqual(get.call_args.kwargs["params"], {"page": 2, "page_size": 2})
        self.assertFalse(get.call_args.kwargs["allow_redirects"])

    @patch("apps.integrations.survey.requests.get")
    def test_search_passes_list_filters(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {"count": 1, "results": [SAMPLE]}
        ADAPTERS["survey"].search(
            "pharmacy", "", 1, 15,
            filters={"province": "Herat", "status": "ongoing", "grade": "1"},
        )
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["province"], "Herat")
        self.assertEqual(params["application_status"], "ongoing")
        self.assertEqual(params["grade"], "1")

    @patch("apps.integrations.survey.requests.get")
    def test_search_projects_candidates(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {"count": 1, "results": [SAMPLE]}
        result = ADAPTERS["survey"].search("wholesaler", "example", 1, 15)
        self.assertEqual(result["count"], 1)
        self.assertFalse(result["has_next"])
        self.assertEqual(result["results"][0]["id"], "123")
        self.assertIn("search", get.call_args.kwargs["params"])
        self.assertEqual(get.call_args.args[0], "http://survey.test:9100/api/applications/wholesale/registration/list/")

    @patch("apps.integrations.survey.requests.get")
    def test_credentials_and_unexpected_responses_are_not_leaked(self, get):
        get.return_value = Mock(status_code=403)
        with self.assertRaisesMessage(survey.SurveyError, "rejected the server credentials") as raised:
            survey.list_applications("pharmacy")
        self.assertNotIn("survey-test-key", str(raised.exception))

    def test_missing_attachments_get_a_notice(self):
        detail = survey.application_details(
            "pharmacy", {"application_id": 123, "name": "No files"}
        )
        self.assertIn("No registration attachment", detail["notice"])

    def test_unsupported_kind_is_rejected(self):
        with self.assertRaises(ValidationError):
            ADAPTERS["survey"].category("importer")

    def test_full_detail_sections_and_sensitive_gating(self):
        full = {
            **SAMPLE,
            "entity_type": "pharmacy",
            "application_status": "completed",
            "application_step": 8,
            "is_official": True,
            "grade": "1",
            "grade_type": "pharmacy",
            "tin_number": "TIN-1",
            "opening_letter_number": "OL-1",
            "opening_letter_date": "2025-01-01",
            "years_of_activity": 3,
            "owner": {
                "first_name": "Example",
                "last_name": "Owner",
                "father_name": "Father",
                "phone_number": "0700000000",
                "date_of_birth": "1980-01-01",
                "e_nid_number": "NID-123",
                "nid_attachment": "http://survey.test/media/owner-nid.pdf",
                "education_level": "bachelor_degree",
                "current_address": SAMPLE["address"],
            },
            "technical_staff": [
                {
                    "first_name": "Tech",
                    "last_name": "One",
                    "phone_number": "0777000000",
                    "technical_card_attachment": "http://survey.test/media/staff-card.pdf",
                }
            ],
            "sharia_lawyer": {
                "first_name": "Law",
                "last_name": "Yer",
                "sharia_lawyer_letter": "http://survey.test/media/lawyer-letter.pdf",
            },
            "surveyor": [{"first_name": "Surv", "last_name": "Eyer", "nid": "NID-1"}],
            "opening_letter": "http://survey.test/media/opening.pdf",
        }
        public = survey.application_details("pharmacy", full, include_sensitive=False)
        titles = [section["title"] for section in public["sections"]]
        self.assertEqual(titles, [
            "Establishment", "Location", "Owner", "Technical staff",
            "Sharia lawyer", "Surveyors", "Attachments",
        ])
        owner = next(section for section in public["sections"] if section["title"] == "Owner")
        owner_fields = {field["label"]: field["value"] for field in owner["fields"]}
        self.assertEqual(owner_fields["Full name"], "Example Owner")
        self.assertNotIn("Electronic NID", owner_fields)
        self.assertNotIn("Date of birth", owner_fields)
        attachments = next(
            section for section in public["sections"] if section["title"] == "Attachments"
        )
        attachment_fields = {
            field["label"]: field["value"] for field in attachments["fields"]
        }
        self.assertIn("Opening letter", attachment_fields)
        self.assertNotIn("Owner — NID document", attachment_fields)
        sensitive = survey.application_details("pharmacy", full, include_sensitive=True)
        owner = next(section for section in sensitive["sections"] if section["title"] == "Owner")
        owner_fields = {field["label"]: field["value"] for field in owner["fields"]}
        self.assertEqual(owner_fields["Electronic NID"], "NID-123")
        self.assertEqual(owner_fields["Date of birth"], "1980-01-01")
        attachments = next(
            section for section in sensitive["sections"] if section["title"] == "Attachments"
        )
        attachment_fields = {
            field["label"]: field["value"] for field in attachments["fields"]
        }
        self.assertEqual(
            attachment_fields["Owner — NID document"],
            "http://survey.test/media/owner-nid.pdf",
        )
        self.assertEqual(
            attachment_fields["Staff 1 (Tech One) — Technical card document"],
            "http://survey.test/media/staff-card.pdf",
        )
        self.assertEqual(
            attachment_fields["Sharia lawyer — Sharia lawyer document"],
            "http://survey.test/media/lawyer-letter.pdf",
        )

    def test_person_only_attachments_explain_permission_gate(self):
        record = {
            "application_id": 55,
            "name": "Person files only",
            "owner": {
                "first_name": "Example",
                "last_name": "Owner",
                "nid_attachment": "http://survey.test/media/owner-nid.pdf",
            },
        }
        public = survey.application_details("pharmacy", record, include_sensitive=False)
        self.assertEqual(
            public["notice"],
            "Identity or professional documents are stored in Survey but require sensitive-source permission.",
        )
        self.assertNotIn(
            "Attachments", [section["title"] for section in public["sections"]]
        )
        sensitive = survey.application_details("pharmacy", record, include_sensitive=True)
        attachments = next(
            section for section in sensitive["sections"] if section["title"] == "Attachments"
        )
        self.assertEqual(
            {field["label"]: field["value"] for field in attachments["fields"]}[
                "Owner — NID document"
            ],
            "http://survey.test/media/owner-nid.pdf",
        )



@override_settings(
    SURVEY_BASE_URL="http://survey.test:9100",
    SURVEY_REGISTRATION_API_KEY="survey-test-key",
)
class SurveySyncTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_superuser(
            username="survey-manager", password="test-password"
        )
        EstablishmentType.objects.exclude(pk__in=["pharmacy", "wholesaler"]).update(is_active=False)
        self.record = survey.candidate("pharmacy", SAMPLE)
        self.list_page = patch.object(
            ADAPTERS["survey"],
            "list_page",
            return_value={"results": [SAMPLE], "next": None},
        )
        self.identity = patch.object(
            ADAPTERS["survey"], "identity", side_effect=lambda kind, external_id: deepcopy(self.record)
        )
        self.list_page.start()
        self.identity.start()
        self.addCleanup(self.list_page.stop)
        self.addCleanup(self.identity.stop)

    def test_auto_create_then_update_without_duplicates(self):
        self.assertEqual(sync_batch(self.actor, "survey", page_size=50, selected_kinds=["pharmacy"])["created"], 1)
        obj = Establishment.objects.get()
        self.assertEqual(obj.kind_id, "pharmacy")
        self.assertEqual(obj.primary_source, "survey")
        self.assertEqual(obj.province.name, "Herat")
        self.assertEqual(obj.district.name, "Injil")
        self.assertEqual(obj.latitude, 34.35)
        self.record["name"] = "Updated pharmacy"
        self.record["details"]["name"] = "Updated pharmacy"
        self.record["details"]["province"] = "Kabul"
        self.record["details"]["location"] = {"latitude": 34.5, "longitude": 69.2}
        self.assertEqual(sync_batch(self.actor, "survey", selected_kinds=["pharmacy"])["updated"], 1)
        obj.refresh_from_db()
        self.assertEqual(obj.name, "Updated pharmacy")
        self.assertEqual(obj.province.name, "Kabul")
        self.assertEqual(Establishment.objects.count(), 1)
        self.assertEqual(sync_batch(self.actor, "survey", selected_kinds=["pharmacy"])["unchanged"], 1)

    def test_only_pharmacy_and_wholesaler_cursors_are_created(self):
        sync_batch(self.actor, "survey")
        self.assertEqual(
            set(RegistrySyncCursor.objects.filter(source_id="survey").values_list("kind_id", flat=True)),
            {"pharmacy", "wholesaler"},
        )

    def test_existing_licensing_survey_reference_is_not_duplicated(self):
        obj = save_establishment(
            self.actor, {"name": "Licensing pharmacy", "kind": "pharmacy", "province": "Herat"}
        )
        SourceLink.objects.create(
            establishment=obj, source="licensing", external_id="P-1",
            details={"survey_id": "123"}, is_primary=True, linked_by=self.actor,
        )
        SourceLink.objects.create(
            establishment=obj, source="survey", external_id="123",
            derived_from="licensing", linked_by=self.actor,
        )
        result = sync_batch(self.actor, "survey", selected_kinds=["pharmacy"])
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(Establishment.objects.count(), 1)
        self.assertEqual(obj.source_links.get(source="survey").external_id, "123")

    def test_survey_id_connected_to_another_type_is_skipped_as_duplicate(self):
        obj = save_establishment(
            self.actor, {"name": "Licensing pharmacy", "kind": "pharmacy", "province": "Herat"}
        )
        SourceLink.objects.create(
            establishment=obj, source="survey", external_id="123",
            derived_from="licensing", linked_by=self.actor,
        )
        result = sync_batch(self.actor, "survey", selected_kinds=["wholesaler"])
        self.assertEqual(result["skipped"], 1)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(Establishment.objects.count(), 1)
        self.assertFalse(Establishment.objects.filter(kind_id="wholesaler").exists())

    def test_full_pass_restarts_pagination(self):
        from apps.integrations.registry_sync import sync_all
        EstablishmentType.objects.exclude(pk="pharmacy").update(is_active=False)
        pages = {
            1: {"results": [SAMPLE], "next": "more"},
            2: {"results": [], "next": None},
        }
        with patch.object(ADAPTERS["survey"], "list_page", side_effect=lambda kind, page, size: pages[page]):
            sync_all(self.actor, "survey", page_size=1)
        self.assertTrue(
            all(state.next_page == 1 for state in RegistrySyncCursor.objects.filter(source_id="survey"))
        )


@override_settings(
    LICENSING_BASE_URL="http://licensing.test",
    LICENSING_REGISTRATION_API_KEY="key",
    SURVEY_BASE_URL="http://survey.test:9100",
    SURVEY_REGISTRATION_API_KEY="survey-test-key",
    SURVEY_SYNC_ENABLED=True,
)
class SurveySystemsEndpointTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_superuser(
            username="survey-viewer", email="survey@example.test", password="Testing-2026!"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def test_survey_is_directly_syncable_and_searchable(self):
        response = self.client.get("/api/v1/registry/systems/")
        self.assertEqual(response.status_code, 200)
        survey_row = next(row for row in response.data["systems"] if row["code"] == "survey")
        self.assertTrue(survey_row["configured"])
        self.assertTrue(survey_row["syncable"])
        self.assertTrue(survey_row["can_sync"])
        catalog = self.client.get("/api/v1/registry/")
        survey_source = next(row for row in catalog.data["systems"] if row["code"] == "survey")
        self.assertTrue(survey_source["searchable"])

    @override_settings(SURVEY_BASE_URL="", SURVEY_REGISTRATION_API_KEY="")
    def test_unconfigured_survey_is_rejected(self):
        response = self.client.post("/api/v1/registry/systems/survey/sync/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_worker_includes_survey_when_configured(self):
        self.assertEqual(Command._configured_sources(None), ["licensing", "survey"])
