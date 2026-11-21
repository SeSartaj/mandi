"""ODK Central project management, proxied through Mandi."""

from rest_framework.exceptions import ValidationError

from apps.accounts.services import require

from . import odk
from .providers import CollectionError


def _project(value):
    return {
        "id": int(value["id"]),
        "name": value.get("name") or "",
        "description": value.get("description") or "",
        "archived": bool(value.get("archived")),
    }


def _message(exc):
    response = getattr(exc.__cause__, "response", None)
    if response is not None and response.status_code == 403:
        return (
            "ODK Central refused the request (403). Creating projects requires the "
            "Mandi service account to be a Central Administrator; renaming or "
            "archiving requires at least Project Manager."
        )
    return str(exc)


def list_projects(actor):
    require(actor, "inspections.deploy_checklist")
    try:
        return [_project(item) for item in odk.list_projects()]
    except CollectionError as exc:
        raise ValidationError({"collection": _message(exc)}) from exc


def create_project(actor, name):
    require(actor, "inspections.deploy_checklist")
    name = (name or "").strip()
    if not name:
        raise ValidationError({"name": "Enter a project name."})
    try:
        return _project(odk.create_project(name))
    except CollectionError as exc:
        raise ValidationError({"collection": _message(exc)}) from exc


def update_project(actor, project_id, name=None, archived=None):
    require(actor, "inspections.deploy_checklist")
    payload = {}
    if name is not None:
        name = name.strip()
        if not name:
            raise ValidationError({"name": "Enter a project name."})
        payload["name"] = name
    if archived is not None:
        payload["archived"] = bool(archived)
    if not payload:
        raise ValidationError("Nothing to update.")
    try:
        return _project(odk.update_project(project_id, payload))
    except CollectionError as exc:
        raise ValidationError({"collection": _message(exc)}) from exc
