from apps.integrations import projects
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .common import validated


class OdkProjects(APIView):
    def get(self, request):
        return Response(projects.list_projects(request.user))

    def post(self, request):
        class Input(serializers.Serializer):
            name = serializers.CharField(max_length=200)

        values = validated(Input, request.data)
        return Response(
            projects.create_project(request.user, values["name"]), status=201
        )


class OdkProjectDetail(APIView):
    def patch(self, request, project_id):
        class Input(serializers.Serializer):
            name = serializers.CharField(max_length=200, required=False)
            archived = serializers.BooleanField(required=False)

        values = validated(Input, request.data)
        if not values:
            raise serializers.ValidationError("Nothing to update.")
        return Response(
            projects.update_project(
                request.user,
                project_id,
                name=values.get("name"),
                archived=values.get("archived"),
            )
        )
