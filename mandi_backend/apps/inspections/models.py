from django.core.validators import FileExtensionValidator
from django.db import models

from apps.core.models import BaseModel


class Checklist(BaseModel):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=250)
    establishment_kind = models.ForeignKey(
        "establishments.EstablishmentType",
        on_delete=models.PROTECT,
        related_name="checklists",
    )
    xlsform = models.FileField(
        upload_to="checklists/xlsforms/",
        blank=True,
        validators=[FileExtensionValidator(["xls", "xlsx"])],
        help_text="XLSForm workbook used for this checklist.",
    )
    allows_all_types = models.BooleanField(
        default=False,
        help_text="Set when the form lets the collector choose any establishment type.",
    )

    class Meta:
        permissions = [("deploy_checklist", "Can deploy checklists")]

    def clean(self):
        from django.core.exceptions import ValidationError

        from apps.establishments.models import EstablishmentType

        super().clean()
        if self.establishment_kind_id and not EstablishmentType.objects.filter(
            pk=self.establishment_kind_id, is_active=True
        ).exists():
            raise ValidationError(
                {"establishment_kind": "Select an active establishment type."}
            )

    def __str__(self):
        return self.name
