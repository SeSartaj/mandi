"""Provider-neutral collection workflows; all business records live in Mandi."""

import io
from datetime import timedelta
from pathlib import Path
from zipfile import BadZipFile

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.exceptions import APIException, ValidationError

from apps.accounts.services import require, require_checklist_access, scope_checklists
from apps.establishments.models import Establishment
from apps.establishments.services import establishment_choice_csv
from apps.inspections.models import Checklist

from .models import CollectionSubmission, CollectorGrant, FormDeployment
from .providers import CollectionError, provider
from .submissions import form_schema
from .xlsform import (
    XlsFormError,
    add_establishment_question,
    set_form_title,
    uses_establishment_type_filter,
)


def deployment_url(deployment):
    return provider(deployment.provider).form_url(deployment) if deployment else None


class StructureConflict(APIException):
    """The published form changed structure; an operator may force-publish it."""

    status_code = 409
    default_code = "structure_conflict"


def deploy(actor, pk, project_id=None, force=False):
    require(actor, "inspections.deploy_checklist")
    require_checklist_access(actor, pk)
    from django.shortcuts import get_object_or_404

    checklist = get_object_or_404(Checklist, pk=pk)
    if not checklist.xlsform:
        raise ValidationError("Upload an XLSForm before deploying.")
    project = str(project_id or settings.COLLECTION_PROJECT_ID)
    form_id = f"mandi_checklist_{checklist.pk}"
    deployment = FormDeployment.objects.filter(
        checklist=checklist, provider=settings.COLLECTION_PROVIDER
    ).first()
    if deployment is None:
        deployment = FormDeployment.objects.create(
            checklist=checklist,
            provider=settings.COLLECTION_PROVIDER,
            project_id=project,
            form_id=form_id,
        )
    elif deployment.project_id != project or deployment.form_id != form_id:
        # Move to another project and/or adopt the collision-free form id.
        deployment.project_id = project
        deployment.form_id = form_id
        deployment.status = "not_deployed"
        deployment.error = ""
        deployment.save(
            update_fields=["project_id", "form_id", "status", "error"]
        )
    # Atomic claim prevents two uploads from racing to publish different drafts.
    if (
        not FormDeployment.objects.filter(pk=deployment.pk)
        .filter(
            ~Q(status="deploying")
            | Q(started_at__lt=timezone.now() - timedelta(minutes=15))
        )
        .update(status="deploying", error="", started_at=timezone.now())
    ):
        raise ValidationError(
            "This checklist is already deploying. Retry after it finishes."
        )
    all_types = False
    try:
        with checklist.xlsform.open("rb") as source:
            content, _ = add_establishment_question(
                Path(checklist.xlsform.name).name, source.read()
            )
        content = set_form_title(content, checklist.name)
        workbook = load_workbook(io.BytesIO(content))
        sheet = workbook["settings"]
        for key, value in {
            "form_id": deployment.form_id,
            "version": timezone.now().strftime("%Y%m%d%H%M%S%f"),
        }.items():
            col = next(
                (c.column for c in sheet[1] if c.value == key), sheet.max_column + 1
            )
            sheet.cell(1, col, key)
            sheet.cell(2, col, value)
        asset = {"content": {}}
        for name in ("survey", "choices"):
            if name in workbook:
                rows = workbook[name].iter_rows(values_only=True)
                headers = next(rows)
                asset["content"][name] = [dict(zip(headers, row)) for row in rows]
        # Select the first translated label when a workbook has no plain label column.
        for nodes in asset["content"].values():
            for node in nodes:
                if not node.get("label"):
                    node["label"] = next(
                        (
                            v
                            for k, v in node.items()
                            if isinstance(k, str) and k.startswith("label::") and v
                        ),
                        "",
                    )
        deployment.schema = form_schema(asset)
        all_types = uses_establishment_type_filter(workbook)
        output = io.BytesIO()
        workbook.save(output)
        workbook.close()
        provider(deployment.provider).deploy(
            deployment,
            output.getvalue(),
            establishment_choice_csv()
            if all_types
            else establishment_choice_csv(kind=checklist.establishment_kind_id),
            force=force,
        )
    except (CollectionError, XlsFormError, ValueError, OSError, BadZipFile) as exc:
        FormDeployment.objects.filter(pk=deployment.pk).update(
            status="failed", error=str(exc)
        )
        if isinstance(exc, CollectionError) and getattr(
            exc, "structure_conflict", False
        ):
            raise StructureConflict(str(exc)) from exc
        raise ValidationError({"deployment": str(exc)}) from exc
    except Exception:
        FormDeployment.objects.filter(pk=deployment.pk).update(
            status="failed", error="Deployment interrupted. Check server logs."
        )
        raise
    deployment.started_at = timezone.now()
    deployment.status = "deployed"
    deployment.error = ""
    deployment.deployed_at = timezone.now()
    deployment.save()
    if checklist.allows_all_types != all_types:
        checklist.allows_all_types = all_types
        checklist.save(update_fields=["allows_all_types"])
    return checklist


def submissions(
    actor,
    checklist_id=None,
    establishment_id=None,
    establishment_kind=None,
    search=None,
    date_from=None,
    date_to=None,
):
    require(actor, "establishments.view_establishment")
    qs = CollectionSubmission.objects.select_related(
        "deployment__checklist", "establishment"
    )
    qs = scope_checklists(actor, qs, "deployment__checklist_id")
    if checklist_id:
        require_checklist_access(actor, checklist_id)
        qs = qs.filter(deployment__checklist_id=checklist_id)
    if establishment_id:
        qs = qs.filter(establishment_id=establishment_id)
    if establishment_kind:
        qs = qs.filter(establishment__kind_id=establishment_kind)
    if search:
        qs = qs.filter(
            Q(establishment__name__icontains=search)
            | Q(submission_id__icontains=search)
        )
    if date_from:
        qs = qs.filter(submitted_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(submitted_at__date__lte=date_to)
    return qs


def form_versions(actor, checklist_id):
    """Published versions of the checklist's deployed form."""
    require(actor, "inspections.view_checklist")
    require_checklist_access(actor, checklist_id)
    deployment = FormDeployment.objects.filter(
        checklist_id=checklist_id,
        provider=settings.COLLECTION_PROVIDER,
        status="deployed",
    ).first()
    if deployment is None:
        return []
    try:
        return provider(deployment.provider).form_versions(deployment)
    except CollectionError as exc:
        raise ValidationError({"collection": str(exc)}) from exc


def sync(actor, checklist_id=None):
    require(actor, "inspections.deploy_checklist")
    qs = FormDeployment.objects.filter(status="deployed")
    qs = scope_checklists(actor, qs, "checklist_id")
    if checklist_id:
        require_checklist_access(actor, checklist_id)
        qs = qs.filter(checklist_id=checklist_id)
    counts = {"fetched": 0, "created": 0, "updated": 0, "skipped": 0}
    try:
        for deployment in qs.select_related("checklist"):
            for remote in provider(deployment.provider).submissions(deployment):
                counts["fetched"] += 1
                identity = remote.submission_id
                if not identity:
                    counts["skipped"] += 1
                    continue
                try:
                    establishment = Establishment.objects.get(
                        pk=remote.establishment_id
                    )
                except (
                    Establishment.DoesNotExist,
                    ValueError,
                    DjangoValidationError,
                    TypeError,
                ):
                    counts["skipped"] += 1
                    continue
                _submission, created = CollectionSubmission.objects.update_or_create(
                    deployment=deployment,
                    submission_id=identity,
                    defaults={
                        "establishment": establishment,
                        "data": remote.data,
                        "submitted_at": remote.submitted_at,
                        "form_version": remote.form_version,
                    },
                )
                counts["created" if created else "updated"] += 1
    except CollectionError as exc:
        raise ValidationError({"collection": str(exc)}) from exc
    return counts


@transaction.atomic
def provision(actor, user, checklist_id):
    require(actor, "accounts.change_user")
    require_checklist_access(actor, checklist_id)
    user = type(user).objects.select_for_update().get(pk=user.pk)
    require_checklist_access(user, checklist_id)
    if not user.is_active:
        raise ValidationError(
            "Activate the employee before provisioning collection access."
        )
    deployment = FormDeployment.objects.get(
        checklist_id=checklist_id,
        provider=settings.COLLECTION_PROVIDER,
        status="deployed",
    )
    if CollectorGrant.objects.filter(
        user=user, deployment=deployment, active=True
    ).exists():
        raise ValidationError(
            "Revoke the existing collector before issuing new credentials."
        )
    remote = provider(deployment.provider).provision_collector(
        deployment, user.display_name or user.username
    )
    grant = CollectorGrant(user=user, deployment=deployment, remote_id=remote["id"])
    try:
        with transaction.atomic():
            grant.save()
    except Exception:
        provider(deployment.provider).revoke_collector(grant)
        raise
    return {"id": grant.pk, **remote["configuration"]}


def revoke(actor, grant):
    require(actor, "accounts.change_user")
    require_checklist_access(actor, grant.deployment.checklist_id)
    if grant.active:
        provider(grant.deployment.provider).revoke_collector(grant)
        grant.active = False
        grant.save(update_fields=["active"])
