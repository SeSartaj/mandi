from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    display_name = models.CharField(max_length=200, blank=True)
    position = models.CharField(max_length=200, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="accounts_user_unique_email",
            )
        ]

    restrict_checklist_access = models.BooleanField(
        default=False,
        help_text="When enabled, only the selected checklists and their submissions are accessible. An empty selection grants no checklist access.",
    )
    allowed_checklists = models.ManyToManyField(
        "inspections.Checklist", blank=True, related_name="allowed_users",
        help_text="Used when Restrict checklist access is enabled. Normal role permissions are still required.",
    )

    def __str__(self):
        return self.display_name or self.username
