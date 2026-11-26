"""External registry adapters. Credentials and HTTP contracts belong in code/config."""
from rest_framework.exceptions import ValidationError
from . import licensing, survey


class RegistryAdapter:
    """A directly syncable external registry.

    ``kinds`` maps Mandi establishment types to the source's registration
    categories; ``project`` turns one raw source record into the minimal
    identity Mandi stores.
    """

    kinds = {}

    @staticmethod
    def project(category, record):
        raise NotImplementedError


class LicensingAdapter(RegistryAdapter):
    kinds = licensing.KIND_CATEGORIES
    project = staticmethod(licensing.candidate)

    def list_applications(self, category, filters):
        return licensing.list_applications(category, filters)

    def get_application(self, category, application_id):
        return licensing.get_application(category, application_id)

    def list_page(self, kind, page, page_size):
        return self.list_applications(self.category(kind), {"page": page, "page_size": page_size, "ordering": "created_at"})

    @staticmethod
    def category(kind):
        category = licensing.KIND_CATEGORIES.get(kind)
        if not category:
            raise ValidationError("Licensing does not support this establishment type.")
        return category

    def search(self, kind, search="", page=1, page_size=20, filters=None):
        category = self.category(kind)
        params = {"search": search, "page": page, "page_size": page_size}
        if filters:
            mapping = {
                "province": "address_province_name_en",
                "district": "address_district_name_en",
                "status": "application_status",
            }
            for key, value in filters.items():
                if value in (None, ""):
                    continue
                params[mapping.get(key, key)] = value
        payload = self.list_applications(category, params)
        records = payload if isinstance(payload, list) else payload["results"]
        return {"count": len(records) if isinstance(payload, list) else payload.get("count", len(records)),
                "has_next": False if isinstance(payload, list) else bool(payload.get("next")),
                "results": [licensing.candidate(category, record) for record in records]}

    def _record(self, kind, external_id):
        category = self.category(kind)
        prefix, separator, application_id = external_id.partition(":")
        if not separator or prefix != category:
            raise ValidationError({"external_id": "Select a Licensing record in the matching category."})
        return category, self.get_application(category, application_id)

    def identity(self, kind, external_id):
        category, record = self._record(kind, external_id)
        return licensing.candidate(category, record)

    def details(self, kind, external_id, include_sensitive=False):
        category, record = self._record(kind, external_id)
        return licensing.application_details(category, record, include_sensitive=include_sensitive)


class SurveyAdapter(RegistryAdapter):
    kinds = survey.KIND_CATEGORIES
    project = staticmethod(survey.candidate)

    def list_applications(self, category, filters):
        return survey.list_applications(category, filters)

    def get_application(self, category, application_id):
        return survey.get_application(category, application_id)

    @staticmethod
    def category(kind):
        category = survey.KIND_CATEGORIES.get(kind)
        if not category:
            raise ValidationError("Survey does not support this establishment type.")
        return category

    @staticmethod
    def _has_next(payload, page, page_size):
        count = payload.get("count")
        if isinstance(count, int):
            return page * page_size < count
        return len(payload.get("results", [])) >= page_size

    @staticmethod
    def _filter_params(filters):
        params = {}
        for key, value in (filters or {}).items():
            if value in (None, ""):
                continue
            params["application_status" if key == "status" else key] = value
        return params

    def list_page(self, kind, page, page_size, filters=None):
        params = {"page": page, "page_size": page_size}
        params.update(self._filter_params(filters))
        payload = self.list_applications(self.category(kind), params)
        # Survey has no `next` link; derive it from the total count.
        return {"results": payload["results"], "count": payload.get("count"),
                "next": "more" if self._has_next(payload, page, page_size) else None}

    def search(self, kind, search="", page=1, page_size=20, filters=None):
        category = self.category(kind)
        params = {"search": search, "page": page, "page_size": page_size}
        params.update(self._filter_params(filters))
        payload = self.list_applications(category, params)
        return {"count": payload.get("count", len(payload["results"])),
                "has_next": self._has_next(payload, page, page_size),
                "results": [survey.candidate(category, record) for record in payload["results"]]}

    def _record(self, kind, external_id):
        category = self.category(kind)
        # Survey IDs are bare numeric keys. A `category:id` form is accepted for
        # compatibility, but mixed types must not address each other's record.
        prefix, separator, value = external_id.partition(":")
        if separator:
            if prefix != category:
                raise ValidationError({"external_id": "Select a Survey record in the matching registration type."})
            external_id = value
        if not external_id:
            raise ValidationError({"external_id": "An application ID is required."})
        return category, self.get_application(category, external_id)

    def identity(self, kind, external_id):
        category, record = self._record(kind, external_id)
        return survey.candidate(category, record)

    def details(self, kind, external_id, include_sensitive=False):
        category, record = self._record(kind, external_id)
        return survey.application_details(category, record, include_sensitive=include_sensitive)


ADAPTERS = {"licensing": LicensingAdapter(), "survey": SurveyAdapter()}


def adapter_for(source):
    from apps.establishments.models import ExternalSystem
    system = ExternalSystem.objects.filter(pk=source, is_active=True).first()
    if not system:
        raise ValidationError({"source": "Unknown or inactive external system."})
    if system.adapter == "licensing" and not licensing.configured():
        return None
    if system.adapter == "survey" and not survey.configured():
        return None
    return ADAPTERS.get(system.adapter)


def detail_with_field_ids(detail):
    import hashlib
    import json
    for section in detail.get("sections", []):
        for field in section.get("fields", []):
            payload = [section["title"], field["label"], field.get("value")]
            field["id"] = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return detail
