from apps.integrations.submissions import extract_scores, submission_answers

"""API input validation and response shapes; domain rules live in services."""

from apps.establishments.models import Establishment, SourceLink
from apps.inspections.models import Checklist, Inspection
from apps.integrations import services as integrations
from apps.integrations.models import KoboSubmission
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ("id", "username", "display_name", "position", "is_active", "is_staff")


class EmployeeInput(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    display_name = serializers.CharField(max_length=200)
    position = serializers.CharField(max_length=200, allow_blank=True, default="")
    password = serializers.CharField(write_only=True)

    group_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False, default=list
    )


class LoginInput(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class SourceLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceLink
        fields = (
            "id",
            "source",
            "external_id",
            "details",
            "is_demo",
            "linked_by",
            "linked_at",
        )


class EstablishmentSerializer(serializers.ModelSerializer):
    source_links = SourceLinkSerializer(many=True, read_only=True)

    class Meta:
        model = Establishment
        fields = (
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
        )
        read_only_fields = ("id", "created_at", "updated_at")


class ChecklistSerializer(serializers.ModelSerializer):
    kobo_project_url = serializers.SerializerMethodField()
    submission_count = serializers.SerializerMethodField()

    class Meta:
        model = Checklist
        fields = "__all__"

    def get_kobo_project_url(self, obj):
        if not obj.kobo_asset_uid:
            return None
        host = settings.KOBO_HOST_HEADER or settings.KOBO_BASE_URL
        if "://" not in host:
            host = f"http://{host}"
        return f"{host.rstrip('/')}/#/forms/{obj.kobo_asset_uid}"

    def get_submission_count(self, obj):
        count = getattr(obj, "submission_count", None)
        return count if count is not None else obj.kobo_submissions.count()


class KoboSubmissionSerializer(serializers.ModelSerializer):
    checklist_name = serializers.CharField(source="checklist.name", default=None)
    checklist_version = serializers.CharField(source="checklist.version", default=None)
    checklist_id = serializers.IntegerField(source="checklist.id", default=None)
    establishment_name = serializers.CharField(
        source="establishment.name", default=None
    )
    scores = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()
    attachments = serializers.SerializerMethodField()
    kobo_url = serializers.SerializerMethodField()

    class Meta:
        model = KoboSubmission
        fields = (
            "id",
            "asset_uid",
            "submission_id",
            "establishment_id",
            "establishment_name",
            "checklist_id",
            "checklist_name",
            "checklist_version",
            "submitted_at",
            "scores",
            "answers",
            "attachments",
            "kobo_url",
            "data",
        )

    @staticmethod
    def attachment_url(obj, index):
        return f"/kobo-submissions/{obj.pk}/attachments/{index}/"

    def get_scores(self, obj):
        return extract_scores(obj.data)

    def get_answers(self, obj):
        answers = submission_answers(obj.data, obj.form_schema)
        for answer in answers:
            for media in answer.get("media") or []:
                media["url"] = self.attachment_url(obj, media["index"])
        return answers

    def get_attachments(self, obj):
        return [
            {**attachment, "url": self.attachment_url(obj, attachment["index"])}
            for attachment in integrations.submission_attachments(obj.data)
        ]

    def get_kobo_url(self, obj):
        return integrations.kobo_asset_url(obj.asset_uid)


class InspectionSerializer(serializers.ModelSerializer):
    establishment_name = serializers.CharField(source="establishment.name")
    checklist = ChecklistSerializer()
    team = UserSerializer(many=True)
    approved_by = UserSerializer()

    class Meta:
        model = Inspection
        fields = (
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
        )


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


class SubmissionFilters(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True)
    establishment_id = serializers.UUIDField(required=False)
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
