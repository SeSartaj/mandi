"""External registry adapters. Credentials and HTTP contracts belong in code/config."""
from rest_framework.exceptions import ValidationError
from . import licensing


class LicensingAdapter:
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

    def search(self, kind, search="", page=1, page_size=20):
        category = self.category(kind)
        payload = self.list_applications(category, {"search": search, "page": page, "page_size": page_size})
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


ADAPTERS = {"licensing": LicensingAdapter()}


def adapter_for(source):
    from apps.establishments.models import ExternalSystem
    system = ExternalSystem.objects.filter(pk=source, is_active=True).first()
    if not system:
        raise ValidationError({"source": "Unknown or inactive external system."})
    if system.adapter == "licensing" and not licensing.configured():
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
