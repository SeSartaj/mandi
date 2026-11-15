"""Server-only Licensing API client and minimal Mandi source projections."""
from urllib.parse import quote

import requests
from django.conf import settings
from rest_framework.exceptions import APIException, NotFound, ValidationError

CATEGORIES = {"company", "factory", "pharmacy", "wholesale"}
KIND_CATEGORIES = {"importer": "company", "factory": "factory", "pharmacy": "pharmacy", "wholesaler": "wholesale"}
FILTERS = {"name", "application_id", "address_province_name_en", "address_district_name_en", "application_step", "application_type", "application_status", "search", "ordering", "page", "page_size", "paginate"}


class LicensingError(APIException):
    status_code = 502
    default_detail = "The Licensing service is unavailable."


def configured():
    return bool(settings.LICENSING_BASE_URL and settings.LICENSING_REGISTRATION_API_KEY)


def _request(category, suffix, params=None):
    if category not in CATEGORIES:
        raise ValidationError({"category": "Unknown Licensing application category."})
    if not configured():
        raise LicensingError("The Licensing connection is not configured.")
    url = f"{settings.LICENSING_BASE_URL.rstrip('/')}/api/applications/{category}/registration/{suffix}"
    try:
        response = requests.get(url, params=params, headers={
            "X-API-KEY": settings.LICENSING_REGISTRATION_API_KEY,
            "Accept": "application/json",
        }, timeout=settings.LICENSING_TIMEOUT, allow_redirects=False)
    except requests.Timeout as exc:
        raise LicensingError("The Licensing service timed out. Try again.") from exc
    except requests.RequestException as exc:
        raise LicensingError("Could not connect to the Licensing service.") from exc
    try:
        if response.status_code == 404:
            raise NotFound("Licensing application not found.")
        if response.status_code in (401, 403):
            raise LicensingError("Licensing rejected the server credentials. Check the server configuration.")
        if response.status_code == 400:
            raise ValidationError("Licensing rejected the search filters.")
        if response.status_code != 200:
            raise LicensingError("The Licensing service returned an unexpected response.")
        try:
            return response.json()
        except ValueError as exc:
            raise LicensingError("The Licensing service returned invalid JSON.") from exc
    finally:
        response.close()


def list_applications(category, filters=None):
    params = {key: value for key, value in (filters or {}).items() if key in FILTERS}
    params.setdefault("page_size", 20)
    payload = _request(category, "list/", params)
    if not isinstance(payload, (dict, list)) or (isinstance(payload, dict) and not isinstance(payload.get("results"), list)):
        raise LicensingError("The Licensing service returned an invalid list.")
    return payload


def get_application(category, application_id):
    if not application_id or str(application_id) in {".", ".."}:
        raise ValidationError({"application_id": "An application ID is required."})
    payload = _request(category, f"{quote(str(application_id), safe='')}/")
    if not isinstance(payload, dict) or not payload.get("application_id"):
        raise LicensingError("The Licensing service returned an invalid application.")
    return payload


def candidate(category, record):
    """Only business identity/location are exposed or saved in source links."""
    application_id = str(record.get("application_id") or "")
    if not application_id:
        raise LicensingError("A Licensing record has no application ID.")
    address = record.get("address") or {}
    province = address.get("province") or {}
    details = {
        "category": category,
        "application_id": application_id,
        "name": record.get("name") or record.get("name_en") or application_id,
        "name_en": record.get("name_en") or "",
        "province": province.get("name_fa") or province.get("name_en") or "",
        "license_number": record.get("aisa_license_number") or "",
    }
    if "application_status" in record:
        details["status"] = record.get("application_status") or ""
    return {"id": f"{category}:{application_id}", "name": details["name"], "details": details, "is_demo": False}


def application_details(category, record):
    """Explicit detail-page projection; identity documents and raw payloads stay upstream."""
    def fields(data, keys):
        return [{"label": label, "value": data.get(key)} for key, label in keys
                if isinstance(data.get(key), (str, int, float, bool)) and data.get(key) != ""]

    sections = [{"title": "Application details", "fields": fields(record, [
        ("name", "Name"), ("name_en", "English name"), ("application_id", "Application ID"),
        ("application_status", "Application status"), ("application_step", "Application step"),
        ("application_type", "Application type"), ("register_type", "Registration type"),
        ("service_status", "Service status"), ("preferred_language", "Preferred language"),
        ("pharmacy_type", "Pharmacy type"), ("grade", "Grade"), ("activity_domain", "Activity domain"),
        ("is_llc", "Limited liability company"),
    ])}]
    address = record.get("address") or {}
    location = fields(address, [("address", "Address"), ("latitude", "Latitude"), ("longitude", "Longitude"), ("long_lat", "Coordinates"), ("total_area", "Total area")])
    for key, label in [("province", "Province"), ("district", "District")]:
        value = address.get(key) or {}
        if isinstance(value, dict):
            value = value.get("name_fa") or value.get("name_en") or value.get("name_ps")
        if isinstance(value, str) and value:
            location.insert(0, {"label": label, "value": value})
    sections.append({"title": "Location", "fields": location})
    for key, title in [("applicant", "Applicant"), ("co_owner", "Co-owner")]:
        person = record.get(key)
        if isinstance(person, dict):
            sections.append({"title": title, "fields": fields(person, [
                ("first_name_fa", "First name"), ("last_name_fa", "Last name"),
                ("first_name_en", "English first name"), ("last_name_en", "English last name"),
                ("phone_number", "Phone"), ("email", "Email"),
            ])})
    sections.append({"title": "License details", "fields": fields(record, [
        ("aisa_license_number", "AISA license number"), ("license_issue_date", "License issue date"),
        ("license_expiry_date", "License expiry date"), ("issue_date", "Issue date"),
        ("expiry_date", "Expiry date"), ("old_license_number", "Previous license number"),
        ("old_license_issue_date", "Previous license issue date"),
        ("environmental_permit_license_number", "Environmental permit number"),
        ("environmental_permit_license_date", "Environmental permit date"),
    ])})
    sections.append({"title": "Record dates", "fields": fields(record, [("created_at", "Created at"), ("updated_at", "Updated at")])})
    return {"name": record.get("name") or record.get("name_en") or record["application_id"],
            "application_id": record["application_id"], "category": category, "is_demo": False,
            "sections": [section for section in sections if section["fields"]]}
