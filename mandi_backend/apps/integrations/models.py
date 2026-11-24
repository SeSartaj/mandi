from django.db import models

from apps.establishments.models import Establishment
from apps.inspections.models import Checklist


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
    entity_list = models.CharField(max_length=100, blank=True)

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
        Establishment,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="collection_submissions",
    )
    submitted_at = models.DateTimeField(null=True)
    form_version = models.CharField(max_length=100, blank=True)
    establishment_snapshot = models.JSONField(default=dict, blank=True, editable=False)
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


class EntityBinding(models.Model):
    """The ODK Entity UUID used for an establishment in one Central project."""

    establishment = models.ForeignKey(
        Establishment, on_delete=models.CASCADE, related_name="entity_bindings"
    )
    project_id = models.CharField(max_length=100)
    entity_uuid = models.UUIDField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["establishment", "project_id"],
                name="entity_binding_project_unique",
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
