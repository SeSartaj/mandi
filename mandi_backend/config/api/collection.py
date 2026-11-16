from apps.accounts.services import require, scope_checklists
from apps.integrations import collection
from apps.integrations.models import CollectorGrant
from apps.integrations.providers import CollectionError, provider
from apps.integrations.submissions import extract_scores, submission_answers
from apps.integrations.submissions import flatten_answers as flatten
from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .common import paginated, validated
from .serializers import SubmissionFilters


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
            "checklist_version": checklist.version,
            "establishment_id": str(obj.establishment_id),
            "establishment_name": obj.establishment.name,
            "submitted_at": obj.submitted_at,
            "scores": extract_scores(data),
            "answers": answers,
            "attachments": attachments,
            "kobo_url": collection.deployment_url(obj.deployment),
            "data": obj.data,
        }


class CollectionSync(APIView):
    def post(self, request):
        if settings.COLLECTION_PROVIDER == "kobo":
            from .submissions import KoboSync

            return KoboSync().post(request)

        class Input(serializers.Serializer):
            checklist_id = serializers.IntegerField(min_value=1, required=False)
            establishment_id = serializers.UUIDField(required=False)

        values = validated(Input, request.data)
        return Response(collection.sync(request.user, values.get("checklist_id")))


class CollectionSubmissions(APIView):
    def get(self, request, pk=None, establishment_pk=None):
        if settings.COLLECTION_PROVIDER == "kobo":
            from .submissions import ChecklistSubmissions, EstablishmentKoboSubmissions

            return (
                ChecklistSubmissions().get(request, pk)
                if pk
                else EstablishmentKoboSubmissions().get(request, establishment_pk)
            )
        filters = validated(
            SubmissionFilters,
            {k: v for k, v in request.query_params.items() if v != ""},
        )
        qs = collection.submissions(
            request.user, pk, establishment_pk or filters.get("establishment_id")
        )
        if filters.get("search"):
            qs = qs.filter(
                Q(establishment__name__icontains=filters["search"])
                | Q(submission_id__icontains=filters["search"])
            )
        if filters.get("date_from"):
            qs = qs.filter(submitted_at__date__gte=filters["date_from"])
        if filters.get("date_to"):
            qs = qs.filter(submitted_at__date__lte=filters["date_to"])
        return paginated(request, qs, CollectionSubmissionSerializer)


class CollectionSubmissionDetail(APIView):
    def get(self, request, pk):
        if settings.COLLECTION_PROVIDER == "kobo":
            from .submissions import KoboSubmissionDetail

            return KoboSubmissionDetail().get(request, pk)
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
        )
        return Response(
            [
                {
                    "id": g.pk,
                    "checklist_id": g.deployment.checklist_id,
                    "checklist_name": g.deployment.checklist.name,
                }
                for g in grants.select_related("deployment__checklist")
            ]
        )

    def post(self, request, pk):
        from django.contrib.auth import get_user_model

        class Input(serializers.Serializer):
            checklist_id = serializers.IntegerField(min_value=1)

        values = validated(Input, request.data)
        user = get_object_or_404(get_user_model(), pk=pk)
        try:
            response = Response(
                collection.provision(request.user, user, values["checklist_id"]),
                status=201,
            )
            response["Cache-Control"] = "no-store"
            return response
        except CollectionError as exc:
            raise ValidationError(str(exc)) from exc
        except collection.FormDeployment.DoesNotExist as exc:
            raise ValidationError("Deploy this checklist first.") from exc

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
        if settings.COLLECTION_PROVIDER == "kobo":
            from .submissions import KoboSubmissionAttachment

            return KoboSubmissionAttachment().get(request, pk, index)
        from apps.integrations.submissions import submission_attachments
        from django.http import StreamingHttpResponse
        from django.utils.http import content_disposition_header

        from .submissions import attachment_chunks

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
            attachment_chunks(upstream),
            content_type=attachment["mimetype"] or "application/octet-stream",
        )
        response["Content-Disposition"] = content_disposition_header(
            True, attachment["basename"]
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response
