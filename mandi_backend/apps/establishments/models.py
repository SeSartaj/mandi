import uuid
from django.conf import settings
from django.db import models
from apps.core.models import BaseModel


class Establishment(BaseModel):
    class Kind(models.TextChoices):
        PHARMACY = "pharmacy", "Pharmacy"
        WHOLESALER = "wholesaler", "Wholesaler"
        IMPORTER = "importer", "Importer"
        FACTORY = "factory", "Factory"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=250)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    subtype = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100)
    district = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["name", "id"]
        indexes = [models.Index(fields=["kind", "province"])]


class SourceLink(models.Model):
    class Source(models.TextChoices):
        SURVEY = "survey", "Survey"
        ARCHIVE = "archive", "Archive"
        LICENSING = "licensing", "Licensing"

    establishment = models.ForeignKey(
        Establishment, on_delete=models.CASCADE, related_name="source_links"
    )
    source = models.CharField(max_length=20, choices=Source.choices)
    external_id = models.CharField(max_length=200)
    details = models.JSONField(default=dict)
    is_demo = models.BooleanField(default=False)
    linked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    linked_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["establishment", "source"], name="one_link_per_source"
            ),
            models.UniqueConstraint(
                fields=["source", "external_id"], name="unique_external_establishment"
            ),
        ]
