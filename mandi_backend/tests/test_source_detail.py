from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.test import APIClient

from apps.establishments.models import Establishment, SourceLink


class SourceDetailTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="source-reader")
        self.user.user_permissions.set(Permission.objects.filter(codename__in=["view_establishment", "view_sourcelink"]))
        self.establishment = Establishment.objects.create(name="Local", kind="factory", province="Kabul")
        SourceLink.objects.create(establishment=self.establishment, source="licensing", external_id="factory:F-1", linked_by=self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.url = f"/api/v1/establishments/{self.establishment.pk}/sources/licensing/"

    @patch("apps.integrations.licensing.get_application")
    def test_linked_details_are_loaded_live(self, get):
        get.return_value = {"application_id": "F-1", "name": "Current title", "application_status": "completed"}
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], "Current title")
        get.assert_called_once_with("factory", "F-1")

    @patch("apps.integrations.licensing.get_application")
    def test_permissions_checked_before_upstream_request(self, get):
        self.user.user_permissions.clear()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        get.assert_not_called()

    def test_missing_link_returns_not_found(self):
        self.establishment.source_links.all().delete()
        self.assertEqual(self.client.get(self.url).status_code, 404)
