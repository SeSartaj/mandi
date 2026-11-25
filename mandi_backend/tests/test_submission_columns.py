from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.establishments.models import Establishment, EstablishmentType
from apps.inspections.models import Checklist
from apps.integrations.models import CollectionSubmission, FormDeployment


class SubmissionColumnsTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="admin", password="TestPassword-2026!", email="admin@example.test"
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.establishment = Establishment.objects.create(
            name="Pharmacy", kind=EstablishmentType.objects.get(pk="pharmacy")
        )
        self.checklist = Checklist.objects.create(code="q", name="Questions")
        self.deployment = FormDeployment.objects.create(
            checklist=self.checklist,
            provider="odk",
            project_id="1",
            form_id="mandi_q",
            status="deployed",
            schema={
                "labels": {"q1": "Clean?", "q2": "Notes"},
                "types": {"q1": "select_one yesno", "q2": "text"},
                "paths": {"q1": "sec/q1", "q2": "sec/q2"},
                "groups": {"sec": "Section"},
                "order": ["q1", "q2"],
                "choices": {"q1": {"yes": "Yes", "no": "No"}},
            },
        )
        for index, (q1, q2) in enumerate([("yes", "clean shop"), ("no", "dusty")]):
            CollectionSubmission.objects.create(
                deployment=self.deployment,
                submission_id=f"s{index}",
                establishment=self.establishment,
                data={"q1": q1, "q2": q2},
            )

    def test_questions_endpoint_returns_form_columns(self):
        response = self.client.get(f"/api/v1/checklists/{self.checklist.pk}/questions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data], ["q1", "q2"])
        self.assertEqual(response.data[0]["group"], "Section")

    def test_answer_column_filter_matches_values_and_choice_labels(self):
        response = self.client.get(
            "/api/v1/submissions/",
            {"checklist_id": self.checklist.pk, "answer.q1": "Yes"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["submission_id"], "s0")

        response = self.client.get(
            "/api/v1/submissions/",
            {"checklist_id": self.checklist.pk, "answer.q2": "dust"},
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["submission_id"], "s1")

    def test_establishment_choices_can_be_scoped_to_a_checklist(self):
        response = self.client.get(
            "/api/v1/integrations/establishment-choices/",
            {"checklist_id": self.checklist.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["name"] for item in response.data], [str(self.establishment.pk)])

    def test_establishment_submissions_are_grouped_by_checklist(self):
        response = self.client.get(
            f"/api/v1/establishments/{self.establishment.pk}/collection-groups/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["checklist_id"], self.checklist.pk)
        self.assertEqual(response.data[0]["count"], 2)
        self.assertEqual(len(response.data[0]["submissions"]), 2)
