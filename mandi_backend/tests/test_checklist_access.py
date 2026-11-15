from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.test import APIClient

from apps.inspections.models import Checklist
from apps.inspections.services import list_checklists, get_checklist, approve_inspection
from apps.integrations.services import checklist_submissions, kobo_submission, kobo_submissions, submission_attachment
from apps.establishments.models import Establishment
from apps.integrations.models import KoboSubmission
from apps.inspections.models import Inspection


class ChecklistAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="scoped", restrict_checklist_access=True)
        self.user.user_permissions.set(Permission.objects.all())
        self.allowed = Checklist.objects.create(name="Allowed", code="allowed", version="1", establishment_kind="pharmacy")
        self.denied = Checklist.objects.create(name="Denied", code="denied", version="1", establishment_kind="pharmacy")
        self.user.allowed_checklists.add(self.allowed)
        self.establishment = Establishment.objects.create(name="Test", kind="pharmacy", province="Kabul")
        self.submission = KoboSubmission.objects.create(asset_uid="asset", submission_id="1", establishment=self.establishment, checklist=self.denied)

    def test_only_assigned_checklists_are_visible(self):
        self.assertEqual(list(list_checklists(self.user)), [self.allowed])
        with self.assertRaises(NotFound):
            get_checklist(self.user, self.denied.pk)
        self.user.allowed_checklists.clear()
        self.assertEqual(list(list_checklists(self.user)), [])

    def test_submissions_and_attachments_cannot_bypass_checklist_access(self):
        with self.assertRaises(PermissionDenied):
            checklist_submissions(self.user, self.denied.pk)
        self.assertFalse(kobo_submissions(self.user, self.establishment.pk).exists())
        with self.assertRaises(NotFound):
            kobo_submission(self.user, self.submission.pk)
        with self.assertRaises(NotFound):
            submission_attachment(self.user, self.submission.pk, 0)
        self.user.allowed_checklists.add(self.denied)
        self.assertEqual(kobo_submission(self.user, self.submission.pk), self.submission)

    def test_unrestricted_users_keep_existing_access(self):
        self.user.restrict_checklist_access = False
        self.assertEqual(list_checklists(self.user).count(), 2)

    def test_allowlist_does_not_grant_role_permissions(self):
        self.user.user_permissions.clear()
        self.user = get_user_model().objects.get(pk=self.user.pk)
        with self.assertRaises(PermissionDenied):
            list_checklists(self.user)

    def test_api_and_admin_filter_checklists(self):
        from apps.inspections.admin import ChecklistAdmin
        from django.contrib.admin import site
        from django.test import RequestFactory
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.get("/api/v1/checklists/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data], [self.allowed.pk])
        request = RequestFactory().get("/admin/")
        request.user = self.user
        self.assertEqual(list(ChecklistAdmin(Checklist, site).get_queryset(request)), [self.allowed])
