import uuid

from django.conf import settings
from django.db import models


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class Country(BaseModel):
    code = models.CharField(max_length=2, unique=True, help_text="ISO 3166-1 alpha-2 code.")
    name = models.CharField(max_length=120, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "countries"

    def __str__(self):
        return self.name


class Province(BaseModel):
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="provinces")
    code = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["country__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["country", "name"], name="unique_province_per_country"
            ),
            models.UniqueConstraint(
                fields=["country", "code"],
                condition=models.Q(code__gt=""),
                name="unique_province_code_per_country",
            ),
        ]

    def __str__(self):
        return self.name


class District(BaseModel):
    province = models.ForeignKey(Province, on_delete=models.PROTECT, related_name="districts")
    code = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["province__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["province", "name"], name="unique_district_per_province"
            ),
            models.UniqueConstraint(
                fields=["province", "code"],
                condition=models.Q(code__gt=""),
                name="unique_district_code_per_province",
            ),
        ]

    def __str__(self):
        return self.name
