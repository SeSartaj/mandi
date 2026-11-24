"""ODK Central HTTP adapter. No access to Central's database or Docker runtime."""

import io
import json
import zlib
from base64 import b64encode
from urllib.parse import quote, urljoin, urlsplit

import requests
import segno
from django.conf import settings
from django.utils.dateparse import parse_datetime

from .providers import CollectionError, RemoteSubmission


def build_settings_qr(server_url, project_name="Mandi"):
    """Build an ODK Collect settings QR (zlib + base64 JSON, per Collect docs)."""
    payload = {
        "general": {
            "server_url": server_url,
            # Collect downloads the newest published version at project open and
            # checks again periodically, so no manual "Get Blank Form" is needed.
            "form_update_mode": "previously_downloaded",
            "periodic_form_updates_check": "every_fifteen_minutes",
        },
        "admin": {},
        "project": {"name": project_name, "icon": "M", "color": "#005a5a"},
    }
    encoded = b64encode(zlib.compress(json.dumps(payload).encode("utf-8")))
    buffer = io.BytesIO()
    segno.make(encoded, micro=False).save(buffer, kind="png", scale=6, border=2)
    return "data:image/png;base64," + b64encode(buffer.getvalue()).decode()


def request(method, path, **kwargs):
    if not settings.ODK_EMAIL or not settings.ODK_PASSWORD:
        raise CollectionError(
            "Configure ODK_EMAIL and ODK_PASSWORD for the Mandi service account."
        )
    url = settings.ODK_BASE_URL.rstrip("/") + "/v1/" + path.lstrip("/")
    headers = {"X-Forwarded-Proto": "https", **(kwargs.pop("headers", None) or {})}
    try:
        response = requests.request(
            method,
            url,
            auth=(settings.ODK_EMAIL, settings.ODK_PASSWORD),
            timeout=settings.ODK_TIMEOUT,
            allow_redirects=False,
            headers=headers,
            **kwargs,
        )
        response.raise_for_status()
        if response.is_redirect:
            raise CollectionError("Central returned a redirect. Check ODK_BASE_URL.")
        return response
    except requests.RequestException as exc:
        # Never echo URLs, response bodies, or credentials into API errors.
        status = exc.response.status_code if exc.response is not None else "unreachable"
        raise CollectionError(
            f"Central request failed ({status}). Check connectivity and service account permissions."
        ) from exc


def form_path(project, form_id):
    return f"projects/{int(project)}/forms/{quote(str(form_id), safe='')}"

def list_projects():
    return request("GET", "projects").json()


def create_project(name):
    return request("POST", "projects", json={"name": name}).json()


def update_project(project_id, payload):
    return request("PATCH", f"projects/{int(project_id)}", json=payload).json()


class OdkProvider:
    name = "odk"

    def form_url(self, deployment):
        if not settings.ODK_PUBLIC_URL:
            return None
        return f"{settings.ODK_PUBLIC_URL.rstrip('/')}/projects/{deployment.project_id}/forms/{quote(deployment.form_id, safe='')}"

    def open_attachment(self, deployment, submission_id, filename):
        path = (
            form_path(deployment.project_id, deployment.form_id)
            + "/submissions/"
            + quote(submission_id, safe="")
            + "/attachments/"
            + quote(filename, safe="")
        )
        return request("GET", path, stream=True)

    @staticmethod
    def _response(exc):
        cause = exc.__cause__
        return getattr(cause, "response", None)

    @classmethod
    def _missing(cls, exc):
        response = cls._response(exc)
        return response is not None and response.status_code == 404

    @classmethod
    def _structure_warning(cls, exc):
        response = cls._response(exc)
        if response is None or response.status_code != 400:
            return False
        try:
            return (response.json() or {}).get("code") == 400.16
        except ValueError:
            return False

    @classmethod
    def _structure_fields(cls, exc):
        response = cls._response(exc)
        try:
            body = response.json() if response is not None else {}
        except ValueError:
            body = {}
        details = body.get("details") if isinstance(body, dict) else None
        fields = (details or {}).get("fields") if isinstance(details, dict) else None
        return [str(item) for item in fields or []]

    @classmethod
    def _structure_error(cls, exc):
        fields = cls._structure_fields(exc)
        changed = ", ".join(fields) if fields else "one or more questions or choice lists"
        return CollectionError(
            "The form's structure differs from the version already published in "
            f"ODK Central ({changed}). Mandi will not overwrite the structure "
            "silently because existing submissions could become unreadable. "
            "Hint: keep existing question names, types and choice lists unchanged; "
            "publish structural changes as a new checklist with a new code so it "
            "gets its own form."
        )

    def deploy(self, deployment, content, force=False, dataset=None):
        base = form_path(deployment.project_id, deployment.form_id)
        headers = {
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }

        def upload(path, **kwargs):
            try:
                return request("POST", path, **kwargs)
            except CollectionError as exc:
                if not self._structure_warning(exc):
                    raise
                if not force:
                    error = self._structure_error(exc)
                    error.structure_conflict = True
                    raise error from exc
                # Explicit operator confirmation: publish the structural change.
                params = dict(kwargs.get("params") or {})
                params["ignoreWarnings"] = "true"
                kwargs["params"] = params
                return request("POST", path, **kwargs)

        # Probe first: never interpret auth/network/server errors as 'form missing'.
        try:
            request("GET", base)
        except CollectionError as exc:
            if not self._missing(exc):
                raise
            upload(
                f"projects/{deployment.project_id}/forms",
                params={"publish": "false"},
                data=content,
                headers=headers,
            )
        else:
            upload(base + "/draft", data=content, headers=headers)
        attachments = request("GET", base + "/draft/attachments").json()
        if dataset and any(
            item["name"] == "establishments.csv" for item in attachments
        ):
            request(
                "PATCH",
                base + "/draft/attachments/establishments.csv",
                json={"dataset": dataset},
            )
        request("POST", base + "/draft/publish")

    def submissions(self, deployment):
        path = (
            form_path(deployment.project_id, deployment.form_id)
            + ".svc/Submissions?$top=250"
        )
        seen = set()
        while path:
            if path in seen:
                raise CollectionError("Central returned a repeated pagination link.")
            seen.add(path)
            payload = request("GET", path).json()
            for data in payload["value"]:
                identity = data.get("__id")
                if identity:
                    attachments = request(
                        "GET",
                        form_path(deployment.project_id, deployment.form_id)
                        + "/submissions/"
                        + quote(identity, safe="")
                        + "/attachments",
                    ).json()
                    data["_attachments"] = [
                        {"filename": item["name"]}
                        for item in attachments
                        if item.get("exists", True)
                    ]
                yield self.normalize(data)
            link = payload.get("@odata.nextLink")
            if not link:
                return
            base = settings.ODK_BASE_URL.rstrip("/") + "/v1/" + path
            resolved = urlsplit(urljoin(base, link))
            expected = urlsplit(settings.ODK_BASE_URL)
            if (resolved.scheme, resolved.netloc) != (
                expected.scheme,
                expected.netloc,
            ) or not resolved.path.startswith("/v1/"):
                raise CollectionError("Central returned an unsafe pagination link.")
            path = resolved.path[4:] + ("?" + resolved.query if resolved.query else "")

    @staticmethod
    def normalize(data):
        metadata = data.get("__system") or {}
        timestamp = metadata.get("submissionDate") or ""
        return RemoteSubmission(
            submission_id=data.get("__id") or "",
            establishment_id=data.get("establishment_id") or "",
            submitted_at=parse_datetime(timestamp),
            form_version=str(metadata.get("formVersion") or ""),
            data=data,
        )

    def form_versions(self, deployment):
        payload = request(
            "GET",
            form_path(deployment.project_id, deployment.form_id) + "/versions",
        ).json()
        items = payload.get("value", []) if isinstance(payload, dict) else payload
        versions = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            version = str(item.get("version") or "")
            if not version:
                continue
            versions.append(
                {"version": version, "published_at": item.get("publishedAt")}
            )
        versions.sort(key=lambda item: item["version"], reverse=True)
        return versions

    def create_collector(self, project_id, display_name):
        user = request(
            "POST",
            f"projects/{int(project_id)}/app-users",
            json={"displayName": display_name},
        ).json()
        return {"id": str(user["id"]), "token": user["token"]}

    def assign_collector(self, deployment, remote_id):
        request(
            "POST",
            form_path(deployment.project_id, deployment.form_id)
            + f"/assignments/app-user/{quote(str(remote_id), safe='')}",
        )

    def unassign_collector(self, deployment, remote_id):
        try:
            request(
                "DELETE",
                form_path(deployment.project_id, deployment.form_id)
                + f"/assignments/app-user/{quote(str(remote_id), safe='')}",
            )
        except CollectionError as exc:
            if not self._missing(exc):
                raise

    def delete_collector(self, project_id, remote_id):
        try:
            request(
                "DELETE",
                f"projects/{int(project_id)}/app-users/"
                f"{quote(str(remote_id), safe='')}",
            )
        except CollectionError as exc:
            # External administrators may already have removed this credential.
            if not self._missing(exc):
                raise

    def collector_configuration(self, project_id, token):
        project_id = str(int(project_id))
        try:
            project_name = (
                request("GET", f"projects/{project_id}").json().get("name")
                or f"Mandi project {project_id}"
            )
        except CollectionError:
            project_name = f"Mandi project {project_id}"
        server_url = f"{settings.ODK_PUBLIC_URL.rstrip('/')}/v1/key/{quote(token, safe='')}/projects/{project_id}"
        return {
            "server_url": server_url,
            "qr": build_settings_qr(server_url, project_name),
            "message": "Scan this QR in ODK Collect, or save the server URL. Mandi does not store the token.",
        }
