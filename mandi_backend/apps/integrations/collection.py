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
from rest_framework.exceptions import ValidationError

from apps.accounts.services import require, require_checklist_access, scope_checklists
from apps.establishments.models import Establishment
from apps.establishments.services import establishment_choice_csv
from apps.inspections.models import Checklist

from .models import CollectionSubmission, CollectorGrant, FormDeployment
from .providers import CollectionError, provider
from .submissions import form_schema
from .xlsform import XlsFormError, add_establishment_question, set_form_title


def deployment_url(deployment):
    return provider(deployment.provider).form_url(deployment) if deployment else None


def deploy(actor, pk):
    require(actor, "inspections.deploy_checklist")
    require_checklist_access(actor, pk)
    from django.shortcuts import get_object_or_404

    checklist = get_object_or_404(Checklist, pk=pk)
    if not checklist.xlsform:
        raise ValidationError("Upload an XLSForm before deploying.")
    deployment, _ = FormDeployment.objects.get_or_create(
        checklist=checklist,
        provider=settings.COLLECTION_PROVIDER,
        defaults={
            "project_id": settings.COLLECTION_PROJECT_ID,
            "form_id": f"mandi_{checklist.pk}",
        },
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
        output = io.BytesIO()
        workbook.save(output)
        workbook.close()
        provider(deployment.provider).deploy(
            deployment,
            output.getvalue(),
            establishment_choice_csv(kind=checklist.establishment_kind),
        )
    except (CollectionError, XlsFormError, ValueError, OSError, BadZipFile) as exc:
        FormDeployment.objects.filter(pk=deployment.pk).update(
            status="failed", error=str(exc)
        )
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


def submissions(actor, checklist_id=None, establishment_id=None):
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
    return qs


def sync(actor, checklist_id=None):
    require(actor, "inspections.add_inspection")
    qs = FormDeployment.objects.filter(status="deployed")
    qs = scope_checklists(actor, qs, "checklist_id")
    if checklist_id:
        require_checklist_access(actor, checklist_id)
        qs = qs.filter(checklist_id=checklist_id)
    counts = {
        "fetched": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "inspections": 0,
        "unmapped_inspectors": 0,
    }
    try:
        for deployment in qs.select_related("checklist"):
            for remote in provider(deployment.provider).submissions(deployment):
                data = remote.data
                counts["fetched"] += 1
                # Establishment selector is inserted at the form root.
                value = remote.establishment_id
                try:
                    establishment = Establishment.objects.get(
                        pk=value, kind=deployment.checklist.establishment_kind
                    )
                except (
                    Establishment.DoesNotExist,
                    ValueError,
                    DjangoValidationError,
                    TypeError,
                ):
                    counts["skipped"] += 1
                    continue
                identity = remote.submission_id
                if not identity:
                    counts["skipped"] += 1
                    continue
                _submission, created = CollectionSubmission.objects.update_or_create(
                    deployment=deployment,
                    submission_id=identity,
                    defaults={
                        "establishment": establishment,
                        "data": data,
                        "submitted_at": remote.submitted_at,
                    },
                )
                counts["created" if created else "updated"] += 1
                # Map Central's immutable submitter actor ID to a Mandi employee.
                remote_actor = remote.inspector_id
                grant = (
                    CollectorGrant.objects.filter(
                        deployment=deployment, remote_id=remote_actor
                    )
                    .select_related("user")
                    .first()
                )
                if not grant or not grant.user.is_active:
                    counts["unmapped_inspectors"] += 1
                    continue
                from apps.inspections.services import ingest_inspection

                from .submissions import extract_scores
                from .submissions import flatten_answers as flatten

                scores = extract_scores(flatten(data))
                import hashlib
                import json

                summary = {
                    "submission_revision": hashlib.sha256(
                        json.dumps(data, sort_keys=True).encode()
                    ).hexdigest()
                }
                if scores["percent"] is not None:
                    summary["overall_percent"] = scores["percent"]
                date_value = remote.inspected_on
                from datetime import date

                try:
                    inspected_on = date.fromisoformat(date_value)
                except (ValueError, TypeError):
                    counts["skipped"] += 1
                    continue
                kind = remote.inspection_kind
                if kind not in {"comprehensive", "brief", "follow_up", "special"}:
                    counts["skipped"] += 1
                    continue
                ingest_inspection(
                    actor,
                    {
                        "establishment_id": establishment.pk,
                        "checklist_id": deployment.checklist_id,
                        "inspected_on": inspected_on,
                        "kind": kind,
                        "team_ids": [grant.user_id],
                        "provider": deployment.provider,
                        "provider_form_id": f"{deployment.project_id}:{deployment.form_id}",
                        "submission_id": identity,
                        "mapping_version": f"{deployment.provider}-v1",
                        "summary": summary,
                    },
                )
                counts["inspections"] += 1
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
