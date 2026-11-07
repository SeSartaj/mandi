# Mandi backend

Django/DRF with PostgreSQL. See [development instructions](../docs/development.md).

Domain rules, authorization, transactions, reporting queries, source linking, approval, and ingestion live in `apps/*/services.py`. API views delegate to services. Models own persistence and database constraints. Most domain administration is read-only so it cannot bypass services; checklist add/edit and inspection add use service-backed admin forms. Django admin is available at `/admin/` on the backend port (`8001`).

Run `../.venv/bin/python manage.py test tests` from this directory. The API contract is available at `/api/v1/schema/` after authentication. Live KoBo and external-system adapters are deferred; the current integrations support stable choice export, normalized ingestion, and explicit demonstration source lookups.
