"""OpenAPI contract using the same input/output serializers as the REST layer."""

from rest_framework.response import Response
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.views import APIView
from . import api


def openapi_document():
    mapper = AutoSchema()
    classes = [
        api.LoginInput,
        api.EmployeeInput,
        api.UserSerializer,
        api.EstablishmentSerializer,
        api.SourceLinkSerializer,
        api.ChecklistSerializer,
        api.InspectionSerializer,
        api.IngestInput,
        api.SummaryInput,
    ]
    schemas = {cls.__name__: mapper.map_serializer(cls()) for cls in classes}

    def ref(name):
        return {"$ref": "#/components/schemas/" + name}

    def array(schema):
        return {"type": "array", "items": schema}

    def page(schema):
        return {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "next": {"type": "string", "nullable": True},
                "previous": {"type": "string", "nullable": True},
                "results": array(schema),
            },
        }

    session = {
        "type": "object",
        "properties": {
            "user": ref("UserSerializer"),
            "permissions": array({"type": "string"}),
        },
    }
    filters = []
    for name, field in api.Filters().fields.items():
        filters.append(
            {
                "name": name,
                "in": "query",
                "required": False,
                "schema": mapper.map_field(field),
            }
        )
    paths = {}

    def route(
        path,
        method,
        description,
        output=None,
        body=None,
        query=False,
        code=200,
        public=False,
    ):
        op = {
            "summary": description,
            "responses": {str(code): {"description": "Success"}},
            "parameters": [],
            "security": [] if public else [{"tokenAuth": []}],
        }
        if output:
            op["responses"][str(code)]["content"] = {
                "application/json": {"schema": output}
            }
        if body:
            op["requestBody"] = {
                "required": True,
                "content": {"application/json": {"schema": body}},
            }
        if query:
            op["parameters"].extend(filters)
            op["parameters"].append(
                {
                    "name": "page",
                    "in": "query",
                    "schema": {"type": "integer", "minimum": 1},
                }
            )
        for name in ["pk", "source"]:
            if "{" + name + "}" in path:
                kind = (
                    "integer"
                    if path.startswith("/inspections/") and name == "pk"
                    else "string"
                )
                op["parameters"].append(
                    {
                        "name": name,
                        "in": "path",
                        "required": True,
                        "schema": {"type": kind},
                    }
                )
        paths.setdefault(path, {})[method] = op

    route(
        "/auth/login/",
        "post",
        "Sign in and issue a local API token",
        dict(session, properties=dict(session["properties"], token={"type": "string"})),
        ref("LoginInput"),
        public=True,
    )
    route("/auth/me/", "get", "Current account and permissions", session)
    route("/auth/logout/", "post", "Revoke the current account token", code=204)
    route(
        "/permission-groups/",
        "get",
        "Predefined Mandi groups and their explicit permissions; requires auth.view_group",
        array(
            {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "permissions": array({"type": "string"}),
                },
            }
        ),
    )
    route(
        "/employees/", "get", "List employees", page(ref("UserSerializer")), query=True
    )
    route(
        "/employees/",
        "post",
        "Create employee without granting permissions",
        ref("UserSerializer"),
        ref("EmployeeInput"),
        code=201,
    )
    route(
        "/establishments/",
        "get",
        "Search establishment registry",
        page(ref("EstablishmentSerializer")),
        query=True,
    )
    route(
        "/establishments/",
        "post",
        "Create establishment",
        ref("EstablishmentSerializer"),
        ref("EstablishmentSerializer"),
        code=201,
    )
    route(
        "/establishments/{pk}/",
        "get",
        "Establishment details and separate source links",
        ref("EstablishmentSerializer"),
    )
    patch_schema = mapper.map_serializer(api.EstablishmentSerializer())
    patch_schema.pop("required", None)
    route(
        "/establishments/{pk}/",
        "patch",
        "Update establishment",
        ref("EstablishmentSerializer"),
        patch_schema,
    )
    route(
        "/establishments/{pk}/sources/{source}/",
        "post",
        "Manually connect or correct a source link",
        ref("SourceLinkSerializer"),
        {
            "type": "object",
            "required": ["external_id"],
            "properties": {"external_id": {"type": "string"}},
        },
    )
    route(
        "/establishments/{pk}/sources/{source}/",
        "delete",
        "Disconnect a source link and record history",
        code=204,
    )
    route(
        "/sources/{source}/",
        "get",
        "Search demonstration source records",
        {"type": "object"},
        query=True,
    )
    route(
        "/inspections/",
        "get",
        "Filter inspection visits",
        page(ref("InspectionSerializer")),
        query=True,
    )
    route(
        "/inspections/{pk}/",
        "get",
        "Inspection summary, team, and approval",
        ref("InspectionSerializer"),
    )
    route(
        "/inspections/{pk}/approve/",
        "post",
        "Approve inspection; requires approve_inspection permission",
        ref("InspectionSerializer"),
    )
    route(
        "/integrations/ingest/",
        "post",
        "Idempotent normalized provider ingestion; changed results reset approval",
        ref("InspectionSerializer"),
        ref("IngestInput"),
    )
    route(
        "/integrations/establishment-choices/",
        "get",
        "Establishment choices by kind: stable ID in name, readable label",
        array(
            {
                "type": "object",
                "properties": {"name": {"type": "string"}, "label": {"type": "string"}},
            }
        ),
        query=True,
    )
    route(
        "/checklists/",
        "get",
        "Available checklist versions",
        array(ref("ChecklistSerializer")),
    )
    route(
        "/checklists/",
        "post",
        "Create a checklist with an XLSForm upload",
        ref("ChecklistSerializer"),
        ref("ChecklistSerializer"),
        code=201,
    )
    route(
        "/checklists/{pk}/",
        "patch",
        "Update a checklist or replace its XLSForm",
        ref("ChecklistSerializer"),
        ref("ChecklistSerializer"),
    )
    route(
        "/checklists/{pk}/deploy/",
        "post",
        "Upload and deploy the checklist XLSForm to KoBo",
        ref("ChecklistSerializer"),
    )
    route(
        "/reports/coverage/",
        "get",
        "Distinct establishment coverage and approval counts",
        {
            "type": "object",
            "properties": {
                k: {"type": "number"}
                for k in [
                    "establishments",
                    "inspected",
                    "uninspected",
                    "visits",
                    "approved",
                    "unapproved",
                    "coverage_percent",
                ]
            },
        },
        query=True,
    )
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Mandi review API",
            "version": "0.1.0",
            "description": "Local review milestone. Live providers and final approval policies are pending.",
        },
        "servers": [{"url": "/api/v1"}],
        "components": {
            "securitySchemes": {
                "tokenAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "Authorization",
                    "description": "Token <token returned by login>",
                }
            },
            "schemas": schemas,
        },
        "paths": paths,
    }


class Schema(APIView):
    def get(self, request):
        return Response(openapi_document())
