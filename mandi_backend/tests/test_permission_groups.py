from importlib import import_module
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient
from apps.accounts.services import create_employee


class PermissionGroupTests(TestCase):
    def user_in(self, name):
        user = get_user_model().objects.create_user(
            username=name.replace(" ", "_"), password="Testing-2026!"
        )
        user.groups.add(Group.objects.get(name=name))
        return user

    def test_migration_installs_explicit_groups_without_seeding(self):
        roles = import_module("apps.accounts.migrations.0002_predefined_groups").ROLES
        for name, specs in roles.items():
            actual = set(
                Group.objects.get(name=name).permissions.values_list(
                    "content_type__app_label", "content_type__model", "codename"
                )
            )
            self.assertEqual(actual, set(specs))
        viewers = self.user_in("Mandi viewers")
        self.assertTrue(viewers.has_perm("inspections.view_inspection"))
        self.assertFalse(viewers.has_perm("inspections.approve_inspection"))
        registry = self.user_in("Mandi registry officers")
        self.assertTrue(registry.has_perm("establishments.change_establishment"))
        self.assertFalse(registry.has_perm("accounts.add_user"))
        reviewer = self.user_in("Mandi inspection reviewers")
        self.assertTrue(reviewer.has_perm("inspections.approve_inspection"))
        self.assertFalse(reviewer.has_perm("inspections.add_inspection"))

    def test_group_assignment_and_escalation_protection(self):
        administrator = self.user_in("Mandi administrators")
        viewer_group = Group.objects.get(name="Mandi viewers")
        user = create_employee(
            administrator,
            {
                "username": "new.viewer",
                "display_name": "Viewer",
                "password": "Testing-2026!",
                "group_ids": [viewer_group.pk],
            },
        )
        self.assertTrue(user.has_perm("establishments.view_establishment"))
        self.assertFalse(user.has_perm("establishments.add_establishment"))
        creator = get_user_model().objects.create_user(username="creator")
        creator.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="accounts", codename="add_user"
            )
        )
        with self.assertRaises(PermissionDenied):
            create_employee(
                creator,
                {
                    "username": "escalated",
                    "password": "Testing-2026!",
                    "group_ids": [viewer_group.pk],
                },
            )
        with self.assertRaises(ValidationError):
            create_employee(
                administrator,
                {
                    "username": "invalid.group",
                    "password": "Testing-2026!",
                    "group_ids": [999999],
                },
            )

    def test_viewer_and_reviewer_api_boundaries(self):
        viewer = self.user_in("Mandi viewers")
        client = APIClient()
        client.force_authenticate(viewer)
        self.assertEqual(client.get("/api/v1/establishments/").status_code, 200)
        self.assertEqual(
            client.post(
                "/api/v1/establishments/",
                {"name": "Forbidden", "kind": "pharmacy", "province": "Kabul"},
            ).status_code,
            403,
        )
        self.assertEqual(client.get("/api/v1/permission-groups/").status_code, 403)
        self.assertEqual(client.post("/api/v1/inspections/1/approve/").status_code, 403)
        admin = self.user_in("Mandi administrators")
        client.force_authenticate(admin)
        response = client.get("/api/v1/permission-groups/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 6)

    def test_new_permissions_do_not_expand_predefined_groups(self):
        ct = Permission.objects.get(
            content_type__app_label="inspections", codename="view_inspection"
        ).content_type
        permission = Permission.objects.create(
            content_type=ct,
            codename="future_sensitive_operation",
            name="Future operation",
        )
        self.assertFalse(Group.objects.filter(permissions=permission).exists())

    def test_employee_api_assigns_predefined_group_and_returns_staff_flag(self):
        administrator = self.user_in("Mandi administrators")
        client = APIClient()
        client.force_authenticate(administrator)
        group = Group.objects.get(name="Mandi viewers")
        response = client.post(
            "/api/v1/employees/",
            {
                "username": "api.viewer",
                "display_name": "API viewer",
                "password": "Testing-2026!",
                "group_ids": [group.pk],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data["is_staff"])
        user = get_user_model().objects.get(username="api.viewer")
        self.assertEqual(
            list(user.groups.values_list("name", flat=True)), ["Mandi viewers"]
        )
