from apps.inspections import services as inspections
from rest_framework.response import Response
from rest_framework.views import APIView

from .common import filters, paginated, validated
from .serializers import IngestInput, InspectionSerializer, SummaryInput


class Inspections(APIView):
    def get(self, request):
        return paginated(
            request,
            inspections.list_inspections(request.user, filters(request)),
            InspectionSerializer,
        )


class InspectionDetail(APIView):
    def get(self, request, pk):
        return Response(
            InspectionSerializer(inspections.get_inspection(request.user, pk)).data
        )


class Approve(APIView):
    def post(self, request, pk):
        return Response(
            InspectionSerializer(inspections.approve_inspection(request.user, pk)).data
        )


class Ingest(APIView):
    def post(self, request):
        data = validated(IngestInput, request.data)
        data["summary"] = SummaryInput(data["summary"]).data
        return Response(
            InspectionSerializer(inspections.ingest_inspection(request.user, data)).data
        )
