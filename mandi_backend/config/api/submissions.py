from apps.integrations import services as integrations
from apps.integrations.kobo import KoboError
from django.http import FileResponse, StreamingHttpResponse
from django.utils.http import content_disposition_header
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .common import paginated, validated
from .serializers import KoboSubmissionSerializer, SubmissionFilters


def attachment_chunks(response):
    """Close the upstream connection when streaming finishes or is interrupted."""
    try:
        yield from response.iter_content(chunk_size=8192)
    finally:
        response.close()


class ChecklistSubmissions(APIView):
    def get(self, request, pk):
        values = validated(
            SubmissionFilters,
            {k: v for k, v in request.query_params.items() if v != ""},
        )
        return paginated(
            request,
            integrations.checklist_submissions(request.user, pk, values),
            KoboSubmissionSerializer,
        )


class KoboSubmissionDetail(APIView):
    def get(self, request, pk):
        submission = integrations.kobo_submission(request.user, pk)
        return Response(KoboSubmissionSerializer(submission).data)


class KoboSubmissionAttachment(APIView):
    def get(self, request, pk, index):
        try:
            attachment, response = integrations.submission_attachment(
                request.user, pk, index
            )
        except KoboError as exc:
            raise ValidationError({"kobo": str(exc)}) from exc
        if request.query_params.get("playback") == "1" and (
            attachment["basename"].lower().endswith(".amr")
            or attachment.get("mimetype", "").lower() in {"audio/amr", "audio/amr-wb"}
        ):
            from apps.integrations.audio import browser_audio
            from pathlib import Path
            try:
                audio = browser_audio(response)
            except KoboError as exc:
                raise ValidationError({"audio": str(exc)}) from exc
            return FileResponse(audio, content_type="audio/mpeg", filename=f"{Path(attachment['basename']).stem}.mp3")
        content_type = attachment.get("mimetype") or response.headers.get(
            "Content-Type", "application/octet-stream"
        )
        stream = StreamingHttpResponse(
            attachment_chunks(response), content_type=content_type
        )
        stream["Content-Disposition"] = content_disposition_header(
            False, attachment["basename"]
        )
        if response.headers.get("Content-Length"):
            stream["Content-Length"] = response.headers["Content-Length"]
        return stream


class EstablishmentKoboSubmissions(APIView):
    def get(self, request, pk):
        return paginated(
            request,
            integrations.kobo_submissions(request.user, pk),
            KoboSubmissionSerializer,
        )


class KoboSync(APIView):
    def post(self, request):
        class Input(serializers.Serializer):
            establishment_id = serializers.UUIDField(required=False)
            checklist_id = serializers.IntegerField(min_value=1, required=False)

        values = validated(Input, request.data)
        return Response(
            integrations.sync_kobo_submissions(
                request.user,
                establishment_id=values.get("establishment_id"),
                checklist_id=values.get("checklist_id"),
            )
        )
