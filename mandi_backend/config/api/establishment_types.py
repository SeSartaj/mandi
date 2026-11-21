from apps.establishments import services
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .common import validated
from .serializers import EstablishmentTypeSerializer


class EstablishmentTypes(APIView):
    def get(self, request):
        return Response(
            EstablishmentTypeSerializer(
                services.list_establishment_types(request.user), many=True
            ).data
        )

    def post(self, request):
        class Input(serializers.Serializer):
            code = serializers.SlugField(max_length=20)
            name = serializers.CharField(max_length=100)
            is_active = serializers.BooleanField(required=False, default=True)

        values = validated(Input, request.data)
        obj = services.save_establishment_type(request.user, values)
        return Response(EstablishmentTypeSerializer(obj).data, status=201)


class EstablishmentTypeDetail(APIView):
    def patch(self, request, code):
        class Input(serializers.Serializer):
            name = serializers.CharField(max_length=100, required=False)
            is_active = serializers.BooleanField(required=False)

        values = validated(Input, request.data)
        if not values:
            raise serializers.ValidationError("Nothing to update.")
        obj = services.save_establishment_type(request.user, values, code)
        return Response(EstablishmentTypeSerializer(obj).data)
