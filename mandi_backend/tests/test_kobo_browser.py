from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from rest_framework.test import APIClient

from apps.establishments.services import save_establishment
from apps.inspections.models import Checklist
from apps.integrations.models import KoboSubmission
from apps.integrations.services import sync_kobo_submissions


class SubmissionBrowserTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reviewer", password="TestPassword-2026!"
        )
        self.user.user_permissions.set(Permission.objects.all())
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.pharmacy = save_establishment(
            self.user,
            {"name": "Kabul Pharmacy", "kind": "pharmacy", "province": "Kabul"},
        )
        self.factory = save_establishment(
            self.user, {"name": "Kabul Factory", "kind": "factory", "province": "Kabul"}
        )
        self.checklist = Checklist.objects.create(
            code="pharmacy",
            version="1",
            name="Pharmacy",
            establishment_kind="pharmacy",
            kobo_asset_uid="asset-1",
        )
        self.other = Checklist.objects.create(
            code="factory", version="1", name="Factory", establishment_kind="factory"
        )
        self.submission = KoboSubmission.objects.create(
            asset_uid="asset-1",
            submission_id="7",
            establishment=self.pharmacy,
            checklist=self.checklist,
            submitted_at="2026-11-08T05:21:11Z",
            data={
                "_id": 7,
                "establishment_id": str(self.pharmacy.pk),
                "_attachments": [
                    {
                        "filename": "reviewer/signature.jpg",
                        "mimetype": "image/jpeg",
                        "download_url": "http://kf.kobo.local/api/v2/assets/asset-1/data/7/attachment/",
                    }
                ],
                "sec2/q2_1": "1",
                "scoring/score_license": "1",
                "scoring/max_license": "2",
                "scoring/pct_license": "50",
                "scoring/title_license": "۲. جواز فعالیت",
                "scoring/result_pct": "50",
                "signature": "signature.jpg",
            },
            form_schema={
                "labels": {"q2_1": "جواز موجود است؟", "signature": "امضاء"},
                "choices": {"q2_1": {"1": "۱ – تکمیل"}},
                "types": {"q2_1": "select_one", "signature": "image"},
                "paths": {"q2_1": "sec2/q2_1", "signature": "sec9/signature"},
                "groups": {"sec2": "۲. جواز فعالیت", "sec9": "۹. امضاء"},
            },
        )
        KoboSubmission.objects.create(
            asset_uid="asset-2",
            submission_id="8",
            establishment=self.factory,
            checklist=self.other,
            submitted_at="2026-11-01T05:00:00Z",
            data={"_id": 8, "establishment_id": str(self.factory.pk)},
        )

    def test_checklist_detail_exposes_submission_count(self):
        response = self.client.get(f"/api/v1/checklists/{self.checklist.pk}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["submission_count"], 1)

    def test_checklist_submissions_are_scoped_to_the_checklist(self):
        response = self.client.get(
            f"/api/v1/checklists/{self.checklist.pk}/submissions/"
        )

        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["establishment_name"], "Kabul Pharmacy")

    def test_search_and_date_filters(self):
        url = f"/api/v1/checklists/{self.checklist.pk}/submissions/"

        self.assertEqual(self.client.get(url, {"search": "Factory"}).json()["count"], 0)
        self.assertEqual(
            self.client.get(url, {"search": "Kabul Phar"}).json()["count"], 1
        )
        self.assertEqual(self.client.get(url, {"search": "7"}).json()["count"], 1)
        self.assertEqual(
            self.client.get(url, {"date_from": "2026-11-08"}).json()["count"], 1
        )
        self.assertEqual(
            self.client.get(url, {"date_to": "2026-11-07"}).json()["count"], 0
        )

    def test_invalid_date_range_is_rejected(self):
        response = self.client.get(
            f"/api/v1/checklists/{self.checklist.pk}/submissions/",
            {"date_from": "2026-11-08", "date_to": "2026-11-01"},
        )

        self.assertEqual(response.status_code, 400)

    def test_submission_detail_includes_grouped_answers_and_media(self):
        response = self.client.get(f"/api/v1/kobo-submissions/{self.submission.pk}/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["establishment_name"], "Kabul Pharmacy")
        self.assertEqual(payload["scores"]["percent"], 50.0)
        answers = {answer["name"]: answer for answer in payload["answers"]}
        self.assertEqual(answers["q2_1"]["group"], "۲. جواز فعالیت")
        self.assertEqual(answers["q2_1"]["display"], "۱ – تکمیل")
        self.assertEqual(answers["signature"]["type"], "image")
        self.assertEqual(len(answers["signature"]["media"]), 1)
        self.assertEqual(
            answers["signature"]["media"][0]["url"],
            f"/kobo-submissions/{self.submission.pk}/attachments/0/",
        )
        self.assertEqual(len(payload["attachments"]), 1)
        self.assertEqual(payload["attachments"][0]["kind"], "image")

    def test_unknown_submission_returns_404(self):
        self.assertEqual(
            self.client.get("/api/v1/kobo-submissions/999/").status_code, 404
        )

    def test_sync_can_be_scoped_to_one_checklist(self):
        with (
            patch(
                "apps.integrations.services.fetch_submissions", return_value=[]
            ) as fetch,
            patch("apps.integrations.services.get_asset", return_value=None),
        ):
            counts = sync_kobo_submissions(self.user, checklist_id=self.checklist.pk)

        self.assertEqual(counts["fetched"], 0)
        fetch.assert_called_once_with("asset-1")

    def test_checklist_can_adopt_an_existing_kobo_project(self):
        asset = {"uid": "adopted-asset", "deployment_status": "deployed"}
        with patch("apps.inspections.services.get_asset", return_value=asset):
            response = self.client.post(
                f"/api/v1/checklists/{self.other.pk}/link-kobo/",
                {"asset_uid": "adopted-asset"},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.other.refresh_from_db()
        self.assertEqual(self.other.kobo_asset_uid, "adopted-asset")
        self.assertEqual(self.other.kobo_deployment_status, "deployed")
        self.assertIsNotNone(self.other.kobo_deployed_at)

    def test_linking_rejects_a_project_used_by_another_checklist(self):
        response = self.client.post(
            f"/api/v1/checklists/{self.other.pk}/link-kobo/",
            {"asset_uid": "asset-1"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("asset_uid", response.json())

    def test_linking_rejects_an_unknown_project(self):
        with patch("apps.inspections.services.get_asset", return_value=None):
            response = self.client.post(
                f"/api/v1/checklists/{self.other.pk}/link-kobo/",
                {"asset_uid": "missing-asset"},
                format="json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("asset_uid", response.json())

    def test_sync_skips_malformed_establishment_id(self):
        with (
            patch(
                "apps.integrations.services.fetch_submissions",
                return_value=[{"_id": 99, "establishment_id": "invalid-uuid"}],
            ),
            patch("apps.integrations.services.get_asset", return_value=None),
        ):
            counts = sync_kobo_submissions(self.user, checklist_id=self.checklist.pk)
        self.assertEqual(counts["skipped"], 1)
        self.assertEqual(counts["created"], 0)

    def test_attachment_connection_closes_when_stream_is_interrupted(self):
        from unittest.mock import Mock
        from config.api.submissions import attachment_chunks

        upstream = Mock()
        upstream.iter_content.return_value = iter([b"first", b"second"])
        chunks = attachment_chunks(upstream)
        self.assertEqual(next(chunks), b"first")
        chunks.close()
        upstream.close.assert_called_once()
