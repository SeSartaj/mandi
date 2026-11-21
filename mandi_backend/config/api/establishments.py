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
        class Input(serializers.Serializer):
            purpose = serializers.ChoiceField(choices=["detail", "evidence"], default="detail")
        options = validated(Input, request.query_params)
        return Response(integrations.source_detail(request.user, pk, source, include_sensitive=False if options["purpose"] == "evidence" else None))

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
            kind = serializers.CharField(max_length=20)
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
            kind = serializers.CharField(max_length=20)

        return Response(
            integrations.establishment_choices(
                request.user, **validated(Input, request.query_params)
            )
        )


class EstablishmentsCsv(APIView):
    def get(self, request):
        # The CSV includes Licensing contact details used by deployed forms.
        accounts.require(request.user, "inspections.deploy_checklist")
        response = HttpResponse(
            establishments.establishment_choice_csv(),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = 'attachment; filename="establishments.csv"'
        return response


class RegistryImport(APIView):
    def post(self, request):
        class Input(serializers.Serializer):
            source = serializers.SlugField(max_length=20)
            external_id = serializers.CharField(max_length=200)
            kind = serializers.SlugField(max_length=20)
        obj = establishments.import_establishment(request.user, **validated(Input, request.data))
        return Response(EstablishmentSerializer(obj).data, status=201)


class RegistryRefresh(APIView):
    def post(self, request, pk):
        return Response(EstablishmentSerializer(establishments.refresh_identity(request.user, pk)).data)


class RegistryOwnership(APIView):
    def post(self, request, pk):
        class Input(serializers.Serializer):
            source = serializers.SlugField(max_length=20, allow_null=True)
        return Response(EstablishmentSerializer(establishments.transfer_ownership(request.user, pk, **validated(Input, request.data))).data)


class RegistryCatalog(APIView):
    def get(self, request):
        accounts.require(request.user, "establishments.view_establishment")
        from apps.establishments.models import EstablishmentType, ExternalSystem
        from apps.integrations.registry import licensing_uses_registration
        systems = list(ExternalSystem.objects.filter(is_active=True).values("code", "name", "adapter"))
        if licensing_uses_registration():
            systems = [system for system in systems if system["code"] != "licensing"]
            for system in systems:
                if system["code"] == "registration":
                    system["name"] = "Licensing"
        from django.conf import settings
        from apps.integrations import licensing
        from apps.integrations.registry import ADAPTERS
        for system in systems:
            code = system["code"]
            system["searchable"] = bool(
                (system["adapter"] == "registration" and settings.REGISTRATION_BASE_URL and settings.REGISTRATION_API_KEY)
                or (system["adapter"] == "licensing" and licensing.configured())
                or (system["adapter"] not in {"registration", "licensing"} and system["adapter"] in ADAPTERS))
        systems.sort(key=lambda item: (item["code"] not in {"registration", "licensing"}, item["name"]))
        from apps.core.models import District, Province
        return Response({
            "types": list(EstablishmentType.objects.filter(is_active=True).values("code", "name")),
            "systems": systems,
            "provinces": list(Province.objects.filter(is_active=True).values("id", "name", "name_local")),
            "districts": list(District.objects.filter(is_active=True).values("id", "name", "name_local", "province_id")),
        })


class RegistrySyncStatus(APIView):
    def get(self, request):
        accounts.require(request.user, "establishments.view_establishment")
        from django.conf import settings
        from apps.establishments.models import RegistrySyncCursor
        return Response({"enabled": settings.REGISTRATION_SYNC_ENABLED,
            "interval": settings.REGISTRATION_SYNC_INTERVAL,
            "states": list(RegistrySyncCursor.objects.values("source_id", "kind_id", "next_page", "last_attempt_at", "last_success_at", "last_error", "counts"))})


class NearbyEstablishments(APIView):
    def get(self, request):
        import math
        accounts.require(request.user, "establishments.view_establishment")
        class Input(serializers.Serializer):
            latitude = serializers.FloatField(min_value=-90, max_value=90)
            longitude = serializers.FloatField(min_value=-180, max_value=180)
        center = validated(Input, request.query_params)
        if not all(math.isfinite(value) for value in center.values()):
            raise serializers.ValidationError("Invalid coordinates.")
        rows = []
        # Bound the database scan before calculating the exact great-circle distance.
        latitude_delta = math.degrees(5 / 6371)
        longitude_delta = min(180, latitude_delta / max(0.000001, math.cos(math.radians(center["latitude"]))))
        candidates = Establishment.objects.filter(
            latitude__gte=center["latitude"] - latitude_delta,
            latitude__lte=center["latitude"] + latitude_delta,
            longitude__isnull=False,
        )
        if longitude_delta < 180:
            from django.db.models import Q
            west, east = center["longitude"] - longitude_delta, center["longitude"] + longitude_delta
            if west < -180:
                candidates = candidates.filter(Q(longitude__gte=west + 360) | Q(longitude__lte=east))
            elif east > 180:
                candidates = candidates.filter(Q(longitude__gte=west) | Q(longitude__lte=east - 360))
            else:
                candidates = candidates.filter(longitude__gte=west, longitude__lte=east)
        for obj in candidates.only("id", "name", "address", "latitude", "longitude").iterator(chunk_size=500):
            lat, lon = obj.latitude, obj.longitude
            if not math.isfinite(lat) or not math.isfinite(lon) or abs(lat) > 90 or abs(lon) > 180:
                continue
            a = math.sin(math.radians(lat - center["latitude"]) / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(center["latitude"])) * math.sin(math.radians(lon - center["longitude"]) / 2) ** 2
            distance = 6371 * 2 * math.asin(math.sqrt(min(1, max(0, a))))
            if distance <= 5:
                rows.append({"id": str(obj.pk), "name": obj.name, "address": obj.address,
                             "latitude": lat, "longitude": lon, "distance_km": round(distance, 3)})
        rows.sort(key=lambda row: (row["distance_km"], row["id"]))
        return Response({"results": rows[:100], "count": len(rows), "radius_km": 5})
