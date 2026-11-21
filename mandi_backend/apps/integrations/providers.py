"""Collection adapter boundary. Only these normalized values enter Mandi workflows."""

from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.utils.module_loading import import_string


class CollectionError(Exception):
    pass


@dataclass
class RemoteSubmission:
    submission_id: str
    establishment_id: str
    submitted_at: datetime | None
    form_version: str
    data: dict


def provider(name):
    adapters = getattr(
        settings, "COLLECTION_ADAPTERS", {"odk": "apps.integrations.odk.OdkProvider"}
    )
    if name not in adapters:
        raise CollectionError(f"Unsupported collection provider: {name}")
    return import_string(adapters[name])()
