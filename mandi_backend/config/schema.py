"""OpenAPI contract using the same input/output serializers as the REST layer."""

from rest_framework.response import Response
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.views import APIView

from . import api
from .api.serializers import EmployeeUpdate


def openapi_document():
    mapper = AutoSchema()
    classes = [
        api.LoginInput,
        api.EmployeeInput,
        EmployeeUpdate,
        api.UserSerializer,
        api.EstablishmentSerializer,
        api.SourceLinkSerializer,
        api.ChecklistSerializer,
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
        params=None,
    ):
        op = {
            "summary": description,
            "responses": {str(code): {"description": "Success"}},
            "parameters": [],
            "security": [] if public else [{"tokenAuth": []}],
        }
        if params:
            for name in params:
                op["parameters"].append(
                    {"name": name, "in": "query", "schema": {"type": "string"}}
                )
            op["parameters"].append(
                {
                    "name": "page",
                    "in": "query",
                    "schema": {"type": "integer", "minimum": 1},
                }
            )
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
                op["parameters"].append(
                    {
                        "name": name,
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                )
        paths.setdefault(path, {})[method] = op

    route("/registry/sync/", "get", "Automatic registry sync status and per-category progress", {"type": "object"})
    route("/registry/", "get", "Active establishment types and external systems", {"type": "object"})
    route("/registry/import/", "post", "Import an identity from its primary registry (idempotent by source and external ID)", ref("EstablishmentSerializer"),
          {"type": "object", "required": ["source", "external_id", "kind"], "properties": {key: {"type": "string"} for key in ["source", "external_id", "kind"]}}, code=201)
    route("/establishments/{pk}/refresh/", "post", "Refresh primary registry identity; local copy survives outages", ref("EstablishmentSerializer"))
    route("/establishments/{pk}/ownership/", "post", "Transfer identity ownership (null source means Mandi)", ref("EstablishmentSerializer"),
          {"type": "object", "required": ["source"], "properties": {"source": {"type": "string", "nullable": True}}})
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
        "Search external source records",
        {"type": "object"},
        query=True,
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
        "/checklists/{pk}/",
        "get",
        "One checklist with its submission count",
        ref("ChecklistSerializer"),
    )
    route(
        "/checklists/{pk}/collection-submissions/",
        "get",
        "Submissions of one checklist; filter by search, establishment or date",
        page({"type": "object"}),
        params=["search", "establishment_id", "date_from", "date_to", "page_size"],
    )
    route(
        "/checklists/{pk}/versions/",
        "get",
        "Published form versions of a checklist's deployed form",
        array(
            {
                "type": "object",
                "properties": {
                    "version": {"type": "string"},
                    "published_at": {"type": "string", "nullable": True},
                },
            }
        ),
    )
    route(
        "/submissions/",
        "get",
        "All submissions filtered by establishment type, establishment or checklist",
        page({"type": "object"}),
        params=[
            "search",
            "establishment_kind",
            "establishment_id",
            "checklist_id",
            "date_from",
            "date_to",
            "page_size",
        ],
    )
    route(
        "/checklists/{pk}/deploy/",
        "post",
        "Upload and deploy the checklist XLSForm to the configured collection provider",
        ref("ChecklistSerializer"),
    )
    route(
        "/collection-submissions/{pk}/",
        "get",
        "One collection submission with scores, typed answers and attachments",
        {"type": "object"},
    )
    route(
        "/integrations/establishments.csv",
        "get",
        "CSV of Mandi establishments for an XLSForm select_one_from_file question",
        {"type": "string", "format": "binary"},
    )
    route(
        "/employees/{pk}/",
        "patch",
        "Update employee profile, password, groups, or checklist access",
        ref("UserSerializer"),
        ref("EmployeeUpdate"),
    )
    route(
        "/employees/{pk}/collection-access/",
        "get",
        "List active collector grants",
        array({"type": "object"}),
    )
    route(
        "/employees/{pk}/collection-access/",
        "post",
        "Provision one form credential; configuration is returned once",
        {"type": "object"},
        {
            "type": "object",
            "required": ["checklist_id"],
            "properties": {"checklist_id": {"type": "integer"}},
        },
        code=201,
    )
    route(
        "/employees/{pk}/collection-access/",
        "delete",
        "Revoke remote collector credential before disabling local access",
        body={
            "type": "object",
            "required": ["grant_id"],
            "properties": {"grant_id": {"type": "integer"}},
        },
        code=204,
    )
    route(
        "/integrations/collection/sync/",
        "post",
        "Import provider submissions into the local submissions list",
        {"type": "object"},
        {"type": "object", "properties": {"checklist_id": {"type": "integer"}}},
    )
    route(
        "/checklists/{pk}/collection-submissions/",
        "get",
        "Provider-neutral checklist submissions",
        page({"type": "object"}),
        query=True,
    )
    route(
        "/establishments/{pk}/collection-submissions/",
        "get",
        "Provider-neutral establishment submissions",
        page({"type": "object"}),
    )
    route(
        "/collection-submissions/{pk}/",
        "get",
        "Submission answers, scores, and protected attachment references",
        {"type": "object"},
    )
    route(
        "/collection-submissions/{pk}/attachments/{index}/",
        "get",
        "Stream an authorized collection attachment",
    )
    route(
        "/checklists/{pk}/download/",
        "get",
        "Download original XLSForm with checklist authorization",
    )
    route(
        "/integrations/establishments.csv",
        "get",
        "Download establishment choices for XLSForms",
    )
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Mandi API",
            "version": "0.1.0",
            "description": "Mandi records, account management, XLSForm deployment, and provider-neutral collection workflows.",
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
