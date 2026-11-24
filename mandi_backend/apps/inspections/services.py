from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.services import require, require_checklist_access, scope_checklists

from .models import Checklist


def list_checklists(actor):
    require(actor, "inspections.view_checklist")
    return (
        scope_checklists(actor, Checklist.objects.all())
        .annotate(submission_count=Count("deployments__submissions", distinct=True))
        .order_by("name")
    )


def get_checklist(actor, pk):
    require(actor, "inspections.view_checklist")
    try:
        return (
            scope_checklists(actor, Checklist.objects.all())
            .annotate(submission_count=Count("deployments__submissions", distinct=True))
            .get(pk=pk)
        )
    except Checklist.DoesNotExist as exc:
        raise NotFound("Checklist not found.") from exc


@transaction.atomic
def save_checklist(actor, data, pk=None):
    require(
        actor,
        "inspections.change_checklist" if pk else "inspections.add_checklist",
    )
    if pk:
        require_checklist_access(actor, pk)
    obj = get_checklist(actor, pk) if pk else Checklist()
    for field in ("code", "name"):
        if field in data:
            setattr(obj, field, data[field])
    if not pk:
        obj.created_by = actor
    obj.updated_by = actor
    uploaded = data.get("xlsform")
    if uploaded:
        obj.xlsform = uploaded
    elif not obj.xlsform:
        raise ValidationError({"xlsform": "Upload the XLSForm file."})
    try:
        obj.full_clean()
    except DjangoValidationError as exc:
        raise ValidationError(exc.messages) from exc
    obj.save()
    if not pk and actor.restrict_checklist_access:
        actor.allowed_checklists.add(obj)
    return obj


def deploy_checklist(actor, pk, project_id=None, force=False):
    """Deploy through the configured collection provider."""
    from apps.integrations.collection import deploy

    return deploy(actor, pk, project_id, force=force)
