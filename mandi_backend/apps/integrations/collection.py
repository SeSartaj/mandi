"""Provider-neutral collection workflows; all business records live in Mandi."""

import io
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from zipfile import BadZipFile

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone
from openpyxl import load_workbook
from rest_framework.exceptions import APIException, ValidationError

from apps.accounts.services import require, require_checklist_access, scope_checklists
from apps.inspections.models import Checklist

from .entities import ensure_dataset, establishment_for_entity, sync_entities
from .models import CollectionSubmission, CollectorGrant, FormDeployment
from .providers import CollectionError, provider
from .submissions import form_schema
from .xlsform import (
    XlsFormError,
    add_establishment_question,
    set_form_title,
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
        has_establishment = any(
            node.get("name") == "establishment_id"
            for node in asset["content"].get("survey", [])
        )
        dataset = None
        if has_establishment:
            dataset = ensure_dataset(project)
            # A form that links an incomplete list would give wrong choices.
            entity_counts = sync_entities(project, dataset)
            if entity_counts["failed"]:
                raise CollectionError(
                    "Could not sync all establishments to the Entity List."
                )
        output = io.BytesIO()
        workbook.save(output)
        workbook.close()
        provider(deployment.provider).deploy(
            deployment,
            output.getvalue(),
            force=force,
            dataset=dataset,
        )
        deployment.entity_list = dataset or ""
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


def statistics(actor, establishment_id):
    """Inspection counters for one establishment, scoped to the actor's checklists."""
    qs = submissions(actor, establishment_id=establishment_id)
    now = timezone.localtime()
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    totals = qs.aggregate(total=Count("pk"), last=Max("submitted_at"))
    return {
        "total": totals["total"] or 0,
        "this_year": qs.filter(submitted_at__gte=year_start).count(),
        "last_submitted_at": totals["last"],
    }


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
                establishment = None
                if remote.establishment_id:
                    establishment = establishment_for_entity(
                        deployment.project_id, remote.establishment_id
                    )
                    if establishment is None:
                        counts["skipped"] += 1
                        continue
                _submission, created = CollectionSubmission.objects.update_or_create(
                    deployment=deployment,
                    submission_id=identity,
                    defaults={
                        "establishment": establishment,
                        "establishment_snapshot": (
                            {
                                "id": str(establishment.pk),
                                "name": establishment.name,
                                "kind": establishment.kind_id,
                                "province": (
                                    establishment.province.name
                                    if establishment.province
                                    else ""
                                ),
                                "district": (
                                    establishment.district.name
                                    if establishment.district
                                    else ""
                                ),
                                "address": establishment.address,
                            }
                            if establishment
                            else {}
                        ),
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
def provision(actor, user, checklist_ids):
    if isinstance(checklist_ids, int):
        checklist_ids = [checklist_ids]
    checklist_ids = sorted({int(checklist_id) for checklist_id in checklist_ids})
    if not checklist_ids:
        raise ValidationError("Select at least one checklist.")
    for checklist_id in checklist_ids:
        require_checklist_access(actor, checklist_id)
    user = type(user).objects.select_for_update().get(pk=user.pk)
    if not user.is_active:
        raise ValidationError(
            "Activate the employee before provisioning collection access."
        )
    deployments = list(
        FormDeployment.objects.filter(
            checklist_id__in=checklist_ids,
            provider=settings.COLLECTION_PROVIDER,
            status="deployed",
        )
        .select_related("checklist")
        .order_by("project_id", "checklist_id")
    )
    if {deployment.checklist_id for deployment in deployments} != set(checklist_ids):
        raise ValidationError("Deploy all selected checklists first.")
    for deployment in deployments:
        require_checklist_access(user, deployment.checklist_id)

    by_project = defaultdict(list)
    for deployment in deployments:
        by_project[str(deployment.project_id)].append(deployment)
    existing = CollectorGrant.objects.filter(
        user=user,
        active=True,
        deployment__project_id__in=by_project,
    ).select_related("deployment__checklist")
    existing_by_project = defaultdict(list)
    for grant in existing:
        existing_by_project[str(grant.deployment.project_id)].append(grant)

    credentials = []
    added = []
    unchanged = []
    for project_id, project_deployments in by_project.items():
        grants = existing_by_project.get(project_id, [])
        remote_ids = {grant.remote_id for grant in grants}
        if len(remote_ids) > 1:
            raise ValidationError(
                "This employee has multiple active credentials for one ODK "
                "project. Revoke them before creating new access."
            )
        granted = {grant.deployment_id: grant for grant in grants}
        new_deployments = [
            deployment
            for deployment in project_deployments
            if deployment.pk not in granted
        ]
        unchanged.extend(
            _grant_summary(grant)
            for deployment in project_deployments
            if (grant := granted.get(deployment.pk)) is not None
        )
        if not new_deployments:
            continue

        adapter = provider(project_deployments[0].provider)
        remote_id = next(iter(remote_ids), None)
        if remote_id is not None:
            assigned = []
            try:
                for deployment in new_deployments:
                    adapter.assign_collector(deployment, remote_id)
                    assigned.append(deployment)
                created = _create_grants(user, new_deployments, remote_id)
            except Exception:
                for deployment in assigned:
                    try:
                        adapter.unassign_collector(deployment, remote_id)
                    except CollectionError:
                        pass
                raise
            added.extend(_grant_summary(grant) for grant in created)
            continue

        remote = adapter.create_collector(
            project_id, user.display_name or user.username
        )
        remote_id = remote["id"]
        assigned = []
        try:
            for deployment in new_deployments:
                adapter.assign_collector(deployment, remote_id)
                assigned.append(deployment)
            created = _create_grants(user, new_deployments, remote_id)
        except Exception:
            for deployment in assigned:
                try:
                    adapter.unassign_collector(deployment, remote_id)
                except CollectionError:
                    pass
            try:
                adapter.delete_collector(project_id, remote_id)
            except CollectionError:
                pass
            raise
        credentials.append(
            {
                "project_id": int(project_id),
                "remote_id": remote_id,
                **adapter.collector_configuration(project_id, remote["token"]),
                "checklists": [_grant_summary(grant) for grant in created],
            }
        )
    return {"credentials": credentials, "added": added, "unchanged": unchanged}


def _grant_summary(grant):
    return {
        "grant_id": grant.pk,
        "checklist_id": grant.deployment.checklist_id,
        "checklist_name": grant.deployment.checklist.name,
    }


def _create_grants(user, deployments, remote_id):
    return [
        CollectorGrant.objects.create(
            user=user, deployment=deployment, remote_id=remote_id
        )
        for deployment in deployments
    ]


def revoke(actor, grant):
    require(actor, "accounts.change_user")
    require_checklist_access(actor, grant.deployment.checklist_id)
    if not grant.active:
        return
    adapter = provider(grant.deployment.provider)
    shared = (
        CollectorGrant.objects.filter(
            user=grant.user,
            active=True,
            remote_id=grant.remote_id,
            deployment__project_id=grant.deployment.project_id,
        )
        .exclude(pk=grant.pk)
        .exists()
    )
    if shared:
        adapter.unassign_collector(grant.deployment, grant.remote_id)
    else:
        adapter.delete_collector(grant.deployment.project_id, grant.remote_id)
    grant.active = False
    grant.save(update_fields=["active"])
