"""API input validation and response shapes; domain rules live in services."""

from apps.core.models import District, Province
from apps.establishments.models import Establishment, EstablishmentType, SourceLink
from apps.inspections.models import Checklist
from apps.integrations.models import CollectionSubmission
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email", "display_name", "position", "is_active", "is_staff", "groups", "restrict_checklist_access", "allowed_checklists")


class EmployeeDetailSerializer(UserSerializer):
    groups_info = serializers.SerializerMethodField()
    allowed_checklists_info = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + (
            "is_superuser",
            "date_joined",
            "last_login",
            "groups_info",
            "allowed_checklists_info",
        )

    def get_groups_info(self, obj):
        return [
            {
                "id": group.pk,
                "name": group.name,
                "permissions": sorted(
                    f"{permission.content_type.app_label}.{permission.codename}"
                    for permission in group.permissions.all()
                ),
            }
            for group in obj.groups.all().order_by("name")
        ]

    def get_allowed_checklists_info(self, obj):
        return [
            {"id": checklist.pk, "code": checklist.code, "name": checklist.name}
            for checklist in obj.allowed_checklists.all().order_by("name")
        ]


class EmployeeInput(serializers.Serializer):
    email = serializers.EmailField(max_length=150)
    display_name = serializers.CharField(max_length=200)
    position = serializers.CharField(max_length=200, allow_blank=True, default="")
    password = serializers.CharField(write_only=True)

    group_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list
    )


class LoginInput(serializers.Serializer):
    email = serializers.EmailField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class EstablishmentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstablishmentType
        fields = ("code", "name", "is_active")


class SourceLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceLink
        fields = (
            "id",
            "source",
            "external_id",
            "details",
            "linked_by",
            "linked_at",
            "is_primary",
            "last_synced_at",
        )


class ProvinceField(serializers.PrimaryKeyRelatedField):
    def __init__(self, **kwargs):
        kwargs.setdefault("queryset", Province.objects.all())
        kwargs.setdefault("allow_null", True)
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if data in (None, ""):
            return None
        if isinstance(data, str) and not data.isdigit():
            from apps.establishments.services import _location_value

            return _location_value(data)
        return super().to_internal_value(data)


class DistrictField(serializers.PrimaryKeyRelatedField):
    def __init__(self, **kwargs):
        kwargs.setdefault("queryset", District.objects.all())
        kwargs.setdefault("allow_null", True)
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        if data in (None, ""):
            return None
        if isinstance(data, str) and not data.isdigit():
            return District.objects.filter(name__iexact=data).first()
        return super().to_internal_value(data)


class EstablishmentSerializer(serializers.ModelSerializer):
    province = ProvinceField()
    district = DistrictField()
    province_name = serializers.CharField(source="province.name", read_only=True)
    province_name_local = serializers.CharField(source="province.name_local", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True)
    district_name_local = serializers.CharField(source="district.name_local", read_only=True)
    source_links = SourceLinkSerializer(many=True, read_only=True)
    primary_source = serializers.ReadOnlyField()

    class Meta:
        model = Establishment
        fields = (
            "id",
            "name",
            "kind",
            "province",
            "province_name",
            "province_name_local",
            "district",
            "district_name",
            "district_name_local",
            "address",
            "latitude",
            "longitude",
            "source_links",
            "primary_source",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ChecklistSerializer(serializers.ModelSerializer):
    submission_count = serializers.SerializerMethodField()
    collection = serializers.SerializerMethodField()

    class Meta:
        model = Checklist
        fields = "__all__"

    def get_collection(self, obj):
        from apps.integrations.collection import deployment_url

        deployment = obj.deployments.filter(provider=settings.COLLECTION_PROVIDER).first()
        if not deployment:
            return {
                "provider": settings.COLLECTION_PROVIDER,
                "project_id": None,
                "form_id": "",
                "status": "not_deployed",
                "error": "",
                "deployed_at": None,
                "url": None,
            }
        return {
            "provider": deployment.provider,
            "project_id": int(deployment.project_id),
            "form_id": deployment.form_id,
            "status": deployment.status,
            "error": deployment.error,
            "deployed_at": deployment.deployed_at,
            "url": deployment_url(deployment),
        }

    def get_submission_count(self, obj):
        count = getattr(obj, "submission_count", None)
        if count is not None:
            return count
        return CollectionSubmission.objects.filter(deployment__checklist=obj).count()


class Filters(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True)
    kind = serializers.CharField(required=False, allow_blank=True)
    province = serializers.CharField(required=False, allow_blank=True)
    district = serializers.CharField(required=False, allow_blank=True)
    establishment_kind = serializers.CharField(max_length=20, required=False)
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


class SubmissionFilters(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True)
    establishment_id = serializers.UUIDField(required=False)
    establishment_kind = serializers.CharField(max_length=20, required=False)
    checklist_id = serializers.IntegerField(min_value=1, required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, data):
        if (
            data.get("date_from")
            and data.get("date_to")
            and data["date_from"] > data["date_to"]
        ):
            raise serializers.ValidationError(
                {"date_to": "The end date must be on or after the start date."}
            )
        return data


class EmployeeUpdate(serializers.Serializer):
    email = serializers.EmailField(max_length=150, required=False)
    display_name = serializers.CharField(max_length=200, required=False)
    position = serializers.CharField(max_length=200, allow_blank=True, required=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False, required=False)
    is_active = serializers.BooleanField(required=False)
    group_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False)
    restrict_checklist_access = serializers.BooleanField(required=False)
    checklist_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False)
