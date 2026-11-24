from django.core.validators import FileExtensionValidator
from django.db import models

from apps.core.models import BaseModel


class Checklist(BaseModel):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=250)
    xlsform = models.FileField(
        upload_to="checklists/xlsforms/",
        blank=True,
        validators=[FileExtensionValidator(["xls", "xlsx"])],
        help_text="XLSForm workbook used for this checklist.",
    )

    class Meta:
        permissions = [("deploy_checklist", "Can deploy checklists")]

    def __str__(self):
        return self.name