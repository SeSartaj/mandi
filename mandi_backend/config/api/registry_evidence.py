from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.inspections.services import capture_evidence, get_inspection
from .common import validated


class InspectionEvidenceView(APIView):
    def get(self, request, pk):
        obj = get_inspection(request.user, pk)
        return Response(list(obj.evidence.values("id", "source", "external_id", "fields", "captured_at", "captured_by_id")))

    def post(self, request, pk):
        class Input(serializers.Serializer):
            source = serializers.SlugField(max_length=20)
            selected_fields = serializers.ListField(child=serializers.CharField(max_length=64), min_length=1, max_length=100)
        evidence = capture_evidence(request.user, pk, **validated(Input, request.data))
        return Response({"id": evidence.pk}, status=201)
