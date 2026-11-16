"""ODK Central HTTP adapter. No access to Central's database or Docker runtime."""

from urllib.parse import quote, urljoin, urlsplit

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime

from .providers import CollectionError, RemoteSubmission


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

    def deploy(self, deployment, content, establishments_csv):
        base = form_path(deployment.project_id, deployment.form_id)
        # Probe first: never interpret auth/network/server errors as 'form missing'.
        try:
            request("GET", base)
        except CollectionError as exc:
            if (
                not isinstance(exc.__cause__, requests.HTTPError)
                or exc.__cause__.response.status_code != 404
            ):
                raise
            request(
                "POST",
                f"projects/{deployment.project_id}/forms",
                params={"publish": "false"},
                data=content,
                headers={
                    "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                },
            )
        else:
            request(
                "POST",
                base + "/draft",
                data=content,
                headers={
                    "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                },
            )
        attachments = request("GET", base + "/draft/attachments").json()
        if any(item["name"] == "establishments.csv" for item in attachments):
            request(
                "POST",
                base + "/draft/attachments/establishments.csv",
                data=establishments_csv,
                headers={"Content-Type": "text/csv"},
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
            inspector_id=str(metadata["submitterId"])
            if metadata.get("submitterId") is not None
            else None,
            inspected_on=data.get("inspected_on") or timestamp[:10],
            inspection_kind=data.get("inspection_kind") or "comprehensive",
            data=data,
        )

    def provision_collector(self, deployment, display_name):
        root = f"projects/{deployment.project_id}"
        user = request(
            "POST", root + "/app-users", json={"displayName": display_name}
        ).json()
        try:
            request(
                "POST",
                form_path(deployment.project_id, deployment.form_id)
                + f"/assignments/app-user/{user['id']}",
            )
        except CollectionError:
            request("DELETE", root + f"/app-users/{user['id']}")
            raise
        return {
            "id": str(user["id"]),
            "configuration": {
                "server_url": f"{settings.ODK_PUBLIC_URL.rstrip('/')}/v1/key/{quote(user['token'], safe='')}/projects/{deployment.project_id}",
                "message": "Save this ODK Collect server URL now. Mandi does not store the token.",
            },
        }

    def revoke_collector(self, grant):
        try:
            request(
                "DELETE",
                f"projects/{grant.deployment.project_id}/app-users/{grant.remote_id}",
            )
        except CollectionError as exc:
            # External administrators may already have removed this credential.
            if (
                not isinstance(exc.__cause__, requests.HTTPError)
                or exc.__cause__.response.status_code != 404
            ):
                raise
