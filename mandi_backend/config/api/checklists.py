from apps.inspections import services as inspections
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .common import validated
from .serializers import ChecklistSerializer


class Checklists(APIView):
    def get(self, request):
        return Response(
            ChecklistSerializer(
                inspections.list_checklists(request.user), many=True
            ).data
        )

    def post(self, request):
        data = validated(ChecklistSerializer, request.data)
        checklist = inspections.save_checklist(request.user, data)
        return Response(ChecklistSerializer(checklist).data, status=201)


class ChecklistDetail(APIView):
    def get(self, request, pk):
        checklist = inspections.get_checklist(request.user, pk)
        return Response(ChecklistSerializer(checklist).data)

    def patch(self, request, pk):
        existing = inspections.get_checklist(request.user, pk)
        data = validated(
            ChecklistSerializer, request.data, instance=existing, partial=True
        )
        checklist = inspections.save_checklist(request.user, data, pk)
        return Response(ChecklistSerializer(checklist).data)


class ChecklistDeploy(APIView):
    def post(self, request, pk):
        checklist = inspections.deploy_checklist(request.user, pk)
        return Response(ChecklistSerializer(checklist).data)


class ChecklistLinkKobo(APIView):
    def post(self, request, pk):
        class Input(serializers.Serializer):
            asset_uid = serializers.CharField()

        values = validated(Input, request.data)
        checklist = inspections.link_kobo_asset(request.user, pk, values["asset_uid"])
        return Response(ChecklistSerializer(checklist).data)


class ChecklistMetadata(APIView):
    def post(self, request):
        from apps.accounts.services import require
        from apps.integrations.xlsform import XlsFormError, read_checklist_metadata
        from rest_framework.exceptions import ValidationError

        permission = "inspections.add_checklist" if request.user.has_perm("inspections.add_checklist") else "inspections.change_checklist"
        require(request.user, permission)
        upload = request.FILES.get("xlsform")
        if not upload:
            raise ValidationError({"xlsform": "Select an XLSForm file."})
        try:
            return Response(read_checklist_metadata(upload.name, upload.read()))
        except XlsFormError as exc:
            raise ValidationError({"xlsform": str(exc)}) from exc
