from copy import deepcopy
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient
from apps.establishments.models import SourceLink
from apps.establishments.services import sync_registry_record, import_establishment
from apps.integrations.licensing import candidate, application_details, readable_address
from apps.integrations.registry import ADAPTERS
from apps.integrations.registry_sync import sync_all
from apps.integrations.services import source_detail, source_search


@override_settings(LICENSING_BASE_URL="http://licensing.test", LICENSING_REGISTRATION_API_KEY="key")
class SourceProfilesTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_superuser(username="profile-manager", password="password")
        self.client = APIClient(); self.client.force_authenticate(self.actor)
        self.raw = {"application_id": "P-1", "name": "Pharmacy", "address": {"province": {"name_en": "Kabul"}, "address": {"land_mark": "Market", "house_number": "1"}},
            "survey_id": "10", "archive_id": "20", "survey": {"id": 10, "name": "Survey pharmacy", "grade": "A"}, "archive": {"id": 20, "name": "Archive pharmacy", "pharmacy_location": [{"village": "Village"}]},
            "technical_staff": [{"first_name_en": "Staff", "passport_number": "secret", "e_nid_number": "secret"}],
            "license_attachment": {"file": "https://licensing.test/media/license.pdf"}}

    def imported(self):
        record = candidate("pharmacy", self.raw)
        sync_registry_record(self.actor, "licensing", "pharmacy", record)
        return SourceLink.objects.get(source="licensing").establishment

    def test_import_already_connected_and_search_works(self):
        class Adapter:
            def search(self, *args):
                return {"results": [], "count": 0}
        with patch.dict(ADAPTERS, {"licensing": Adapter()}):
            self.assertEqual(source_search(self.actor, "licensing", "pharmacy")["count"], 0)
        obj = self.imported()
        with patch("apps.integrations.services.source_record") as fetch:
            same = import_establishment(self.actor, "licensing", "pharmacy:P-1", "pharmacy")
        fetch.assert_not_called()
        self.assertEqual(same.pk, obj.pk)
        self.assertEqual(obj.source_links.get(is_primary=True).source, "licensing")

    def test_catalog_has_one_licensing_source(self):
        result = self.client.get("/api/v1/registry/")
        codes = [item["code"] for item in result.data["systems"]]
        self.assertIn("licensing", codes)
        self.assertNotIn("registration", codes)

    def test_auto_mappings_backfill_even_unchanged_identity(self):
        raw = deepcopy(self.raw);raw.pop("survey_id");raw.pop("survey");raw.pop("archive_id");raw.pop("archive")
        sync_registry_record(self.actor, "licensing", "pharmacy", candidate("pharmacy", raw))
        self.assertEqual(sync_registry_record(self.actor, "licensing", "pharmacy", candidate("pharmacy", self.raw)), "unchanged")
        obj = SourceLink.objects.get(source="licensing").establishment
        self.assertEqual(obj.source_links.count(), 3)
        self.assertEqual(obj.source_links.get(source="archive").external_id, "20")
        self.assertEqual(obj.source_links.get(source="survey").derived_from, "licensing")
        sync_registry_record(self.actor, "licensing", "pharmacy", candidate("pharmacy", self.raw))
        self.assertEqual(obj.source_links.count(), 3)

    def test_auto_mapping_changes_and_clears_but_preserves_manual(self):
        obj = self.imported()
        self.raw["survey_id"] = "11"
        sync_registry_record(self.actor, "licensing", "pharmacy", candidate("pharmacy", self.raw))
        self.assertEqual(obj.source_links.get(source="survey").external_id, "11")
        self.raw["survey_id"] = None;self.raw["survey"] = None
        sync_registry_record(self.actor, "licensing", "pharmacy", candidate("pharmacy", self.raw))
        self.assertFalse(obj.source_links.filter(source="survey").exists())
        SourceLink.objects.create(establishment=obj, source="survey", external_id="manual", linked_by=self.actor)
        self.raw["survey_id"] = "12"
        with self.assertRaises(ValidationError):
            sync_registry_record(self.actor, "licensing", "pharmacy", candidate("pharmacy", self.raw))
        self.assertEqual(obj.source_links.get(source="survey").external_id, "manual")

    @patch("apps.integrations.registry.LicensingAdapter.get_application")
    def test_source_sections_load_current_nested_profiles(self, get):
        obj = self.imported(); get.return_value = self.raw
        for source in ["licensing", "archive", "survey"]:
            result = source_detail(self.actor, obj.pk, source)
            self.assertTrue(result["sections"])
            self.assertNotIn("secret", str(result))
            if source != "licensing":
                self.assertEqual(result["via"], "licensing")
        self.assertIn("Market", obj.address)
        self.assertNotIn("{", obj.address)

    @patch("apps.integrations.registry.LicensingAdapter.get_application")
    def test_changed_reference_never_displays_wrong_profile(self, get):
        obj = self.imported(); changed = deepcopy(self.raw); changed["archive_id"]="wrong"
        get.return_value=changed
        with self.assertRaises(ValidationError):source_detail(self.actor,obj.pk,"archive")

    def test_null_province_import_and_nested_business_details(self):
        self.raw["address"]["province"] = None
        obj = self.imported()
        self.assertIsNone(obj.province)
        self.assertEqual(readable_address(self.raw["address"]["address"]), "Market · 1")
        details = application_details("pharmacy",self.raw)
        self.assertIn("Staff", str(details))
        self.assertIn("license.pdf",str(details))
        self.assertNotIn("secret",str(details))

    def test_complete_pass_visits_later_pages(self):
        from apps.establishments.models import EstablishmentType,RegistrySyncCursor
        EstablishmentType.objects.exclude(pk="pharmacy").update(is_active=False)
        class Adapter:
            def list_page(adapter,kind,page,page_size):
                return {"results":[{"application_id":f"P-{page}"}],"next":"more" if page==1 else None}
            def identity(adapter,kind,external_id):
                return {"id":external_id,"name":external_id,"details":{"province":"Kabul"},"is_demo":False}
        with patch.dict(ADAPTERS,{"licensing":Adapter()}):
            result=sync_all(self.actor,page_size=1)
        self.assertEqual(result["created"],2)
        self.assertEqual(RegistrySyncCursor.objects.get().next_page,1)

    @patch("apps.integrations.registry.LicensingAdapter.get_application")
    def test_focused_profile_excludes_identity_metadata_for_all_readers(self, get):
        from django.contrib.auth.models import Permission
        obj = self.imported();get.return_value = self.raw
        reader = get_user_model().objects.create_user(username="profile-reader")
        reader.user_permissions.set(Permission.objects.filter(codename__in=["view_establishment", "view_sourcelink"]))
        self.assertNotIn("secret", str(source_detail(reader, obj.pk, "licensing")))
        self.assertNotIn("secret", str(source_detail(self.actor, obj.pk, "licensing")))
        self.assertNotIn("secret", str(source_detail(self.actor, obj.pk, "licensing", include_sensitive=False)))

    def test_profile_shows_useful_fields_without_database_metadata(self):
        raw = deepcopy(self.raw)
        raw["address"].update({"id": 413, "district": {"id": 431, "province": {"id": 1, "name_en": "Kabul"}, "name_fa": "۱۱", "name_en": "11"}, "latitude": "34.5", "longitude": "69.1", "long_lat": "SRID=4326;POINT (69.1 34.5)"})
        raw["applicant"] = {"id": 1070, "first_name_fa": "نام", "last_name_fa": "مالک", "first_name_en": "Owner", "last_name_en": "Name", "father_name_fa": "پدر", "phone_number": "0700000000", "email": "test@example.test", "tin_number": "hidden-tax", "grand_father_name": "hidden-ancestor", "nid_attachment": {"file": "hidden-document"}, "address": {"id": 1070}}
        raw["finance_response_amount"] = "hidden-finance"
        raw["created_by"] = 12345
        result = application_details("pharmacy", raw, include_sensitive=True)
        location = next(section for section in result["sections"] if section["title"] == "Location")
        district = next(field["value"] for field in location["fields"] if field["label"] == "District")
        self.assertEqual(district, {"name_fa": "۱۱", "name_en": "11"})
        self.assertEqual(location["location"], {"latitude": 34.5, "longitude": 69.1})
        self.assertTrue(
            {field["label"] for field in location["fields"]}
            <= {
                "Country", "Province", "District", "Address", "Neighborhood", "Village",
                "Landmark", "Street", "House number", "Floor", "Market", "Area",
            }
        )
        text = str(result)
        for unwanted in ["hidden-tax", "hidden-ancestor", "hidden-document", "hidden-finance", "SRID=", "12345", "'id': 413", "'id': 431"]:
            self.assertNotIn(unwanted, text)
        self.assertIn("0700000000", text)
        self.assertIn("Owner Name", text)

    def test_location_coordinates_are_validated_and_country_is_named(self):
        from apps.integrations.licensing import _location_section
        for latitude, longitude in [(None, 69), ("nan", 69), (91, 69), (34, 181), ("bad", 69)]:
            section = _location_section({"latitude": latitude, "longitude": longitude})
            self.assertNotIn("location", section)
        section = _location_section({"country": {"id": 1, "code": "af", "name_en": "Afghanistan"}, "latitude": 0, "longitude": 0})
        self.assertEqual(section["fields"], [{"label": "Country", "value": {"name_en": "Afghanistan"}}])
        self.assertEqual(section["location"], {"latitude": 0.0, "longitude": 0.0})
