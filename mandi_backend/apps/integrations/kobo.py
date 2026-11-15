from io import BytesIO
from pathlib import Path
import json
import time
from urllib.parse import urlparse

import requests
from django.conf import settings

from .xlsform import XlsFormError, add_establishment_question, set_form_title


class KoboError(Exception):
    """Raised when KoBo rejects a request or cannot be reached."""


def _headers():
    if not settings.KOBO_API_TOKEN:
        raise KoboError(
            "KoBo API token is not configured. Set KOBO_API_TOKEN in the backend environment."
        )
    headers = {"Authorization": f"Token {settings.KOBO_API_TOKEN}"}
    if settings.KOBO_HOST_HEADER:
        headers["Host"] = settings.KOBO_HOST_HEADER
    return headers


def _url(path):
    return f"{settings.KOBO_BASE_URL.rstrip('/')}{path}"


def _error_message(response):
    try:
        payload = response.json()
    except ValueError:
        payload = response.text[:500]
    if isinstance(payload, dict):
        for key in ("detail", "error", "non_field_errors"):
            if key in payload:
                value = payload[key]
                if isinstance(value, list):
                    value = "; ".join(str(item) for item in value)
                return f"KoBo returned HTTP {response.status_code}: {value}"
    return f"KoBo returned HTTP {response.status_code}: {payload}"


def _request(method, path, **kwargs):
    try:
        response = requests.request(
            method,
            _url(path),
            headers=_headers(),
            verify=settings.KOBO_VERIFY_TLS,
            timeout=settings.KOBO_TIMEOUT,
            **kwargs,
        )
    except requests.RequestException as exc:
        raise KoboError(f"Cannot reach KoBo: {exc}") from exc
    if not response.ok:
        raise KoboError(_error_message(response))
    return response


def _public_asset_url(asset_uid):
    host = settings.KOBO_HOST_HEADER or settings.KOBO_BASE_URL
    if "://" not in host:
        host = f"http://{host}"
    return f"{host.rstrip('/')}/api/v2/assets/{asset_uid}/"


def get_asset(asset_uid):
    try:
        return _request("GET", f"/api/v2/assets/{asset_uid}/").json()
    except KoboError as exc:
        if "HTTP 404" in str(exc):
            return None
        raise


def import_xlsform(file_handle, filename, name, destination=None):
    data = {
        "name": name,
        "library": "false",
        "desired_type": "survey",
    }
    if destination:
        data["destination"] = destination
    response = _request(
        "POST",
        "/api/v2/imports/",
        data=data,
        files={"file": (filename, file_handle)},
    )
    import_uid = response.json()["uid"]
    deadline = time.monotonic() + settings.KOBO_POLL_TIMEOUT

    while time.monotonic() < deadline:
        result = _request("GET", f"/api/v2/imports/{import_uid}/").json()
        status = result.get("status")
        if status == "failed":
            raise KoboError(f"KoBo import failed: {result.get('messages', {})}")
        if status == "complete":
            messages = result.get("messages", {})
            created = messages.get("created") or messages.get("updated") or []
            if not created:
                raise KoboError(
                    f"KoBo import completed without an asset: {messages}"
                )
            return created[0]["uid"]
        time.sleep(settings.KOBO_POLL_INTERVAL)

    raise KoboError("KoBo import timed out before the form could be prepared.")


def deploy_asset(asset):
    asset_uid = asset["uid"]
    if asset.get("has_deployment"):
        payload = {
            "active": True,
            "version_id": asset["version_id"],
        }
        _request(
            "PATCH",
            f"/api/v2/assets/{asset_uid}/deployment/",
            json=payload,
        )
    else:
        _request(
            "POST",
            f"/api/v2/assets/{asset_uid}/deployment/",
            json={"active": True},
        )
    return get_asset(asset_uid)


def replace_form_media(asset_uid, filename, content, description):
    """Replace a form media file (e.g. establishments.csv) on an asset."""
    files = _request("GET", f"/api/v2/assets/{asset_uid}/files/").json()
    for item in files.get("results", []):
        if (
            item.get("file_type") == "form_media"
            and item.get("description") == description
        ):
            _request(
                "DELETE",
                f"/api/v2/assets/{asset_uid}/files/{item['uid']}/",
            )
    _request(
        "POST",
        f"/api/v2/assets/{asset_uid}/files/",
        data={
            "file_type": "form_media",
            "description": description,
            "metadata": json.dumps({"filename": filename}),
        },
        files={"content": (filename, content, "text/csv")},
    )


def fetch_submissions(asset_uid):
    """Return all JSON submissions for an asset, following KoBo pagination."""
    submissions = []
    path = f"/api/v2/assets/{asset_uid}/data/?format=json&limit=1000"
    while path:
        payload = _request("GET", path).json()
        submissions.extend(payload.get("results", []))
        next_url = payload.get("next")
        if not next_url:
            break
        parsed = urlparse(next_url)
        path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    return submissions


def _kobo_host():
    host = settings.KOBO_HOST_HEADER or settings.KOBO_BASE_URL
    return (host or "").split("://")[-1].split("/")[0].lower()


def open_attachment(download_url):
    """Stream an uploaded submission attachment from KoBo.

    KoBo returns absolute URLs pointing at the public host, which the backend
    reaches through ``KOBO_BASE_URL`` with the ``Host`` header set, so only the
    path and query are reused.
    """
    if not download_url:
        raise KoboError("This attachment has no KoBo download URL.")
    parsed = urlparse(download_url)
    allowed = {_kobo_host()}
    base_host = urlparse(settings.KOBO_BASE_URL or "").hostname or ""
    allowed.add(base_host.lower())
    if parsed.netloc and parsed.netloc.split(":")[0].lower() not in allowed:
        raise KoboError("Attachment URL is not a KoBo URL.")
    path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    try:
        response = requests.get(
            _url(path),
            headers=_headers(),
            verify=settings.KOBO_VERIFY_TLS,
            timeout=settings.KOBO_TIMEOUT,
            stream=True,
        )
    except requests.RequestException as exc:
        raise KoboError(f"Cannot reach KoBo: {exc}") from exc
    if not response.ok:
        raise KoboError(_error_message(response))
    return response


def deploy_checklist_to_kobo(checklist, establishments_csv=None):
    """Import the checklist XLSForm and deploy it as a KoBo survey."""
    if not checklist.xlsform:
        raise KoboError("Upload an XLSForm before deploying.")

    existing_asset = (
        get_asset(checklist.kobo_asset_uid) if checklist.kobo_asset_uid else None
    )
    filename = Path(checklist.xlsform.name).name

    with checklist.xlsform.open("rb") as file_handle:
        try:
            xlsform_content, xlsform_name = add_establishment_question(
                filename, file_handle.read()
            )
            xlsform_content = set_form_title(xlsform_content, checklist.name)
        except XlsFormError as exc:
            raise KoboError(str(exc)) from exc

    if existing_asset:
        asset_uid = checklist.kobo_asset_uid
        if establishments_csv is not None:
            replace_form_media(
                asset_uid,
                "establishments.csv",
                establishments_csv,
                "establishments.csv",
            )
        asset_uid = import_xlsform(
            BytesIO(xlsform_content),
            xlsform_name,
            checklist.name,
            destination=_public_asset_url(existing_asset["uid"]),
        )
    else:
        asset_uid = import_xlsform(
            BytesIO(xlsform_content),
            xlsform_name,
            checklist.name,
        )
        if establishments_csv is not None:
            replace_form_media(
                asset_uid,
                "establishments.csv",
                establishments_csv,
                "establishments.csv",
            )
        # Re-import now that the external CSV exists so KoBo keeps the
        # select_one_from_file question in the final asset content.
        asset_uid = import_xlsform(
            BytesIO(xlsform_content),
            xlsform_name,
            checklist.name,
            destination=_public_asset_url(asset_uid),
        )

    # Importers can derive the asset name from workbook content. Apply the saved
    # Mandi name after all imports, for both new and existing projects.
    _request("PATCH", f"/api/v2/assets/{asset_uid}/", json={"name": checklist.name})
    asset = get_asset(asset_uid)
    if not asset:
        raise KoboError("KoBo created the import but the asset could not be loaded.")

    deployed_asset = deploy_asset(asset)
    if not deployed_asset or deployed_asset.get("deployment_status") != "deployed":
        raise KoboError(
            f"KoBo did not report a successful deployment: {deployed_asset}"
        )
    return asset_uid, deployed_asset
