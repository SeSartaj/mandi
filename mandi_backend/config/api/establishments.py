from apps.accounts import services as accounts
from apps.establishments import services as establishments
from apps.establishments.models import Establishment, SourceLink
from apps.integrations import collection
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
        establishment = establishments.get_establishment(request.user, pk)
        data = EstablishmentSerializer(establishment).data
        data["inspection_stats"] = collection.statistics(request.user, establishment.pk)
        return Response(data)

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
            kind = serializers.CharField(max_length=20, required=False, allow_blank=True)
            checklist_id = serializers.IntegerField(min_value=1, required=False)

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
        from apps.integrations import licensing
        from apps.integrations.registry import ADAPTERS
        systems = list(ExternalSystem.objects.filter(is_active=True).values("code", "name", "adapter"))
        for system in systems:
            if system["adapter"] == "licensing":
                system["searchable"] = licensing.configured()
            else:
                system["searchable"] = system["adapter"] in ADAPTERS
        systems.sort(key=lambda item: (item["code"] != "licensing", item["name"]))
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
        return Response({"enabled": settings.LICENSING_SYNC_ENABLED,
            "interval": settings.LICENSING_SYNC_INTERVAL,
            "states": list(RegistrySyncCursor.objects.values("source_id", "kind_id", "next_page", "last_attempt_at", "last_success_at", "last_error", "counts"))})


REGISTRY_SYNC_PERMISSIONS = (
    "view_establishment",
    "view_sourcelink",
    "add_establishment",
    "change_establishment",
    "change_sourcelink",
)


def latest_full_sync(system):
    latest = system.sync_requests.order_by("-requested_at").first()
    if latest is None:
        return None
    return {
        "state": latest.state,
        "requested_at": latest.requested_at,
        "started_at": latest.started_at,
        "finished_at": latest.finished_at,
        "result": latest.result,
        "error": latest.error,
    }


class RegistrySystems(APIView):
    """Active external systems with connection, sync capability, and sync state."""

    def get(self, request):
        from django.conf import settings
        from apps.establishments.models import ExternalSystem, RegistrySyncCursor, RegistrySyncRequest
        from apps.integrations import licensing
        from apps.integrations.registry import ADAPTERS

        accounts.require(request.user, "establishments.view_establishment")
        can_trigger = all(
            request.user.has_perm(f"establishments.{permission}")
            for permission in REGISTRY_SYNC_PERMISSIONS
        )
        systems = []
        for system in ExternalSystem.objects.filter(is_active=True).order_by("name"):
            adapter = ADAPTERS.get(system.adapter)
            if system.adapter == "licensing":
                configured = licensing.configured()
            else:
                # Archive/survey profiles are delivered through Licensing, so
                # they count as available when that connection is configured.
                configured = adapter is not None or (
                    system.adapter in {"archive", "survey"} and licensing.configured()
                )
            syncable = bool(configured and adapter is not None and hasattr(adapter, "list_page"))
            states = list(
                RegistrySyncCursor.objects.filter(source=system).values(
                    "kind_id",
                    "next_page",
                    "last_attempt_at",
                    "last_success_at",
                    "last_error",
                    "counts",
                )
            )
            systems.append({
                "code": system.code,
                "name": system.name,
                "adapter": system.adapter,
                "configured": configured,
                "syncable": syncable,
                "can_sync": syncable and can_trigger,
                "states": states,
                "full_sync": latest_full_sync(system),
            })
        return Response({
            "enabled": settings.LICENSING_SYNC_ENABLED,
            "interval": settings.LICENSING_SYNC_INTERVAL,
            "systems": systems,
        })


class RegistrySystemSync(APIView):
    """Run one bounded sync batch for a directly supported external system."""
    def post(self, request, code):
        from django.conf import settings
        from apps.establishments.models import ExternalSystem
        from apps.integrations import licensing
        from apps.integrations.registry import adapter_for
        from apps.integrations.registry_sync import sync_batch

        system = ExternalSystem.objects.filter(pk=code, is_active=True).first()
        if system is None:
            raise serializers.ValidationError({"source": "Unknown or inactive external system."})
        if system.adapter == "licensing" and not licensing.configured():
            raise serializers.ValidationError({"source": "The Licensing connection is not configured."})
        adapter = adapter_for(code)
        if adapter is None or not hasattr(adapter, "list_page"):
            raise serializers.ValidationError({"source": "This external system does not support direct sync."})
        try:
            page_size = min(100, max(1, int(request.data.get("page_size", settings.LICENSING_SYNC_PAGE_SIZE))))
        except (TypeError, ValueError):
            raise serializers.ValidationError({"page_size": "Enter a whole number."})
        result = sync_batch(request.user, code, page_size)
        return Response(result, status=202 if result.get("busy") else 200)


class RegistrySystemFullSync(APIView):
    """Queue one complete pass; the registry worker executes it in the background."""

    def post(self, request, code):
        from django.db import IntegrityError, transaction
        from apps.establishments.models import ExternalSystem, RegistrySyncRequest
        from apps.integrations import licensing
        from apps.integrations.registry import adapter_for

        system = ExternalSystem.objects.filter(pk=code, is_active=True).first()
        if system is None:
            raise serializers.ValidationError({"source": "Unknown or inactive external system."})
        if system.adapter == "licensing" and not licensing.configured():
            raise serializers.ValidationError({"source": "The Licensing connection is not configured."})
        adapter = adapter_for(code)
        if adapter is None or not hasattr(adapter, "list_page"):
            raise serializers.ValidationError({"source": "This external system does not support direct sync."})
        for permission in REGISTRY_SYNC_PERMISSIONS:
            accounts.require(request.user, f"establishments.{permission}")
        active = RegistrySyncRequest.objects.filter(
            source=system, state__in=["pending", "running"]
        ).first()
        queued = False
        if active is None:
            try:
                with transaction.atomic():
                    active = RegistrySyncRequest.objects.create(
                        source=system, requested_by=request.user
                    )
                    queued = True
            except IntegrityError:
                active = RegistrySyncRequest.objects.filter(
                    source=system, state__in=["pending", "running"]
                ).first()
        if active is None:
            raise serializers.ValidationError("The complete sync request could not be queued.")
        return Response(
            {"state": active.state, "requested_at": active.requested_at, "queued": queued},
            status=202 if queued else 200,
        )


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
        latitude_delta = math.degrees(1 / 6371)
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
        candidate_ids = list(candidates.values_list("pk", flat=True))
        licensing_by_id = dict(
            SourceLink.objects.filter(
                source="licensing", establishment_id__in=candidate_ids
            ).values_list("establishment_id", "details")
        )
        for obj in candidates.select_related("province", "district").only("id", "name", "address", "latitude", "longitude", "province__name", "district__name").iterator(chunk_size=500):
            lat, lon = obj.latitude, obj.longitude
            if not math.isfinite(lat) or not math.isfinite(lon) or abs(lat) > 90 or abs(lon) > 180:
                continue
            a = math.sin(math.radians(lat - center["latitude"]) / 2) ** 2 + math.cos(math.radians(lat)) * math.cos(math.radians(center["latitude"])) * math.sin(math.radians(lon - center["longitude"]) / 2) ** 2
            distance = 6371 * 2 * math.asin(math.sqrt(min(1, max(0, a))))
            if distance <= 1:
                licensing = licensing_by_id.get(obj.pk) or {}
                rows.append({
                    "id": str(obj.pk),
                    "name": obj.name,
                    "address": obj.address,
                    "province": obj.province.name if obj.province else licensing.get("province", ""),
                    "district": obj.district.name if obj.district else licensing.get("district", ""),
                    "house_number": licensing.get("house_number", ""),
                    "floor": licensing.get("floor", ""),
                    "market": licensing.get("market", ""),
                    "pharmacy_type": licensing.get("pharmacy_type", ""),
                    "latitude": lat,
                    "longitude": lon,
                    "distance_km": round(distance, 3),
                })
        rows.sort(key=lambda row: (row["distance_km"], row["id"]))
        return Response({"results": rows[:100], "count": len(rows), "radius_km": 1})
