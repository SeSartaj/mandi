from django.contrib.auth import get_user_model
from unittest.mock import patch
from io import StringIO
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from apps.establishments.models import Establishment, SourceLink
from apps.establishments.services import sync_registry_record
from apps.integrations.licensing import candidate, application_details


class EstablishmentMapTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_superuser(username="map-manager", password="test")
        self.client = APIClient()
        self.client.force_authenticate(self.actor)

    def record(self, key, lat, lon):
        return candidate("pharmacy", {"application_id": key, "name": key,
            "address": {"latitude": lat, "longitude": lon,
                        "address": {"house_number": "12", "street": "Market Road", "not_precise_address": "Near hospital"}}})

    def test_coordinates_backfill_and_nearby_distance(self):
        for key, lat, lon in [("center", 34.5, 69.2), ("near", 34.501, 69.2), ("far", 35.5, 69.2)]:
            sync_registry_record(self.actor, "licensing", "pharmacy", self.record(key, lat, lon))
        link = SourceLink.objects.get(external_id="pharmacy:near")
        link.establishment.latitude = None
        link.establishment.longitude = None
        link.establishment.save()
        link.details = {"name": "near"}
        link.save()
        self.assertEqual(sync_registry_record(self.actor, "licensing", "pharmacy", self.record("near", 34.501, 69.2)), "updated")
        response = self.client.get("/api/v1/establishments/nearby/", {"latitude": 34.5, "longitude": 69.2})
        self.assertEqual(response.status_code, 200)
        link.establishment.refresh_from_db()
        self.assertEqual(link.establishment.latitude, 34.501)
        self.assertEqual([row["name"] for row in response.data["results"]], ["center", "near"])
        self.assertGreater(response.data["results"][1]["distance_km"], 0)
        self.assertEqual(self.client.get("/api/v1/establishments/nearby/", {"latitude": 91, "longitude": 0}).status_code, 400)

    def test_complete_address_is_preserved_without_coordinates(self):
        raw = {"application_id": "one", "name": "One", "address": {"address": {"house_number": "12", "street": "Market Road", "not_precise_address": "Near hospital"}}}
        location = next(section for section in application_details("pharmacy", raw)["sections"] if section["title"] == "Location")
        fields = {field["label"]: field["value"] for field in location["fields"]}
        self.assertEqual(fields["Address"], "Near hospital")
        self.assertEqual(fields["Street"], "Market Road")
        self.assertEqual(fields["House number"], "12")
        self.assertNotIn("location", location)

    def test_permission_required(self):
        self.client.force_authenticate(get_user_model().objects.create_user(username="map-reader"))
        self.assertEqual(self.client.get("/api/v1/establishments/nearby/", {"latitude": 34.5, "longitude": 69.2}).status_code, 403)

    def test_native_coordinates_are_stored_and_returned_without_source_links(self):
        response = self.client.post("/api/v1/establishments/", {"name": "Native", "kind": "pharmacy",
            "province": "Kabul", "latitude": 34.501, "longitude": 69.2}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["latitude"], 34.501)
        nearby = self.client.get("/api/v1/establishments/nearby/", {"latitude": 34.5, "longitude": 69.2})
        self.assertEqual([row["name"] for row in nearby.data["results"]], ["Native"])
        url = f"/api/v1/establishments/{response.data['id']}/"
        self.assertEqual(self.client.patch(url, {"latitude": 91}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"latitude": None}, format="json").status_code, 400)

    @override_settings(LICENSING_BASE_URL="http://licensing.test", LICENSING_REGISTRATION_API_KEY="key")
    @patch("apps.integrations.registry.LicensingAdapter.list_page")
    def test_backfill_existing_registry_records_without_opening_profiles(self, list_page):
        raw = {"application_id": "existing", "name": "Existing", "address": {"latitude": "34.5", "longitude": "69.2"}}
        record = candidate("pharmacy", raw)
        sync_registry_record(self.actor, "licensing", "pharmacy", record)
        Establishment.objects.update(latitude=None, longitude=None)
        list_page.return_value = {"results": [raw], "next": None}
        output = StringIO()
        call_command("backfill_establishment_locations", stdout=output)
        self.assertIn("Saved coordinates for 1", output.getvalue())
        self.assertEqual(Establishment.objects.get().latitude, 34.5)

    def test_coordinate_only_registry_changes_are_applied(self):
        sync_registry_record(self.actor, "licensing", "pharmacy", self.record("move", 34.5, 69.2))
        sync_registry_record(self.actor, "licensing", "pharmacy", self.record("move", 34.6, 69.3))
        obj = Establishment.objects.get()
        self.assertEqual((obj.latitude, obj.longitude), (34.6, 69.3))
