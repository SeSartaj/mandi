from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.throttling import ScopedRateThrottle
from apps.accounts import services as accounts
from apps.establishments import services as establishments
from apps.inspections import services as inspections
from apps.integrations import services as integrations
from apps.reporting import services as reporting
from apps.establishments.models import Establishment, SourceLink
from apps.inspections.models import Inspection, Checklist


class MandiPagination(PageNumberPagination):
    """Shared page size contract for the copied CMS table/pagination controls."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ["id", "username", "display_name", "position", "is_active", "is_staff"]


class EmployeeInput(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    display_name = serializers.CharField(max_length=200)
    position = serializers.CharField(max_length=200, allow_blank=True, default="")
    password = serializers.CharField(write_only=True)

    group_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list
    )


class PermissionGroups(APIView):
    def get(self, request):
        return Response(
            [
                {
                    "id": group.pk,
                    "name": group.name,
                    "permissions": [
                        f"{p.content_type.app_label}.{p.codename}"
                        for p in group.permissions.all()
                    ],
                }
                for group in accounts.permission_groups(request.user)
            ]
        )


class LoginInput(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class SourceLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceLink
        fields = [
            "id",
            "source",
            "external_id",
            "details",
            "is_demo",
            "linked_by",
            "linked_at",
        ]


class EstablishmentSerializer(serializers.ModelSerializer):
    source_links = SourceLinkSerializer(many=True, read_only=True)

    class Meta:
        model = Establishment
        fields = [
            "id",
            "name",
            "kind",
            "subtype",
            "province",
            "district",
            "address",
            "phone",
            "source_links",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Checklist
        fields = "__all__"


class InspectionSerializer(serializers.ModelSerializer):
    establishment_name = serializers.CharField(source="establishment.name")
    checklist = ChecklistSerializer()
    team = UserSerializer(many=True)
    approved_by = UserSerializer()

    class Meta:
        model = Inspection
        fields = [
            "id",
            "establishment_id",
            "establishment_name",
            "checklist",
            "inspected_on",
            "kind",
            "team",
            "provider",
            "provider_form_id",
            "submission_id",
            "mapping_version",
            "summary",
            "approved",
            "approved_by",
            "approved_at",
            "is_demo",
            "synced_at",
        ]


class SectionInput(serializers.Serializer):
    name = serializers.CharField()
    earned = serializers.FloatField(min_value=0)
    possible = serializers.FloatField(min_value=0)


class FindingInput(serializers.Serializer):
    issue = serializers.CharField()
    action = serializers.CharField(required=False, allow_blank=True, default="")
    deadline = serializers.DateField(required=False)


class SummaryInput(serializers.Serializer):
    overall_percent = serializers.FloatField(min_value=0, max_value=100, required=False)
    sections = SectionInput(many=True, required=False)
    findings = FindingInput(many=True, required=False)


class IngestInput(serializers.Serializer):
    establishment_id = serializers.UUIDField()
    checklist_id = serializers.IntegerField(min_value=1)
    inspected_on = serializers.DateField()
    kind = serializers.ChoiceField(choices=Inspection.Kind.choices)
    team_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False
    )
    provider = serializers.CharField(max_length=50)
    provider_form_id = serializers.CharField(max_length=100)
    submission_id = serializers.CharField(max_length=200)
    mapping_version = serializers.CharField(max_length=100)
    summary = SummaryInput(default=dict)


class Filters(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True)
    kind = serializers.CharField(required=False, allow_blank=True)
    province = serializers.CharField(required=False, allow_blank=True)
    district = serializers.CharField(required=False, allow_blank=True)
    establishment_kind = serializers.ChoiceField(
        choices=Establishment.Kind.values, required=False
    )
    establishment_id = serializers.UUIDField(required=False)
    checklist_id = serializers.IntegerField(min_value=1, required=False)
    inspector_id = serializers.IntegerField(min_value=1, required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    approved = serializers.ChoiceField(choices=["true", "false"], required=False)

    def validate(self, data):
        if (
            data.get("date_from")
            and data.get("date_to")
            and data["date_from"] > data["date_to"]
        ):
            raise serializers.ValidationError("Start date must be before end date.")
        return data


def validated(cls, data, **kwargs):
    s = cls(data=data, **kwargs)
    s.is_valid(raise_exception=True)
    return s.validated_data


def filters(request):
    return validated(
        Filters, {k: v for k, v in request.query_params.items() if v != ""}
    )


def paginated(request, qs, serializer):
    p = MandiPagination()
    return p.get_paginated_response(
        serializer(p.paginate_queryset(qs, request), many=True).data
    )


def session(user):
    return {
        "user": UserSerializer(user).data,
        "permissions": sorted(user.get_all_permissions()),
    }


class Login(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        token, user = accounts.login(**validated(LoginInput, request.data))
        return Response({"token": token.key, **session(user)})


class Me(APIView):
    def get(self, request):
        return Response(session(request.user))


class Logout(APIView):
    def post(self, request):
        accounts.logout(request.user)
        return Response(status=204)


class Employees(APIView):
    def get(self, request):
        return paginated(request, accounts.employees(request.user), UserSerializer)

    def post(self, request):
        return Response(
            UserSerializer(
                accounts.create_employee(
                    request.user, validated(EmployeeInput, request.data)
                )
            ).data,
            status=201,
        )


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

        values = validated(Input, request.query_params)
        return Response(
            {
                "is_demo": True,
                "results": integrations.source_candidates(
                    request.user, source, **values
                ),
            }
        )


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


class Checklists(APIView):
    def get(self, request):
        return Response(
            ChecklistSerializer(inspections.list_checklists(request.user), many=True).data
        )

    def post(self, request):
        data = validated(ChecklistSerializer, request.data)
        checklist = inspections.save_checklist(request.user, data)
        return Response(ChecklistSerializer(checklist).data, status=201)


class ChecklistDetail(APIView):
    def patch(self, request, pk):
        existing = inspections.get_checklist(request.user, pk)
        payload = {
            field: getattr(existing, field)
            for field in ("code", "name", "version", "establishment_kind")
        }
        payload.update(
            request.data.dict() if hasattr(request.data, "dict") else request.data
        )
        data = validated(ChecklistSerializer, payload, instance=existing)
        values = {
            field: data[field]
            for field in ("code", "name", "version", "establishment_kind")
        }
        values["xlsform"] = data.get("xlsform")
        checklist = inspections.save_checklist(request.user, values, pk)
        return Response(ChecklistSerializer(checklist).data)


class ChecklistDeploy(APIView):
    def post(self, request, pk):
        checklist = inspections.deploy_checklist(request.user, pk)
        return Response(ChecklistSerializer(checklist).data)


class Choices(APIView):
    def get(self, request):
        class Input(serializers.Serializer):
            kind = serializers.ChoiceField(choices=Establishment.Kind.values)

        return Response(
            integrations.establishment_choices(
                request.user, **validated(Input, request.query_params)
            )
        )


class Coverage(APIView):
    def get(self, request):
        return Response(reporting.coverage(request.user, filters(request)))
