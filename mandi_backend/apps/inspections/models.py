from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Q
from apps.core.models import BaseModel
from apps.establishments.models import Establishment


class Checklist(BaseModel):
    class DeploymentStatus(models.TextChoices):
        NOT_DEPLOYED = "not_deployed", "Not deployed"
        DEPLOYING = "deploying", "Deploying"
        DEPLOYED = "deployed", "Deployed"
        FAILED = "failed", "Deployment failed"

    code = models.CharField(max_length=100)
    name = models.CharField(max_length=250)
    version = models.CharField(max_length=100)
    establishment_kind = models.CharField(
        max_length=20, choices=Establishment.Kind.choices
    )
    xlsform = models.FileField(
        upload_to="checklists/xlsforms/",
        blank=True,
        validators=[FileExtensionValidator(["xls", "xlsx"])],
        help_text="XLSForm workbook used for this checklist.",
    )
    kobo_asset_uid = models.CharField(max_length=100, blank=True)
    kobo_deployment_status = models.CharField(
        max_length=30,
        choices=DeploymentStatus.choices,
        default=DeploymentStatus.NOT_DEPLOYED,
    )
    kobo_deployment_error = models.TextField(blank=True)
    kobo_deployed_at = models.DateTimeField(null=True, blank=True)
    kobo_deployed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["code", "version"], name="checklist_version_unique"
            )
        ]
        permissions = [("deploy_checklist", "Can deploy checklists to KoBo")]

    def __str__(self):
        return f"{self.name} ({self.version})"


class Inspection(BaseModel):
    class Kind(models.TextChoices):
        COMPREHENSIVE = "comprehensive", "Comprehensive"
        BRIEF = "brief", "Brief"
        FOLLOW_UP = "follow_up", "Follow-up"
        SPECIAL = "special", "Special"

    establishment = models.ForeignKey(
        Establishment, on_delete=models.PROTECT, related_name="inspections"
    )
    checklist = models.ForeignKey(Checklist, on_delete=models.PROTECT)
    inspected_on = models.DateField()
    kind = models.CharField(max_length=20, choices=Kind.choices)
    team = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="inspections")
    provider = models.CharField(max_length=50)
    provider_form_id = models.CharField(max_length=100)
    submission_id = models.CharField(max_length=200)
    mapping_version = models.CharField(max_length=100)
    summary = models.JSONField(default=dict)
    approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approved_inspections",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    is_demo = models.BooleanField(default=False)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-inspected_on", "-id"]
        indexes = [
            models.Index(fields=["inspected_on", "kind"]),
            models.Index(fields=["approved"]),
        ]
        permissions = [("approve_inspection", "Can approve an inspection")]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "provider_form_id", "submission_id"],
                name="provider_submission_unique",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        approved=False,
                        approved_by__isnull=True,
                        approved_at__isnull=True,
                    )
                    | Q(
                        approved=True,
                        approved_by__isnull=False,
                        approved_at__isnull=False,
                    )
                ),
                name="approval_metadata_consistent",
            ),
        ]
