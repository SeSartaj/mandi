from django.db import models

from apps.core.models import BaseModel
from apps.establishments.models import Establishment
from apps.inspections.models import Checklist


class KoboSubmission(BaseModel):
    asset_uid = models.CharField(max_length=100)
    submission_id = models.CharField(max_length=200)
    establishment = models.ForeignKey(
        Establishment, on_delete=models.CASCADE, related_name="kobo_submissions"
    )
    checklist = models.ForeignKey(
        Checklist,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="kobo_submissions",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    data = models.JSONField(default=dict)
    form_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="Question and choice labels copied from the deployed KoBo form.",
    )

    class Meta:
        ordering = ["-submitted_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["asset_uid", "submission_id"],
                name="unique_kobo_submission_per_asset",
            )
        ]
        indexes = [models.Index(fields=["establishment", "-submitted_at"])]

    def __str__(self):
        return f"{self.asset_uid}/{self.submission_id}"


class FormDeployment(models.Model):
    """A checklist can be deployed to different providers without changing its identity."""

    checklist = models.ForeignKey(
        Checklist, on_delete=models.PROTECT, related_name="deployments"
    )
    provider = models.CharField(max_length=50, default="odk")
    project_id = models.CharField(max_length=100)
    form_id = models.CharField(max_length=200)
    status = models.CharField(max_length=30, default="not_deployed")
    error = models.TextField(blank=True)
    deployed_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    schema = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "project_id", "form_id"],
                name="collection_remote_form_unique",
            ),
            models.UniqueConstraint(
                fields=["checklist", "provider"],
                name="collection_checklist_provider_unique",
            ),
        ]


class CollectionSubmission(models.Model):
    deployment = models.ForeignKey(
        FormDeployment, on_delete=models.PROTECT, related_name="submissions"
    )
    submission_id = models.CharField(max_length=200)
    establishment = models.ForeignKey(
        Establishment, on_delete=models.PROTECT, related_name="collection_submissions"
    )
    submitted_at = models.DateTimeField(null=True)
    data = models.JSONField(default=dict)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["deployment", "submission_id"],
                name="collection_submission_unique",
            )
        ]


class CollectorGrant(models.Model):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="collector_grants"
    )
    deployment = models.ForeignKey(FormDeployment, on_delete=models.PROTECT)
    remote_id = models.CharField(max_length=200)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "deployment"],
                condition=models.Q(active=True),
                name="collection_active_grant_unique",
            )
        ]
