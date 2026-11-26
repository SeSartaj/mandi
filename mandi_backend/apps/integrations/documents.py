"""Serve source documents through Mandi.

Licensing and Survey both protect stored files with the same ``X-API-KEY`` header
they use for their JSON API, so a browser cannot open an attachment URL directly.
Mandi therefore replaces every upstream document URL in a source profile with a
short-lived, signed link to this gateway, and the gateway streams the file with
the integration key attached. The key itself never leaves the server.
"""
import re
from urllib.parse import quote, unquote, urljoin, urlsplit

import requests
from django.conf import settings
from django.core import signing
from django.http import StreamingHttpResponse
from django.utils.http import content_disposition_header
from rest_framework.exceptions import (
    APIException,
    NotFound,
    PermissionDenied,
    ValidationError,
)

from apps.accounts.services import require

SALT = "mandi.source-document"
LINK_MAX_AGE = 60 * 60  # one hour, refreshed whenever the profile is reloaded
MAX_BYTES = 40 * 1024 * 1024
CHUNK = 64 * 1024

_CONNECTIONS = {
    "licensing": (
        "LICENSING_BASE_URL",
        "LICENSING_REGISTRATION_API_KEY",
        "LICENSING_TIMEOUT",
    ),
    "survey": ("SURVEY_BASE_URL", "SURVEY_REGISTRATION_API_KEY", "SURVEY_TIMEOUT"),
}


class DocumentError(APIException):
    status_code = 502
    default_detail = "Mandi could not load this document from the source system."


def configured(source):
    """The source's base URL when both it and its integration key are set."""
    names = _CONNECTIONS.get(source)
    if not names:
        return None
    base = str(getattr(settings, names[0], "") or "").rstrip("/")
    key = getattr(settings, names[1], "") or ""
    return base if base and key else None


def _connection(source):
    names = _CONNECTIONS.get(source)
    if not names:
        raise ValidationError({"source": "This source does not provide documents."})
    base = configured(source)
    if not base:
        raise DocumentError("This source is not configured in Mandi.")
    key = getattr(settings, names[1], "") or ""
    timeout = getattr(settings, names[2], None) or 30
    return base, key, timeout


def _is_source_url(base, url):
    origin, parts = urlsplit(base), urlsplit(url)
    if parts.scheme not in ("http", "https") or parts.username or parts.password:
        return False
    if (parts.scheme, parts.netloc) != (origin.scheme, origin.netloc):
        return False
    root = origin.path.rstrip("/")
    return not root or parts.path == root or parts.path.startswith(root + "/")


def _owner(url):
    """Which configured source serves this absolute URL, if any."""
    for code in _CONNECTIONS:
        base = configured(code)
        if base and _is_source_url(base, url):
            return code
    return None


def _resolve(value, fallback):
    """Return ``(source, absolute URL)`` for a stored document value."""
    text = str(value or "").strip()
    if not text:
        return None, None
    if "://" in text:
        owner = _owner(text)
        return (owner, text) if owner else (None, None)
    # Only path-like values are documents; plain words such as "Shop" are data.
    if not (text.startswith("/") or text.lower().startswith("media/")):
        return None, None
    base = configured(fallback or "")
    if not base:
        return None, None
    candidate = urljoin(base + "/", text.lstrip("/"))
    return (fallback, candidate) if _is_source_url(base, candidate) else (None, None)


def proxy_path(source, url):
    """A signed Mandi URL for one upstream document, relative to the API root."""
    token = signing.dumps({"source": source, "url": url}, salt=SALT, compress=True)
    return f"sources/{quote(source, safe='')}/document/?token={quote(token, safe='')}"


def _rewrite_value(value, fallback):
    if isinstance(value, list):
        return [_rewrite_value(item, fallback) for item in value]
    if isinstance(value, tuple):
        return [_rewrite_value(item, fallback) for item in value]
    if not isinstance(value, str):
        return value
    source, url = _resolve(value, fallback)
    return proxy_path(source, url) if source else value


def rewrite(detail, fallback):
    """Replace upstream document URLs in a source profile with signed Mandi links."""
    if not isinstance(detail, dict):
        return detail
    for section in detail.get("sections") or []:
        for field in section.get("fields") or []:
            if isinstance(field, dict) and "value" in field:
                field["value"] = _rewrite_value(field.get("value"), fallback)
    return detail


def from_token(token):
    """Validate a signed document link and return ``(source, url)``."""
    try:
        payload = signing.loads(token, salt=SALT, max_age=LINK_MAX_AGE)
    except signing.SignatureExpired as exc:
        raise PermissionDenied(
            "This document link expired. Reload the establishment and open it again."
        ) from exc
    except signing.BadSignature as exc:
        raise PermissionDenied("This document link is not valid.") from exc
    source = payload.get("source") if isinstance(payload, dict) else None
    url = payload.get("url") if isinstance(payload, dict) else None
    if source not in _CONNECTIONS or not isinstance(url, str) or not url:
        raise PermissionDenied("This document link is not valid.")
    return source, url


def _absolute(base, url):
    target = urljoin(base + "/", str(url or "").strip())
    if not _is_source_url(base, target):
        raise PermissionDenied(
            "Mandi only opens documents hosted by the linked source system."
        )
    return target


def _open(base, key, timeout, url):
    target = _absolute(base, url)
    for _ in range(4):
        try:
            response = requests.get(
                target,
                headers={"X-API-KEY": key},
                timeout=timeout,
                stream=True,
                allow_redirects=False,
            )
        except requests.Timeout as exc:
            raise DocumentError(
                "The source system timed out while loading this document."
            ) from exc
        except requests.RequestException as exc:
            raise DocumentError(
                "Mandi could not reach the source system for this document."
            ) from exc
        if not response.is_redirect:
            break
        location = response.headers.get("Location")
        response.close()
        if not location:
            raise DocumentError(
                "The source system redirected this document without a target."
            )
        target = _absolute(base, urljoin(target, location))
    else:
        raise DocumentError("The source system redirected this document too many times.")
    if response.status_code in (401, 403):
        response.close()
        raise DocumentError(
            "The source system rejected Mandi's integration key for this document."
        )
    if response.status_code == 404:
        response.close()
        raise NotFound("This document no longer exists in the source system.")
    if response.status_code != 200:
        response.close()
        raise DocumentError(
            "The source system returned an unexpected response for this document."
        )
    return response


def _filename(upstream, url):
    header = upstream.headers.get("Content-Disposition") or ""
    match = re.search(r"filename\*=UTF-8''([^;]+)", header, re.IGNORECASE)
    if match:
        return unquote(match.group(1)).strip()
    match = re.search(r'filename="?([^";]+)"?', header, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return unquote(urlsplit(url).path.rsplit("/", 1)[-1]).strip() or "document"


def _chunks(upstream):
    try:
        sent = 0
        while True:
            chunk = upstream.raw.read(CHUNK, decode_content=True)
            if not chunk:
                break
            sent += len(chunk)
            if sent > MAX_BYTES:
                raise DocumentError("This document is too large to open in Mandi.")
            yield chunk
    finally:
        upstream.close()


def response(source, url):
    """Stream one document from ``source`` back to the browser."""
    base, key, timeout = _connection(source)
    upstream = _open(base, key, timeout, url)
    length = upstream.headers.get("Content-Length")
    try:
        size = int(length) if length else None
    except (TypeError, ValueError):
        size = None
    if size is not None and size > MAX_BYTES:
        upstream.close()
        raise DocumentError("This document is too large to open in Mandi.")
    result = StreamingHttpResponse(
        _chunks(upstream),
        content_type=upstream.headers.get("Content-Type") or "application/octet-stream",
    )
    result["Content-Disposition"] = content_disposition_header(
        False, _filename(upstream, url) or "document"
    )
    result["X-Content-Type-Options"] = "nosniff"
    result["Cache-Control"] = "private, no-store"
    if size is not None:
        result["Content-Length"] = str(size)
    return result


def require_viewer(actor):
    """Permission check for the authenticated (non-signed) download path."""
    require(actor, "establishments.view_sourcelink")
