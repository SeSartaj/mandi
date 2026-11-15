from apps.accounts import services as accounts
from apps.establishments import services as establishments
from apps.establishments.models import Establishment
from apps.integrations import services as integrations
from django.http import HttpResponse
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .common import filters, paginated, validated
from .serializers import EstablishmentSerializer, SourceLinkSerializer


class Establishments(APIView):
    def get(self, request):
        return paginated(
            request,
            establishments.list_establishments(
                request.user, filters(request)
            ).prefetch_related("source_links"),
            EstablishmentSerializer,
        )

    def post(self, request):
        return Response(
            EstablishmentSerializer(
                establishments.save_establishment(
                    request.user, validated(EstablishmentSerializer, request.data)
                )
            ).data,
            status=201,
        )


class EstablishmentDetail(APIView):
    def get(self, request, pk):
        return Response(
            EstablishmentSerializer(
                establishments.get_establishment(request.user, pk)
            ).data
        )

    def patch(self, request, pk):
        data = validated(EstablishmentSerializer, request.data, partial=True)
        return Response(
            EstablishmentSerializer(
                establishments.save_establishment(request.user, data, pk)
            ).data
        )


class SourceConnection(APIView):
    def get(self, request, pk, source):
        return Response(integrations.source_detail(request.user, pk, source))

    def post(self, request, pk, source):
        class Input(serializers.Serializer):
            external_id = serializers.CharField(max_length=200)

        values = validated(Input, request.data)
        link = establishments.connect_source(
            request.user, pk, source, values["external_id"]
        )
        return Response(SourceLinkSerializer(link).data)

    def delete(self, request, pk, source):
        establishments.disconnect_source(request.user, pk, source)
        return Response(status=204)


class SourceSearch(APIView):
    def get(self, request, source):
        class Input(serializers.Serializer):
            kind = serializers.ChoiceField(choices=Establishment.Kind.values)
            search = serializers.CharField(required=False, allow_blank=True, default="")
            page = serializers.IntegerField(min_value=1, default=1)
            page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)

        values = validated(Input, request.query_params)
        return Response(
            integrations.source_search(request.user, source, **values)
        )


class Choices(APIView):
    def get(self, request):
        class Input(serializers.Serializer):
            kind = serializers.ChoiceField(choices=Establishment.Kind.values)

        return Response(
            integrations.establishment_choices(
                request.user, **validated(Input, request.query_params)
            )
        )


class KoboEstablishmentsCsv(APIView):
    def get(self, request):
        accounts.require(request.user, "establishments.view_establishment")
        response = HttpResponse(
            establishments.establishment_choice_csv(),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = 'attachment; filename="establishments.csv"'
        return response
