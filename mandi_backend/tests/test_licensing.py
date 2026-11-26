from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import NotFound, ValidationError

from apps.integrations.licensing import candidate, get_application, list_applications, LicensingError


@override_settings(LICENSING_BASE_URL="http://licensing.test", LICENSING_REGISTRATION_API_KEY="test-key", LICENSING_TIMEOUT=3)
class LicensingTests(TestCase):
    def response(self, payload, status=200):
        response = Mock(status_code=status)
        response.json.return_value = payload
        return response

    @patch("apps.integrations.licensing.requests.get")
    def test_all_category_paths_and_headers(self, get):
        for category in ("company", "factory", "pharmacy", "wholesale"):
            get.return_value = self.response({"results": [], "count": 0, "next": None})
            list_applications(category, {"search": "name", "page": 2})
            self.assertEqual(get.call_args.args[0], f"http://licensing.test/api/applications/{category}/registration/list/")
            self.assertEqual(get.call_args.kwargs["headers"]["X-API-KEY"], "test-key")
            self.assertEqual(get.call_args.kwargs["params"]["page"], 2)
            self.assertFalse(get.call_args.kwargs["allow_redirects"])
            get.return_value.close.assert_called_once()

    @patch("apps.integrations.licensing.requests.get")
    def test_plain_array_and_detail_id_encoding(self, get):
        get.return_value = self.response([])
        self.assertEqual(list_applications("company", {"paginate": "false"}), [])
        get.return_value = self.response({"application_id": "ID /?#", "name": "Title"})
        get_application("pharmacy", "ID /?#")
        self.assertTrue(get.call_args.args[0].endswith("/registration/ID%20%2F%3F%23/"))

    def test_null_fields_and_minimal_projection(self):
        record = {"application_id": "same", "name": "Name", "address": None, "applicant": {"passport": "private"}, "technical_staff": [{"id_number": "private"}]}
        company = candidate("company", record)
        pharmacy = candidate("pharmacy", record)
        self.assertNotEqual(company["id"], pharmacy["id"])
        self.assertNotIn("applicant", company["details"])
        self.assertNotIn("technical_staff", company["details"])
        self.assertEqual(company["details"]["province"], "")

    @patch("apps.integrations.licensing.requests.get")
    def test_upstream_failures_are_sanitized(self, get):
        for status, error in [(400, ValidationError), (401, LicensingError), (403, LicensingError), (404, NotFound), (500, LicensingError), (302, LicensingError)]:
            get.return_value = self.response({"secret": "private"}, status)
            with self.assertRaises(error):
                get_application("factory", "ID")
        get.side_effect = requests.Timeout("private upstream data")
        with self.assertRaises(LicensingError) as error:
            list_applications("factory")
        self.assertNotIn("private", str(error.exception))

    @patch("apps.integrations.licensing.requests.get")
    def test_bad_category_does_not_make_request(self, get):
        with self.assertRaises(ValidationError):
            list_applications("anything")
        get.assert_not_called()

    @patch("apps.integrations.licensing.requests.get")
    def test_live_picker_and_detail_lookup(self, get):
        from types import SimpleNamespace
        from apps.integrations.services import source_search, source_record
        actor = SimpleNamespace(is_authenticated=True, is_active=True, has_perm=lambda p: True)
        record = {"application_id": "APP-1", "name": "Business", "address": {"province": None}}
        get.return_value = self.response({"results": [record], "count": 21, "next": "http://licensing.test/next"})
        result = source_search(actor, "licensing", "importer", page=1)
        self.assertEqual(result["count"], 21)
        self.assertTrue(result["has_next"])
        self.assertEqual(result["results"][0]["id"], "company:APP-1")
        get.return_value = self.response(record)
        linked = source_record(actor, "licensing", "company:APP-1", "importer")
        self.assertEqual(linked["details"]["application_id"], "APP-1")
        self.assertTrue(get.call_args.args[0].endswith("/company/registration/APP-1/"))
        with self.assertRaises(ValidationError):
            source_record(actor, "licensing", "pharmacy:APP-1", "importer")


class LicensingDetailProjectionTests(SimpleTestCase):
    def test_details_include_business_location_contacts_but_not_identity_documents(self):
        from apps.integrations.licensing import application_details
        result = application_details("factory", {
            "application_id": "F-1", "name": "Factory", "application_status": "completed",
            "address": {"province": {"name_en": "Kabul"}, "district": None, "address": "Street"},
            "applicant": {"first_name_en": "Name", "phone_number": "0700000000", "passport": "secret"},
            "co_owner": None, "technical_staff": [{"national_id": "secret"}],
            "license_attachment": {"file": "private-document"}, "issue_date": "2026-01-01",
        })
        self.assertEqual(result["application_id"], "F-1")
        text = str(result)
        self.assertIn("Kabul", text)
        self.assertIn("0700000000", text)
        self.assertNotIn("secret", text)
        self.assertIn("private-document", text)

    def test_optional_sections_are_omitted(self):
        from apps.integrations.licensing import application_details
        result = application_details("pharmacy", {"application_id": "P-1", "address": None, "applicant": None})
        self.assertEqual(len(result["sections"]), 1)

    def test_all_attachment_fields_are_projected(self):
        from apps.integrations.licensing import application_details
        result = application_details("pharmacy", {
            "application_id": "P-1",
            "request_letter_attachment": {"file": "https://licensing.test/request.pdf"},
            "stamp_attachment": {"file": "https://licensing.test/stamp.png"},
            "land_ownership_attachment": {"file": "https://licensing.test/land.pdf"},
            "finance_response_attachment": {"file": "https://licensing.test/finance.pdf"},
            "extra_attachments": [
                {"file": "https://licensing.test/extra-1.pdf"},
                {"file": "https://licensing.test/extra-2.pdf"},
            ],
        })
        attachments = next(
            section for section in result["sections"] if section["title"] == "Attachments"
        )
        values = {field["label"]: field["value"] for field in attachments["fields"]}
        self.assertEqual(values["Request letter"], "https://licensing.test/request.pdf")
        self.assertEqual(values["Stamp"], "https://licensing.test/stamp.png")
        self.assertEqual(values["Land ownership"], "https://licensing.test/land.pdf")
        self.assertEqual(values["Finance response"], "https://licensing.test/finance.pdf")
        self.assertEqual(values["Extra attachments"], [
            "https://licensing.test/extra-1.pdf",
            "https://licensing.test/extra-2.pdf",
        ])

    def test_profile_includes_form_relevant_identity_license_and_premises(self):
        from apps.integrations.licensing import application_details
        result = application_details("factory", {
            "application_id": "F-1",
            "name": "فابریکه",
            "name_en": "Factory",
            "application_step": "license_issuance",
            "register_type": "new",
            "service_status": "active",
            "old_license_number": "OLD-1",
            "old_license_issue_date": "2020-01-01",
            "company_branches": [{"name_en": "Branch"}],
            "warehouses": [{"name_en": "Store"}],
            "address": {"province": {"name_en": "Kabul"}, "total_area": "500"},
        })
        fields = {
            field["label"]: field["value"]
            for section in result["sections"]
            for field in section["fields"]
        }
        for label in (
            "English name",
            "Application step",
            "Register type",
            "Service status",
            "Old license number",
            "Old license issue date",
            "Branches",
            "Warehouses",
        ):
            self.assertIn(label, fields)
        self.assertEqual(fields["Area"], "500")
        self.assertNotIn("Inspection date", fields)
