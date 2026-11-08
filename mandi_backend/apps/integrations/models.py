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
