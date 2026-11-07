from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.services import require
from apps.establishments.models import Establishment
from apps.integrations.kobo import KoboError, deploy_checklist_to_kobo

from .models import Checklist, Inspection


def list_inspections(actor, filters):
    require(actor, "inspections.view_inspection")
    qs = Inspection.objects.select_related(
        "establishment", "checklist", "approved_by"
    ).prefetch_related("team")
    for field in ("establishment_id", "kind", "checklist_id"):
        if filters.get(field):
            qs = qs.filter(**{field: filters[field]})
    if filters.get("inspector_id"):
        qs = qs.filter(team__id=filters["inspector_id"])
    if filters.get("province"):
        qs = qs.filter(establishment__province=filters["province"])
    if filters.get("establishment_kind"):
        qs = qs.filter(establishment__kind=filters["establishment_kind"])
    for key, lookup in [
        ("date_from", "inspected_on__gte"),
        ("date_to", "inspected_on__lte"),
    ]:
        if filters.get(key):
            qs = qs.filter(**{lookup: filters[key]})
    if filters.get("approved") in ("true", "false"):
        qs = qs.filter(approved=filters["approved"] == "true")
    return qs.distinct()


def get_inspection(actor, pk):
    try:
        return list_inspections(actor, {}).get(pk=pk)
    except Inspection.DoesNotExist as exc:
        raise NotFound("Inspection not found.") from exc


def list_checklists(actor):
    require(actor, "inspections.view_checklist")
    return Checklist.objects.order_by("name", "version")


def get_checklist(actor, pk):
    require(actor, "inspections.view_checklist")
    try:
        return Checklist.objects.get(pk=pk)
    except Checklist.DoesNotExist as exc:
        raise NotFound("Checklist not found.") from exc


@transaction.atomic
def save_checklist(actor, data, pk=None):
    require(
        actor,
        "inspections.change_checklist" if pk else "inspections.add_checklist",
    )
    obj = Checklist.objects.get(pk=pk) if pk else Checklist()
    for field in ("code", "name", "version", "establishment_kind"):
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
    return obj


def deploy_checklist(actor, pk):
    """Upload the XLSForm to KoBo and deploy it as a survey."""
    require(actor, "inspections.deploy_checklist")
    try:
        checklist = Checklist.objects.get(pk=pk)
    except Checklist.DoesNotExist as exc:
        raise NotFound("Checklist not found.") from exc
    if not checklist.xlsform:
        raise ValidationError({"xlsform": "Upload an XLSForm before deploying."})

    checklist.kobo_deployment_status = Checklist.DeploymentStatus.DEPLOYING
    checklist.kobo_deployment_error = ""
    checklist.kobo_deployed_by = actor
    checklist.save(
        update_fields=[
            "kobo_deployment_status",
            "kobo_deployment_error",
            "kobo_deployed_by",
        ]
    )

    try:
        asset_uid, asset = deploy_checklist_to_kobo(checklist)
    except KoboError as exc:
        checklist.kobo_deployment_status = Checklist.DeploymentStatus.FAILED
        checklist.kobo_deployment_error = str(exc)
        checklist.save(
            update_fields=[
                "kobo_deployment_status",
                "kobo_deployment_error",
            ]
        )
        raise ValidationError({"deployment": str(exc)}) from exc
    except Exception as exc:
        message = f"Unexpected KoBo deployment error: {exc}"
        checklist.kobo_deployment_status = Checklist.DeploymentStatus.FAILED
        checklist.kobo_deployment_error = message
        checklist.save(
            update_fields=[
                "kobo_deployment_status",
                "kobo_deployment_error",
            ]
        )
        raise ValidationError({"deployment": message}) from exc

    checklist.kobo_asset_uid = asset_uid
    checklist.kobo_deployment_status = Checklist.DeploymentStatus.DEPLOYED
    checklist.kobo_deployment_error = ""
    checklist.kobo_deployed_at = timezone.now()
    checklist.save(
        update_fields=[
            "kobo_asset_uid",
            "kobo_deployment_status",
            "kobo_deployment_error",
            "kobo_deployed_at",
        ]
    )
    return checklist


@transaction.atomic
def create_manual_inspection(
    actor,
    *,
    establishment,
    checklist,
    inspected_on,
    kind,
    team,
    provider,
    provider_form_id,
    submission_id,
    mapping_version,
    summary,
):
    """Service-backed creation used by the admin add form."""
    require(actor, "inspections.add_inspection")
    if checklist.establishment_kind != establishment.kind:
        raise ValidationError("Checklist is not applicable to this establishment type.")
    team = list(team)
    if not team or any(not member.is_active for member in team):
        raise ValidationError({"team": "Select active inspectors."})
    for section in (summary or {}).get("sections", []):
        if section.get("earned", 0) > section.get("possible", 0):
            raise ValidationError(
                {"summary": "Earned score cannot exceed the possible score."}
            )
    obj = Inspection.objects.create(
        establishment=establishment,
        checklist=checklist,
        inspected_on=inspected_on,
        kind=kind,
        provider=provider,
        provider_form_id=provider_form_id,
        submission_id=submission_id,
        mapping_version=mapping_version,
        summary=summary or {},
        created_by=actor,
        updated_by=actor,
    )
    obj.team.set(team)
    return obj


@transaction.atomic
def approve_inspection(actor, pk):
    require(actor, "inspections.approve_inspection")
    try:
        obj = Inspection.objects.select_for_update().get(pk=pk)
    except Inspection.DoesNotExist as exc:
        raise NotFound("Inspection not found.") from exc
    if not obj.approved:
        obj.approved, obj.approved_by, obj.approved_at = True, actor, timezone.now()
        obj.save(update_fields=["approved", "approved_by", "approved_at"])
    return get_inspection(actor, pk)


@transaction.atomic
def ingest_inspection(actor, data):
    """Provider-neutral normalized input; provider mapping happens before this boundary."""
    require(actor, "inspections.add_inspection")
    values = dict(data)
    summary = values.get("summary", {})
    for section in summary.get("sections", []):
        if section["earned"] > section["possible"]:
            raise ValidationError(
                {"summary": "Earned score cannot exceed the possible score."}
            )
    team_ids = values.pop("team_ids")
    try:
        establishment = Establishment.objects.get(pk=values.pop("establishment_id"))
        checklist = Checklist.objects.get(pk=values.pop("checklist_id"))
    except (Establishment.DoesNotExist, Checklist.DoesNotExist) as exc:
        raise ValidationError("Unknown establishment or checklist.") from exc
    if checklist.establishment_kind != establishment.kind:
        raise ValidationError("Checklist is not applicable to this establishment type.")
    team = list(get_user_model().objects.filter(pk__in=team_ids, is_active=True))
    if not team_ids or len(team) != len(set(team_ids)):
        raise ValidationError({"team_ids": "Select active, known inspectors."})
    key = {
        field: values.pop(field)
        for field in ("provider", "provider_form_id", "submission_id")
    }
    payload = dict(values, establishment=establishment, checklist=checklist)
    # The database key serializes concurrent imports of a new submission too.
    obj, created = Inspection.objects.get_or_create(
        **key,
        defaults=dict(payload, created_by=actor, updated_by=actor),
    )
    obj = Inspection.objects.select_for_update().get(pk=obj.pk)
    if not created:
        changed = any(getattr(obj, k) != v for k, v in payload.items()) or set(
            obj.team.values_list("pk", flat=True)
        ) != set(team_ids)
        if not changed:
            return get_inspection(actor, obj.pk)
        obj.approved = False
        obj.approved_by = obj.approved_at = None
        for key_name, value in payload.items():
            setattr(obj, key_name, value)
        obj.updated_by = actor
        obj.save()
    obj.team.set(team)
    return get_inspection(actor, obj.pk)
