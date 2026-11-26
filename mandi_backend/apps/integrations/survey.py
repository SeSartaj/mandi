"""Server-only Survey registration API client and minimal Mandi source projections."""
import math
from urllib.parse import quote

import requests
from django.conf import settings
from rest_framework.exceptions import APIException, NotFound, ValidationError

CATEGORIES = {"pharmacy", "wholesale"}
KIND_CATEGORIES = {"pharmacy": "pharmacy", "wholesaler": "wholesale"}
FILTERS = {
    "search", "page", "page_size", "ordering",
    "name", "entity_type", "application_status", "application_step",
    "is_official", "has_lawyer", "has_pharmacist",
    "confirmed_by_team_leader", "confirmed_by_project_coordinator",
    "confirmed_by_audit", "grade", "grade_type", "tin_number",
    "opening_letter_number", "opening_letter_date",
    "years_of_activity", "years_of_activity__gte", "years_of_activity__lte",
    "current_entity_area__gte", "required_entity_area__lte",
    "owner_first_name", "owner_last_name", "owner_father_name",
    "owner_grand_father", "owner_phone",
    "province", "district", "village", "latitude", "longitude",
    "rejected_by", "rejection_reason", "created_at", "updated_at",
    "exclude_rejected",
}


class SurveyError(APIException):
    status_code = 502
    default_detail = "The Survey service is unavailable."


def configured():
    return bool(settings.SURVEY_BASE_URL and settings.SURVEY_REGISTRATION_API_KEY)


def _request(category, suffix, params=None):
    if category not in CATEGORIES:
        raise ValidationError({"category": "Unknown Survey registration type."})
    base_url, api_key, timeout = (
        settings.SURVEY_BASE_URL,
        settings.SURVEY_REGISTRATION_API_KEY,
        settings.SURVEY_TIMEOUT,
    )
    if not base_url or not api_key:
        raise SurveyError("The Survey connection is not configured.")
    url = f"{base_url.rstrip('/')}/api/applications/{category}/registration/{suffix}"
    try:
        response = requests.get(url, params=params, headers={
            "X-API-KEY": api_key,
            "Accept": "application/json",
        }, timeout=timeout, allow_redirects=False)
    except requests.Timeout as exc:
        raise SurveyError("The Survey service timed out. Try again.") from exc
    except requests.RequestException as exc:
        raise SurveyError("Could not connect to the Survey service.") from exc
    try:
        if response.status_code == 404:
            raise NotFound("Survey registration not found.")
        if response.status_code in (401, 403):
            raise SurveyError("Survey rejected the server credentials. Check the server configuration.")
        if response.status_code == 400:
            raise ValidationError("Survey rejected the search filters.")
        if response.status_code != 200:
            raise SurveyError("The Survey service returned an unexpected response.")
        try:
            return response.json()
        except ValueError as exc:
            raise SurveyError("The Survey service returned invalid JSON.") from exc
    finally:
        response.close()


def list_applications(category, filters=None):
    params = {key: value for key, value in (filters or {}).items() if key in FILTERS}
    params.setdefault("page", 1)
    params.setdefault("page_size", 20)
    payload = _request(category, "list/", params)
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise SurveyError("The Survey service returned an invalid list.")
    return payload


def get_application(category, application_id):
    if not application_id or str(application_id) in {".", ".."}:
        raise ValidationError({"application_id": "An application ID is required."})
    payload = _request(category, f"{quote(str(application_id), safe='')}/")
    if not isinstance(payload, dict) or not payload.get("application_id"):
        raise SurveyError("The Survey service returned an invalid registration.")
    return payload


def _text(value):
    return str(value).strip() if value is not None else ""


def _area_name(value):
    if isinstance(value, dict):
        for key in ("name", "name_en", "name_fa", "name_ps"):
            if _text(value.get(key)):
                return _text(value[key])
        return ""
    return _text(value)


def _coordinates(address):
    """Survey sends decimal strings, with a GeoJSON point as a second source."""
    try:
        latitude = float(address["latitude"])
        longitude = float(address["longitude"])
    except (KeyError, TypeError, ValueError, OverflowError):
        latitude = longitude = None
    if latitude is None or longitude is None:
        point = address.get("point")
        coordinates = point.get("coordinates") if isinstance(point, dict) else None
        if isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
            try:
                longitude, latitude = float(coordinates[0]), float(coordinates[1])
            except (TypeError, ValueError, OverflowError):
                latitude = longitude = None
    if latitude is None or longitude is None:
        return None, None
    if not (math.isfinite(latitude) and math.isfinite(longitude)):
        return None, None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None, None
    return latitude, longitude


def _applicant(record):
    applicant = record.get("applicant")
    if not isinstance(applicant, dict):
        applicant = record.get("owner")
    if not isinstance(applicant, dict):
        return "", ""
    name = " ".join(
        part for part in (_text(applicant.get("first_name")), _text(applicant.get("last_name"))) if part
    )
    return name, _text(applicant.get("phone_number"))


def candidate(category, record):
    """Store business identity, location, contact and registration summary."""
    application_id = _text(record.get("application_id") or record.get("id"))
    if not application_id:
        raise SurveyError("A Survey record has no application ID.")
    address = record.get("address") if isinstance(record.get("address"), dict) else {}
    province = _area_name(address.get("province_name")) or _area_name(address.get("province"))
    district = _area_name(address.get("district_name"))
    village = _text(address.get("village"))
    exact_address = _text(address.get("exact_address"))
    owner, owner_phone = _applicant(record)
    details = {
        "category": category,
        "application_id": application_id,
        "name": _text(record.get("name")) or application_id,
        "province": province,
        "district": district,
        "address": " · ".join(dict.fromkeys(part for part in (village, exact_address) if part)),
        "village": village,
        "owner": owner,
        "owner_phone": owner_phone,
        "status": _text(record.get("application_status")),
        "grade": _text(record.get("grade")),
        "pharmacy_type": _text(record.get("grade_type")),
        "tin_number": _text(record.get("tin_number")),
        "opening_letter_number": _text(record.get("opening_letter_number")),
        "opening_letter_date": _text(record.get("opening_letter_date")),
        "years_of_activity": record.get("years_of_activity"),
        "current_entity_area": record.get("current_entity_area"),
        "required_entity_area": record.get("required_entity_area"),
        "wholesale_count_nearby": record.get("wholesale_count_nearby"),
        "pharmacy_count_nearby": record.get("pharmacy_count_nearby"),
        "distance_to_nearest_pharmacy": record.get("distance_to_nearest_pharmacy"),
        "distance_to_nearest_health_center": record.get("distance_to_nearest_health_center"),
        "type_of_health_center": _text(record.get("type_of_health_center")),
        "is_official": record.get("is_official"),
        "application_step": record.get("application_step"),
        "has_lawyer": record.get("has_lawyer"),
        "has_pharmacist": record.get("has_pharmacist"),
        "confirmed_by_team_leader": record.get("confirmed_by_team_leader"),
        "confirmed_by_project_coordinator": record.get("confirmed_by_project_coordinator"),
        "confirmed_by_audit": record.get("confirmed_by_audit"),
        "rejection_reason": _text(record.get("rejection_reason")),
        "is_resent": record.get("is_resent"),
    }
    latitude, longitude = _coordinates(address)
    if latitude is not None and longitude is not None:
        details["location"] = {"latitude": latitude, "longitude": longitude}
    # Survey application IDs are globally unique across pharmacy and wholesale.
    # An existing `survey_id` therefore identifies the same establishment.
    return {"id": application_id, "name": details["name"], "details": details, "external_mappings": {}}


def _section(title, data):
    return {"title": title, "fields": [
        {"label": label, "value": value}
        for label, value in data.items()
        if value is not None and value != "" and value != [] and value != {}
    ]}


def _location_section(address):
    province = _area_name(address.get("province_name")) or _area_name(address.get("province"))
    district = _area_name(address.get("district_name"))
    village = _text(address.get("village"))
    exact_address = _text(address.get("exact_address"))
    section = _section("Location", {
        "Province": province,
        "District": district,
        "Village": village,
        "Address": exact_address,
    })
    latitude, longitude = _coordinates(address)
    if latitude is not None and longitude is not None:
        section["location"] = {"latitude": latitude, "longitude": longitude}
    return section


def _address_data(address):
    if not isinstance(address, dict):
        return {}
    data = {
        "Province": _area_name(address.get("province_name")) or _area_name(address.get("province")),
        "District": _area_name(address.get("district_name")),
        "Village": _text(address.get("village")),
        "Address": _text(address.get("exact_address")),
    }
    return {key: value for key, value in data.items() if value not in (None, "")}


_SENSITIVE_PERSON_KEYS = (
    ("Date of birth", "date_of_birth"),
    ("NID type", "nid_type"),
    ("Electronic NID", "e_nid_number"),
    ("NID took", "nid_took"),
    ("NID page", "nid_page_number"),
    ("NID register", "nid_register_number"),
    ("NID sokok", "nid_sokok_number"),
    ("NID attachment", "nid_attachment"),
    ("Technical card attachment", "technical_card_attachment"),
    ("Sharia lawyer letter", "sharia_lawyer_letter"),
)


def _person_data(person, include_sensitive=False):
    if not isinstance(person, dict):
        return {}
    name = " ".join(
        part for part in (_text(person.get("first_name")), _text(person.get("last_name"))) if part
    )
    data = {
        "Full name": name,
        "Father's name": _text(person.get("father_name")),
        "Grandfather's name": _text(person.get("grand_father")),
        "Gender": _text(person.get("gender")),
        "Phone": _text(person.get("phone_number")),
        "Country": _text(person.get("country")),
        "Owner is alive": person.get("is_owner_alive"),
        "Owner is also staff": person.get("owner_as_pharmacist"),
        "Education level": _text(person.get("education_level")),
        "University": _text(person.get("university_name")),
        "Field of study": _text(person.get("field_of_study")),
        "Study location": _text(person.get("study_location")),
        "Graduation year": person.get("graduation_year"),
        "Education document number": _text(person.get("education_document_number")),
        "Education document date": _text(person.get("education_document_date")),
        "Technical card number": _text(person.get("technical_card_number")),
        "Technical card expiry": _text(person.get("technical_card_expiry_date")),
        "Sharia lawyer number": _text(person.get("sharia_lawyer_number")),
        "Sharia lawyer issue date": _text(person.get("sharia_lawyer_document_issue_date")),
        "Sharia lawyer authority": _text(person.get("sharia_lawyer_document_issue_authority")),
        "Sharia lawyer authorities": _text(person.get("sharia_lawyer_authorities")),
    }
    current = _address_data(person.get("current_address"))
    if current:
        data["Current address"] = current
    main = _address_data(person.get("main_address"))
    if main:
        data["Main address"] = main
    if include_sensitive:
        for label, key in _SENSITIVE_PERSON_KEYS:
            data[label] = person.get(key)
    return {key: value for key, value in data.items() if value not in (None, "", [], {})}


def _surveyor_data(surveyor, include_sensitive=False):
    if not isinstance(surveyor, dict):
        return {}
    data = {
        "Full name": " ".join(
            part for part in (_text(surveyor.get("first_name")), _text(surveyor.get("last_name"))) if part
        ),
        "Father's name": _text(surveyor.get("father_name")),
        "Phone": _text(surveyor.get("phone_number")),
        "Province": surveyor.get("province"),
    }
    if include_sensitive:
        data["NID"] = _text(surveyor.get("nid"))
    return {key: value for key, value in data.items() if value not in (None, "", [], {})}


_PERSON_ATTACHMENT_FIELDS = (
    ("NID document", "nid_attachment"),
    ("Technical card document", "technical_card_attachment"),
    ("Sharia lawyer document", "sharia_lawyer_letter"),
)


def _person_attachments(person, prefix, include_sensitive):
    if not include_sensitive or not isinstance(person, dict):
        return {}
    data = {}
    for label, key in _PERSON_ATTACHMENT_FIELDS:
        value = person.get(key)
        if value:
            data[f"{prefix} — {label}"] = value
    return data


def _has_person_attachments(person):
    return isinstance(person, dict) and any(
        person.get(key) for _, key in _PERSON_ATTACHMENT_FIELDS
    )


def application_details(category, record, include_sensitive=False):
    """A complete Survey registration profile for Mandi's source panel."""
    application_id = _text(record.get("application_id") or record.get("id"))
    address = record.get("address") if isinstance(record.get("address"), dict) else {}
    owner_raw = record.get("owner") or record.get("applicant")
    staff_raw = [
        item for item in (record.get("technical_staff") or []) if isinstance(item, dict)
    ]
    lawyer_raw = record.get("sharia_lawyer")
    owner = _person_data(owner_raw, include_sensitive)
    staff = [
        person for person in (
            _person_data(item, include_sensitive) for item in staff_raw
        )
        if person
    ]
    lawyer = _person_data(lawyer_raw, include_sensitive)
    surveyors = [
        person for person in (
            _surveyor_data(item, include_sensitive)
            for item in (record.get("surveyor") or [])
            if isinstance(item, dict)
        )
        if person
    ]
    attachments = {
        label: value
        for label, value in (
            ("Opening letter", record.get("opening_letter")),
            ("Form attachment", record.get("form_attachment")),
            ("Other attachments", record.get("other_attachments")),
        )
        if value
    }
    attachments.update(_person_attachments(owner_raw, "Owner", include_sensitive))
    for position, person in enumerate(staff_raw, start=1):
        name = " ".join(
            part for part in (_text(person.get("first_name")), _text(person.get("last_name"))) if part
        )
        prefix = f"Staff {position}" + (f" ({name})" if name else "")
        attachments.update(_person_attachments(person, prefix, include_sensitive))
    attachments.update(
        _person_attachments(lawyer_raw, "Sharia lawyer", include_sensitive)
    )
    hidden_person_attachments = any(
        _has_person_attachments(person)
        for person in (owner_raw, *staff_raw, lawyer_raw)
    )
    establishment = {
        "Name": _text(record.get("name")) or application_id,
        "Survey ID": application_id,
        "Registration type": category.capitalize(),
        "Status": _text(record.get("application_status")),
        "Application step": record.get("application_step"),
        "Official": record.get("is_official"),
        "Grade": _text(record.get("grade")),
        "Pharmacy type": _text(record.get("grade_type")),
        "Opening letter number": _text(record.get("opening_letter_number")),
        "Opening letter date": _text(record.get("opening_letter_date")),
        "Years of activity": record.get("years_of_activity"),
        "TIN number": _text(record.get("tin_number")),
        "Current area": record.get("current_entity_area"),
        "Required area": record.get("required_entity_area"),
        "Located where caroky": record.get("is_located_where_caroky"),
        "Nearby pharmacies": record.get("pharmacy_count_nearby"),
        "Nearby wholesalers": record.get("wholesale_count_nearby"),
        "Distance to nearest pharmacy": record.get("distance_to_nearest_pharmacy"),
        "Distance to nearest health center": record.get("distance_to_nearest_health_center"),
        "Type of health center": _text(record.get("type_of_health_center")),
        "Has lawyer": record.get("has_lawyer"),
        "Has pharmacist": record.get("has_pharmacist"),
        "Confirmed by team leader": record.get("confirmed_by_team_leader"),
        "Confirmed by project coordinator": record.get("confirmed_by_project_coordinator"),
        "Confirmed by audit": record.get("confirmed_by_audit"),
        "Rejection reason": _text(record.get("rejection_reason")),
        "Is resent": record.get("is_resent"),
        "GPS pharmacies nearby": record.get("gps_pharmacy_count_nearby"),
        "GPS distance to nearest pharmacy": record.get("gps_distance_to_nearest_pharmacy"),
        "Created": record.get("created_at"),
        "Updated": record.get("updated_at"),
    }
    sections = [
        _section("Establishment", establishment),
        _location_section(address),
        _section("Owner", owner),
        _section("Technical staff", {
            "Technical staff count": len(staff) or None,
            "Staff members": staff,
        }),
        _section("Sharia lawyer", lawyer),
        _section("Surveyors", {"Survey team": surveyors}),
        _section("Attachments", attachments),
    ]
    return {
        "name": _text(record.get("name")) or application_id,
        "application_id": application_id,
        "category": category,
        "notice": (
            None
            if attachments
            else (
                "Identity or professional documents are stored in Survey but require sensitive-source permission."
                if hidden_person_attachments
                else "No registration attachment files are stored in Survey."
            )
        ),
        "sections": [section for section in sections if section["fields"] or section.get("location")],
    }
