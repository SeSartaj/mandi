import math
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from django.db import models
from apps.core.models import BaseModel, District, Province


class EstablishmentType(models.Model):
    code = models.SlugField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ExternalSystem(models.Model):
    code = models.SlugField(max_length=20, primary_key=True)
    name = models.CharField(max_length=100)
    adapter = models.SlugField(max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Establishment(BaseModel):
    class Kind(models.TextChoices):
        PHARMACY = "pharmacy", "Pharmacy"
        WHOLESALER = "wholesaler", "Wholesaler"
        IMPORTER = "importer", "Importer"
        FACTORY = "factory", "Factory"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=250)
    kind = models.ForeignKey(
        EstablishmentType, on_delete=models.PROTECT, related_name="establishments"
    )
    province = models.ForeignKey(
        Province, null=True, blank=True, on_delete=models.PROTECT, related_name="establishments"
    )
    district = models.ForeignKey(
        District, null=True, blank=True, on_delete=models.PROTECT, related_name="establishments"
    )
    address = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(null=True, blank=True, validators=[MinValueValidator(-180), MaxValueValidator(180)])

    def clean(self):
        from django.core.exceptions import ValidationError
        super().clean()
        if (self.latitude is None) != (self.longitude is None):
            raise ValidationError("Provide both latitude and longitude.")
        if any(value is not None and not math.isfinite(value) for value in (self.latitude, self.longitude)):
            raise ValidationError("Coordinates must be finite numbers.")
        if self.kind_id and not EstablishmentType.objects.filter(
            pk=self.kind_id, is_active=True
        ).exists():
            raise ValidationError({"kind": "Select an active establishment type."})
        if self.district and self.province and self.district.province_id != self.province_id:
            raise ValidationError({"district": "District must belong to the selected province."})

    def get_kind_display(self):
        return str(self.kind) if self.kind_id else ""

    @property
    def primary_source(self):
        return next((link.source for link in self.source_links.all() if link.is_primary), None)

    class Meta:
        ordering = ["name", "id"]
        indexes = [models.Index(fields=["kind", "province"])]


class SourceLink(models.Model):
    class Source(models.TextChoices):
        SURVEY = "survey", "Survey"
        ARCHIVE = "archive", "Archive"
        LICENSING = "licensing", "Licensing"
        REGISTRATION = "registration", "Registration"

    establishment = models.ForeignKey(
        Establishment, on_delete=models.CASCADE, related_name="source_links"
    )
    source = models.CharField(max_length=20)
    external_id = models.CharField(max_length=200)
    details = models.JSONField(default=dict)
    is_primary = models.BooleanField(default=False)
    derived_from = models.CharField(max_length=20, blank=True, db_default="")
    last_synced_at = models.DateTimeField(null=True, blank=True)
    linked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    linked_at = models.DateTimeField(auto_now=True)

    class Meta:
        permissions = [("view_sensitive_source_details", "Can view personal identity details from external sources")]
        constraints = [
            models.UniqueConstraint(fields=["establishment"], condition=models.Q(is_primary=True), name="one_primary_source"),
            models.UniqueConstraint(
                fields=["establishment", "source"], name="one_link_per_source"
            ),
            models.UniqueConstraint(
                fields=["source", "external_id"], name="unique_external_establishment"
            ),
        ]


class RegistrySyncCursor(models.Model):
    source = models.ForeignKey(ExternalSystem, on_delete=models.PROTECT)
    kind = models.ForeignKey(EstablishmentType, on_delete=models.PROTECT)
    next_page = models.PositiveIntegerField(default=1)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=250, blank=True)
    counts = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["source", "kind"], name="registry_sync_cursor_unique")]
