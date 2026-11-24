from apps.accounts.services import require, scope_checklists
from apps.integrations import collection, odk
from apps.integrations.models import CollectorGrant
from apps.integrations.providers import CollectionError, provider
from apps.integrations.submissions import extract_scores, submission_answers
from apps.integrations.submissions import flatten_answers as flatten
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .common import paginated, validated
from .serializers import SubmissionFilters


def _attachment_chunks(response):
    """Close the upstream connection when streaming finishes or is interrupted."""
    try:
        yield from response.iter_content(chunk_size=8192)
    finally:
        response.close()


def _project_directory():
    """Best-effort project names for employee screens.

    Missing Central connectivity must not make the employee page unusable; the
    UI falls back to the project ID when names are unavailable.
    """
    try:
        return [
            {
                "id": int(project["id"]),
                "name": project.get("name") or f"Project {project['id']}",
                "archived": bool(project.get("archived")),
            }
            for project in odk.list_projects()
        ]
    except (CollectionError, KeyError, TypeError, ValueError):
        return None


class CollectionProjects(APIView):
    def get(self, request):
        require(request.user, "accounts.view_user")
        directory = _project_directory()
        if directory is None:
            return Response(
                {
                    "available": False,
                    "projects": [],
                    "error": "Project names are temporarily unavailable.",
                }
            )
        return Response({"available": True, "projects": directory, "error": ""})


class CollectionSubmissionSerializer(serializers.Serializer):
    def to_representation(self, obj):
        checklist = obj.deployment.checklist
        data = flatten(obj.data)
        from apps.integrations.submissions import submission_attachments

        attachments = submission_attachments(obj.data)
        for item in attachments:
            item["url"] = (
                f"/collection-submissions/{obj.pk}/attachments/{item['index']}/"
            )
        display_data = {**data, "_attachments": obj.data.get("_attachments", [])}
        answers = submission_answers(display_data, obj.deployment.schema)
        for answer in answers:
            for media in answer.get("media", []):
                media["url"] = (
                    f"/collection-submissions/{obj.pk}/attachments/{media['index']}/"
                )
        return {
            "id": obj.pk,
            "submission_id": obj.submission_id,
            "asset_uid": obj.deployment.form_id,
            "provider": obj.deployment.provider,
            "checklist_id": checklist.pk,
            "checklist_name": checklist.name,
            "form_version": obj.form_version,
            "establishment_id": str(obj.establishment_id) if obj.establishment_id else None,
            "establishment_name": (
                obj.establishment_snapshot.get("name")
                or (obj.establishment.name if obj.establishment else None)
            ),
            "establishment_kind": (
                obj.establishment_snapshot.get("kind")
                or (obj.establishment.kind_id if obj.establishment else None)
            ),
            "submitted_at": obj.submitted_at,
            "scores": extract_scores(data),
            "answers": answers,
            "attachments": attachments,
            "form_url": collection.deployment_url(obj.deployment),
            "data": obj.data,
        }


class CollectionSync(APIView):
    def post(self, request):
        class Input(serializers.Serializer):
            checklist_id = serializers.IntegerField(min_value=1, required=False)
            establishment_id = serializers.UUIDField(required=False)

        values = validated(Input, request.data)
        return Response(collection.sync(request.user, values.get("checklist_id")))


class EntitySync(APIView):
    def post(self, request):
        require(request.user, "inspections.deploy_checklist")
        from apps.integrations.entities import sync_entities

        class Input(serializers.Serializer):
            project_id = serializers.IntegerField(min_value=1, required=False)
            dataset = serializers.CharField(max_length=100, required=False)

        values = validated(Input, request.data)
        try:
            return Response(
                sync_entities(
                    project_id=values.get("project_id"),
                    name=values.get("dataset"),
                )
            )
        except CollectionError as exc:
            raise ValidationError({"collection": str(exc)}) from exc


class CollectionSubmissions(APIView):
    def get(self, request, pk=None, establishment_pk=None):
        filters = validated(
            SubmissionFilters,
            {k: v for k, v in request.query_params.items() if v != ""},
        )
        qs = collection.submissions(
            request.user,
            pk or filters.get("checklist_id"),
            establishment_pk or filters.get("establishment_id"),
            filters.get("establishment_kind"),
            filters.get("search"),
            filters.get("date_from"),
            filters.get("date_to"),
        )
        return paginated(request, qs, CollectionSubmissionSerializer)


class CollectionSubmissionDetail(APIView):
    def get(self, request, pk):
        return Response(
            CollectionSubmissionSerializer(
                get_object_or_404(collection.submissions(request.user), pk=pk)
            ).data
        )


class CollectorAccess(APIView):
    def get(self, request, pk):
        require(request.user, "accounts.change_user")
        grants = scope_checklists(
            request.user,
            CollectorGrant.objects.filter(user_id=pk, active=True),
            "deployment__checklist_id",
        ).select_related("deployment__checklist")
        grouped = {}
        for grant in grants.order_by(
            "deployment__project_id", "deployment__checklist__name"
        ):
            project_id = str(grant.deployment.project_id)
            key = (project_id, grant.remote_id)
            credential = grouped.setdefault(
                key,
                {
                    "project_id": int(project_id),
                    "remote_id": grant.remote_id,
                    "checklists": [],
                },
            )
            credential["checklists"].append(
                {
                    "grant_id": grant.pk,
                    "checklist_id": grant.deployment.checklist_id,
                    "checklist_name": grant.deployment.checklist.name,
                }
            )
        return Response(list(grouped.values()))

    def post(self, request, pk):
        from django.contrib.auth import get_user_model

        class Input(serializers.Serializer):
            checklist_ids = serializers.ListField(
                child=serializers.IntegerField(min_value=1),
                required=False,
                default=list,
            )
            checklist_id = serializers.IntegerField(min_value=1, required=False)

        values = validated(Input, request.data)
        checklist_ids = values.get("checklist_ids") or (
            [values["checklist_id"]] if values.get("checklist_id") else []
        )
        if not checklist_ids:
            raise ValidationError(
                {"checklist_ids": "Select at least one checklist."}
            )
        user = get_object_or_404(get_user_model(), pk=pk)
        try:
            response = Response(
                collection.provision(request.user, user, checklist_ids),
                status=201,
            )
            response["Cache-Control"] = "no-store"
            return response
        except CollectionError as exc:
            raise ValidationError(str(exc)) from exc

    def delete(self, request, pk):
        require(request.user, "accounts.change_user")

        class Input(serializers.Serializer):
            grant_id = serializers.IntegerField(min_value=1)

        values = validated(Input, request.data)
        grant = get_object_or_404(
            CollectorGrant.objects.select_related("deployment"),
            pk=values["grant_id"],
            user_id=pk,
        )
        try:
            collection.revoke(request.user, grant)
        except CollectionError as exc:
            raise ValidationError(str(exc)) from exc
        return Response(status=204)


class CollectionAttachment(APIView):
    def get(self, request, pk, index):
        from apps.integrations.submissions import submission_attachments
        from django.http import StreamingHttpResponse
        from django.utils.http import content_disposition_header

        obj = get_object_or_404(collection.submissions(request.user), pk=pk)
        attachments = submission_attachments(obj.data)
        if index >= len(attachments):
            from rest_framework.exceptions import NotFound

            raise NotFound("Attachment not found.")
        attachment = attachments[index]
        try:
            upstream = provider(obj.deployment.provider).open_attachment(
                obj.deployment, obj.submission_id, attachment["filename"]
            )
        except CollectionError as exc:
            raise ValidationError(str(exc)) from exc
        response = StreamingHttpResponse(
            _attachment_chunks(upstream),
            content_type=attachment["mimetype"] or "application/octet-stream",
        )
        response["Content-Disposition"] = content_disposition_header(
            True, attachment["basename"]
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response
