"""Server-only Licensing API client and minimal Mandi source projections."""
import math
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


def _request(category, suffix, params=None, *, connection=None):
    if category not in CATEGORIES:
        raise ValidationError({"category": "Unknown Licensing application category."})
    base_url, api_key, timeout = connection or (settings.LICENSING_BASE_URL, settings.LICENSING_REGISTRATION_API_KEY, settings.LICENSING_TIMEOUT)
    if not base_url or not api_key:
        raise LicensingError("The Licensing connection is not configured.")
    url = f"{base_url.rstrip('/')}/api/applications/{category}/registration/{suffix}"
    try:
        response = requests.get(url, params=params, headers={
            "X-API-KEY": api_key,
            "Accept": "application/json",
        }, timeout=timeout, allow_redirects=False)
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


def list_applications(category, filters=None, *, connection=None):
    params = {key: value for key, value in (filters or {}).items() if key in FILTERS}
    params.setdefault("page_size", 20)
    payload = _request(category, "list/", params, connection=connection)
    if not isinstance(payload, (dict, list)) or (isinstance(payload, dict) and not isinstance(payload.get("results"), list)):
        raise LicensingError("The Licensing service returned an invalid list.")
    return payload


def get_application(category, application_id, *, connection=None):
    if not application_id or str(application_id) in {".", ".."}:
        raise ValidationError({"application_id": "An application ID is required."})
    payload = _request(category, f"{quote(str(application_id), safe='')}/", connection=connection)
    if not isinstance(payload, dict) or not payload.get("application_id"):
        raise LicensingError("The Licensing service returned an invalid application.")
    return payload


def readable_address(value):
    if isinstance(value, dict):
        return " · ".join(str(part) for part in value.values() if isinstance(part, (str, int, float)) and str(part).strip())
    return str(value or "")


def related_mappings(record):
    mappings = {}
    for source in ("archive", "survey"):
        nested = record.get(source)
        if source + "_id" in record or isinstance(nested, dict):
            external_id = record.get(source + "_id")
            if external_id is None and isinstance(nested, dict):
                external_id = nested.get("id")
            mappings[source] = str(external_id) if external_id is not None and str(external_id).strip() else None
    return mappings


def _plain_name(value):
    """Collapse a multilingual name object to one display string."""
    if isinstance(value, dict):
        for key in ("name_en", "name_fa", "name_ps"):
            if value.get(key):
                return str(value[key])
        return ""
    return str(value or "")


def _joined_names(items):
    values = _named_items(items)
    if isinstance(values, list):
        return ", ".join(text for text in (_plain_name(item) for item in values) if text)
    return _plain_name(values)


def candidate(category, record):
    """Only business identity, location, license and contact details are saved."""
    application_id = str(record.get("application_id") or "")
    if not application_id:
        raise LicensingError("A Licensing record has no application ID.")
    address = record.get("address") or {}
    province = address.get("province") or {}
    district = address.get("district") or {}
    location_fields = _location(address, province)
    def location_name(value):
        return (value.get("name_fa") or value.get("name_en") or value.get("name_ps") or "") if isinstance(value, dict) else str(value)
    applicant = record.get("applicant") if isinstance(record.get("applicant"), dict) else {}
    staff = [person for person in (record.get("technical_staff") or []) if isinstance(person, dict)]
    # When the owner is also the technical manager, Licensing may omit a
    # separate technical_staff entry; use the applicant as the manager then.
    manager = staff[0] if staff else (applicant if record.get("is_owner_and_technical_same") else {})
    details = {
        "category": category,
        "application_id": application_id,
        "name": record.get("name") or record.get("name_en") or application_id,
        "name_en": record.get("name_en") or "",
        "province": location_name(province),
        "district": location_name(district),
        "address": readable_address(address.get("address")),
        "house_number": location_fields.get("House number") or "",
        "floor": location_fields.get("Floor") or "",
        "market": location_fields.get("Market") or "",
        "neighborhood": location_fields.get("Neighborhood") or "",
        "license_number": record.get("aisa_license_number") or "",
        "license_issue_date": str(record.get("license_issue_date") or record.get("issue_date") or record.get("aisa_license_issue_date") or ""),
        "license_expiry_date": str(record.get("license_expiry_date") or record.get("expiry_date") or record.get("aisa_license_expire_date") or ""),
        "grade": record.get("grade") or "",
        "pharmacy_type": record.get("pharmacy_type") or "",
        "owner": _plain_name(_person_name(applicant)),
        "owner_phone": str(applicant.get("phone_number") or applicant.get("phone") or ""),
        "owner_email": str(applicant.get("email") or ""),
        "technical_manager": _plain_name(_person_name(manager)),
        "technical_manager_phone": str(manager.get("phone_number") or manager.get("phone") or ""),
        "technical_staff_count": len(staff),
        "activities": _joined_names(record.get("activity_domain")),
    }
    location = _location_section(address).get("location")
    if location:
        details["location"] = location
    if "application_status" in record:
        details["status"] = record.get("application_status") or ""
    return {"id": f"{category}:{application_id}", "name": details["name"], "details": details, "external_mappings": related_mappings(record)}


# All operational fields are rendered recursively; personal identity documents stay upstream.
_PRIVATE_KEYS = {"salary", "dob", "hr_code", "tin_number", "photo_attachment", "birth_province", "birth_district"}


def _public_value(value):
    if isinstance(value, dict):
        return {key: _public_value(item) for key, item in value.items()
                if key not in _PRIVATE_KEYS and not any(token in key.lower() for token in ("passport", "nid", "national_id"))}
    if isinstance(value, list):
        return [_public_value(item) for item in value]
    return value


def _label(key):
    return {"name_fa": "Dari name", "name_en": "English name", "name_ps": "Pashto name",
            "application_id": "Application ID", "is_llc": "Limited liability company"}.get(key, key if key[:1].isupper() else key.replace("_", " ").capitalize())


def _section(title, data, include_sensitive=False):
    data = data if include_sensitive else _public_value(data)
    return {"title": title, "fields": [{"label": _label(key), "value": value}
            for key, value in data.items() if value is not None and value != "" and value != [] and value != {}]}


def _name(value):
    if isinstance(value, dict):
        names = {key: value[key] for key in ("name_fa", "name_en", "name_ps") if value.get(key)}
        return names or value.get("name")
    return value if isinstance(value, str) else None


def _person_name(person, prefix=""):
    names = {}
    for language in ("fa", "en", "ps"):
        if prefix:
            text = person.get(f"{prefix}_{language}")
        else:
            text = " ".join(str(person.get(f"{part}_{language}") or "").strip() for part in ("first_name", "last_name")).strip()
        if text:
            names[f"name_{language}"] = text
    if names:
        return names
    if prefix:
        return person.get(prefix)
    return person.get("name") or " ".join(str(person.get(part) or "").strip() for part in ("first_name", "last_name")).strip()


def _person(person, staff=False):
    if not isinstance(person, dict):
        return None
    values = {"Full name": _person_name(person), "Father's name": _person_name(person, "father_name"),
              "Phone": person.get("phone_number") or person.get("phone"), "Email": person.get("email")}
    if staff:
        values.update({"Qualification": person.get("qualification_level"), "Shift": person.get("shift")})
    return {key: value for key, value in values.items() if value is not None and value != "" and value != {}}


def _first(*values):
    """The first value that is present, so Dari/English duplicates collapse."""
    for value in values:
        if value not in (None, "", {}, []):
            return value
    return None


def _location(address, fallback_province=None):
    """A readable address: one location per line, no duplicated upstream keys."""
    if not isinstance(address, dict):
        address = {"address": address}
    street = address.get("address")
    parts = street if isinstance(street, dict) else {}
    village = _first(parts.get("village_name_fa"), parts.get("village_name"), address.get("village"))
    neighborhood = _first(parts.get("neighborhood_fa"), parts.get("neighborhood"))
    landmark = _first(parts.get("land_mark_fa"), parts.get("land_mark"))
    description = street if isinstance(street, str) else parts.get("not_precise_address")
    if not description:
        description = " · ".join(
            dict.fromkeys(str(value).strip() for value in (village, neighborhood, landmark) if value)
        )
    return {"Country": _name(address.get("country") or address.get("country_name")),
            "Province": (_name(address.get("province") or address.get("province_name")) or _name(fallback_province)),
            "District": _name(address.get("district") or address.get("district_name")),
            "Address": description or None,
            "Neighborhood": _name(neighborhood) or neighborhood,
            "Village": _name(village) or village,
            "Landmark": _name(landmark) or landmark,
            "Street": _first(parts.get("street"), parts.get("street_name")),
            "House number": _first(parts.get("house_number"), parts.get("house number")),
            "Floor": _first(parts.get("floor")),
            "Market": _first(parts.get("market")),
            "Area": address.get("total_area")}


def _location_section(address, fallback_province=None):
    section = _section("Location", _location(address, fallback_province))
    if isinstance(address, dict):
        try:
            latitude, longitude = float(address["latitude"]), float(address["longitude"])
            if math.isfinite(latitude) and math.isfinite(longitude) and -90 <= latitude <= 90 and -180 <= longitude <= 180:
                section["location"] = {"latitude": latitude, "longitude": longitude}
        except (KeyError, TypeError, ValueError, OverflowError):
            pass
    return section


def _named_items(items):
    if not isinstance(items, list):
        return _name(items)
    return [name for item in items if (name := _name(item))]


def _document_url(value):
    return value.get("file") if isinstance(value, dict) else value if isinstance(value, str) else None


def application_details(category, record, include_sensitive=False):
    """A concise inspection profile, not an explorer for the upstream schema."""
    location = record.get("address") or {}
    if not isinstance(location, dict):
        location = {"address": location}
    applicant = _person(record.get("applicant"))
    co_owner = _person(record.get("co_owner"))
    staff = [_person(person, staff=True) for person in (record.get("technical_staff") or []) if isinstance(person, dict)]
    staff_people = [person for person in staff if person]
    sections = [
        _section("Establishment", {"Name": _name({"name_fa": record.get("name"), "name_en": record.get("name_en")}),
            "English name": record.get("name_en"), "Application ID": record.get("application_id"),
            "Application status": record.get("application_status"), "Application step": record.get("application_step"),
            "Application type": record.get("application_type"), "Register type": record.get("register_type"),
            "Service status": record.get("service_status"), "Grade": record.get("grade"),
            "Pharmacy type": record.get("pharmacy_type"), "Limited liability company": record.get("is_llc")}),
        _location_section(location),
        _section("Applicant and ownership", {"Applicant": applicant, "Co-owner": co_owner,
            "Owner is technical staff": record.get("is_owner_and_technical_same")}),
        _section("Technical staff", {"Technical staff count": len(staff_people) or None,
            "Staff members": staff_people}),
        _section("Legal representative", {"Representative": _person(record.get("sharia_lawyer"))}),
        _section("License details", {"License number": record.get("aisa_license_number"),
            "License issue date": record.get("license_issue_date") or record.get("issue_date") or record.get("aisa_license_issue_date"),
            "License expiry date": record.get("license_expiry_date") or record.get("expiry_date") or record.get("aisa_license_expire_date"),
            "License document": _document_url(record.get("license_attachment") or record.get("aisa_license_attachment")),
            "Old license number": record.get("old_license_number"),
            "Old license issue date": record.get("old_license_issue_date"),
            "Environmental permit number": record.get("environmental_permit_license_number")}),
        _section("Activities and premises", {"Activities": _named_items(record.get("activity_domain")),
            "Production lines": _named_items(record.get("production_lines")),
            "Branches": _named_items(record.get("company_branches") or record.get("factory_branches")),
            "Warehouses": _named_items(record.get("warehouses")),
            "Premises area": location.get("total_area")}),
    ]
    return {"name": record.get("name") or record.get("name_en") or str(record["application_id"]),
            "application_id": record["application_id"], "category": category,
            "sections": [section for section in sections if section["fields"] or section.get("location")]}


def related_details(record, source, external_id, include_sensitive=False):
    expected = related_mappings(record).get(source)
    if expected != external_id:
        raise ValidationError("The linked source ID changed in Licensing. Refresh the establishment identity to update its mapping.")
    nested = record.get(source)
    if isinstance(nested, dict) and nested.get("id") is not None and str(nested["id"]) != external_id:
        raise ValidationError("Licensing returned an inconsistent linked source ID. The profile cannot be shown safely.")
    if not isinstance(nested, dict):
        return {"name": source.capitalize(), "application_id": external_id,
                "via": "licensing", "notice": "Licensing provides this source ID but no source profile. A direct adapter is needed for further details.", "sections": []}
    return {"name": nested.get("name") or (nested.get("pharmacy_name") if isinstance(nested.get("pharmacy_name"), str) else source.capitalize()),
            "application_id": external_id, "via": "licensing",
            "notice": "These details are supplied by the linked Licensing record.",
            "sections": _related_sections(nested, source)}


def _related_sections(record, source):
    locations = record.get("pharmacy_location") or []
    address = record.get("address") or (locations[-1] if locations else {})
    owners = record.get("pharmacy_owner") or ([record["owner"]] if isinstance(record.get("owner"), dict) else [])
    sections = [
        _section(source.capitalize() + " details", {"Name": record.get("name"), "Establishment type": record.get("entity_type"),
            "Grade": record.get("grade"), "Application status": record.get("application_status"), "Establishment year": record.get("establishment_year")}),
        _location_section(address, record.get("province_name")),
        _section("Ownership", {"Owners": [person for raw in owners if (person := _person(raw))]}),
    ]
    return [section for section in sections if section["fields"] or section.get("location")]
